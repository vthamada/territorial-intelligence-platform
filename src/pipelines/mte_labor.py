from __future__ import annotations

import ftplib
import io
import json
import posixpath
import re
import time
import unicodedata
import zipfile
from collections import deque
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from sqlalchemy import text

from app.db import session_scope
from app.logging import get_logger
from app.settings import Settings, get_settings
from pipelines.common.bronze_store import artifact_to_dict, persist_raw_bytes
from pipelines.common.http_client import HttpClient
from pipelines.common.observability import replace_pipeline_checks_from_dicts, upsert_pipeline_run

JOB_NAME = "labor_mte_fetch"
SOURCE = "MTE"
DATASET_NAME = "mte_novo_caged"
WAVE = "MVP-3"
MTE_PORTAL_URL = "https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/novo-caged"
MTE_MICRODATA_URL = f"{MTE_PORTAL_URL}/microdados"
MTE_FTP_HOST_DEFAULT = "ftp.mtps.gov.br"
MTE_FTP_PORT_DEFAULT = 21
MTE_FTP_ROOT_CANDIDATES_DEFAULT = (
    "/pdet/microdados/NOVO CAGED",
    "/pdet/microdados/NOVO_CAGED",
)
MTE_FTP_MAX_DEPTH_DEFAULT = 4
MTE_FTP_MAX_DIRS_DEFAULT = 300
MANUAL_MTE_DIR = Path("data/manual/mte")


def _normalize_text(value: str) -> str:
    stripped = value.strip().casefold()
    normalized = unicodedata.normalize("NFKD", stripped)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _normalize_column_name(value: str) -> str:
    base = _normalize_text(value)
    return re.sub(r"[^a-z0-9]+", "_", base).strip("_")


def _parse_reference_period(reference_period: str) -> str:
    token = str(reference_period).strip()
    if not token:
        raise ValueError("reference_period is empty")
    year = token.split("-")[0]
    if not year.isdigit() or len(year) != 4:
        raise ValueError(f"Invalid reference_period '{reference_period}'. Expected year (YYYY).")
    return year


def _normalize_code(value: Any) -> str:
    text_value = str(value).strip()
    if not text_value:
        return ""
    if text_value.endswith(".0"):
        text_value = text_value[:-2]
    return "".join(ch for ch in text_value if ch.isdigit())


def _coerce_numeric(series: pd.Series) -> pd.Series:
    text_series = series.astype(str).str.strip()
    text_series = text_series.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(text_series, errors="coerce").fillna(0)


def _resolve_municipality_context(settings: Settings) -> tuple[str, str, str]:
    with session_scope(settings) as session:
        row = session.execute(
            text(
                """
                SELECT territory_id::text, name, municipality_ibge_code
                FROM silver.dim_territory
                WHERE level = 'municipality'
                  AND municipality_ibge_code = :municipality_ibge_code
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """
            ),
            {"municipality_ibge_code": settings.municipality_ibge_code},
        ).first()
    if row is None:
        raise RuntimeError("Municipality territory not found. Run ibge_admin_fetch first.")
    territory_id = str(row[0]).strip()
    municipality_name = str(row[1]).strip()
    municipality_ibge_code = str(row[2]).strip()
    if not territory_id or not municipality_name or not municipality_ibge_code:
        raise RuntimeError("Invalid municipality context in dim_territory.")
    return territory_id, municipality_name, municipality_ibge_code


def _probe_remote_access(client: HttpClient) -> dict[str, Any]:
    portal_status = None
    microdata_status = None
    microdata_final_url = None
    requires_login = False

    try:
        portal_resp = client._request("GET", MTE_PORTAL_URL)  # noqa: SLF001
        portal_status = portal_resp.status_code
    except Exception:
        portal_status = None

    try:
        micro_resp = client._request("GET", MTE_MICRODATA_URL)  # noqa: SLF001
        microdata_status = micro_resp.status_code
        microdata_final_url = str(micro_resp.url)
        requires_login = "require_login" in microdata_final_url.casefold()
    except Exception as exc:
        microdata_status = None
        microdata_final_url = f"error://{exc}"

    return {
        "portal_status": portal_status,
        "microdata_status": microdata_status,
        "microdata_final_url": microdata_final_url,
        "requires_login": requires_login,
    }


def _is_tabular_candidate(path_or_name: str) -> bool:
    suffix = Path(path_or_name).suffix.casefold()
    return suffix in {".csv", ".txt", ".zip"}


def _list_manual_candidates(manual_dir: Path) -> list[Path]:
    if not manual_dir.exists():
        return []
    candidates = [
        path
        for path in manual_dir.iterdir()
        if path.is_file() and _is_tabular_candidate(path.name)
    ]
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)


def _read_delimited_with_fallback(
    raw_bytes: bytes,
    *,
    separators: tuple[str, ...] = (";", ","),
) -> pd.DataFrame:
    for encoding in ("utf-8", "latin1"):
        for sep in separators:
            try:
                return pd.read_csv(
                    io.BytesIO(raw_bytes),
                    encoding=encoding,
                    sep=sep,
                    low_memory=False,
                )
            except Exception:
                continue
    raise ValueError("Could not parse tabular file with supported delimiters/encodings.")


def _extract_tabular_bytes_from_zip(zip_bytes: bytes) -> tuple[bytes, str]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        names = [name for name in archive.namelist() if _is_tabular_candidate(name)]
        if not names:
            raise ValueError("ZIP file has no CSV/TXT entry.")
        selected = sorted(names)[0]
        return archive.read(selected), Path(selected).suffix.casefold()


def _load_dataframe_from_bytes(raw_bytes: bytes, *, suffix: str) -> pd.DataFrame:
    normalized_suffix = suffix.casefold()
    if normalized_suffix == ".zip":
        inner_bytes, inner_suffix = _extract_tabular_bytes_from_zip(raw_bytes)
        return _load_dataframe_from_bytes(inner_bytes, suffix=inner_suffix)
    if normalized_suffix in {".csv", ".txt"}:
        separators = (";", ",") if normalized_suffix == ".csv" else (";", ",", "\t", "|")
        return _read_delimited_with_fallback(raw_bytes, separators=separators)
    raise ValueError(f"Unsupported dataset format '{suffix}'.")


def _load_manual_dataframe(path: Path) -> pd.DataFrame:
    return _load_dataframe_from_bytes(path.read_bytes(), suffix=path.suffix)


def _ftp_path_join(base_path: str, entry_name: str) -> str:
    if entry_name.startswith("/"):
        return posixpath.normpath(entry_name)
    return posixpath.normpath(posixpath.join(base_path, entry_name))


def _is_ftp_directory(ftp: ftplib.FTP, path: str) -> bool:
    current_dir = ftp.pwd()
    try:
        ftp.cwd(path)
        return True
    except Exception:
        return False
    finally:
        try:
            ftp.cwd(current_dir)
        except Exception:
            pass


def _ftp_list_entries(ftp: ftplib.FTP, path: str) -> tuple[list[str], list[str]]:
    dirs: list[str] = []
    files: list[str] = []
    seen: set[str] = set()

    try:
        for name, facts in ftp.mlsd(path):
            if name in {".", ".."}:
                continue
            full_path = _ftp_path_join(path, name)
            if full_path in seen:
                continue
            seen.add(full_path)
            entry_type = str(facts.get("type", "")).casefold()
            if entry_type == "dir":
                dirs.append(full_path)
            elif entry_type == "file":
                files.append(full_path)
            elif _is_ftp_directory(ftp, full_path):
                dirs.append(full_path)
            else:
                files.append(full_path)
        return sorted(dirs), sorted(files)
    except Exception:
        pass

    try:
        names = ftp.nlst(path)
    except Exception:
        return [], []

    for name in names:
        full_path = _ftp_path_join(path, str(name))
        if full_path in seen or full_path == posixpath.normpath(path):
            continue
        seen.add(full_path)
        if _is_ftp_directory(ftp, full_path):
            dirs.append(full_path)
        else:
            files.append(full_path)
    return sorted(dirs), sorted(files)


def _extract_timestamp_token(path_or_name: str) -> int:
    name = Path(path_or_name).name
    month_match = re.search(r"(20\d{2})(0[1-9]|1[0-2])", name)
    if month_match:
        return int(month_match.group(0))
    year_match = re.search(r"(20\d{2})", name)
    if year_match:
        return int(f"{year_match.group(1)}00")
    return 0


def _parse_root_candidates(raw_candidates: str | None) -> tuple[str, ...]:
    if not raw_candidates:
        return MTE_FTP_ROOT_CANDIDATES_DEFAULT
    parsed = tuple(
        candidate.strip()
        for candidate in raw_candidates.split(",")
        if candidate.strip()
    )
    return parsed or MTE_FTP_ROOT_CANDIDATES_DEFAULT


def _directory_priority(path: str, reference_year: str) -> int:
    name = Path(path).name.casefold()
    if reference_year in name:
        return 0
    if name.startswith("20"):
        return 1
    if any(token in name for token in ("novo", "caged", "mov", "extracao")):
        return 2
    return 3


def _select_best_ftp_file(paths: list[str], reference_year: str) -> str | None:
    if not paths:
        return None
    year_paths = [path for path in paths if reference_year in path]
    candidates = year_paths or paths

    def rank(path: str) -> tuple[int, int, str]:
        suffix = Path(path).suffix.casefold()
        suffix_score = {".zip": 3, ".txt": 2, ".csv": 1}.get(suffix, 0)
        return (
            _extract_timestamp_token(path),
            suffix_score,
            Path(path).name.casefold(),
        )

    return sorted(candidates, key=rank, reverse=True)[0]


def _discover_ftp_candidates(
    ftp: ftplib.FTP,
    *,
    reference_year: str,
    root_candidates: tuple[str, ...],
    max_depth: int,
    max_dirs: int,
) -> tuple[list[str], str | None]:
    year_token = str(reference_year)
    collected: list[str] = []
    selected_root: str | None = None
    visited: set[str] = set()
    scanned_dirs = 0

    for root in root_candidates:
        if not _is_ftp_directory(ftp, root):
            continue
        selected_root = root
        queue: deque[tuple[str, int]] = deque([(root, 0)])
        while queue and scanned_dirs < max_dirs:
            current_dir, depth = queue.popleft()
            if current_dir in visited:
                continue
            visited.add(current_dir)
            scanned_dirs += 1

            child_dirs, child_files = _ftp_list_entries(ftp, current_dir)
            collected.extend(path for path in child_files if _is_tabular_candidate(path))

            if depth >= max_depth:
                continue
            prioritized_dirs = sorted(
                child_dirs,
                key=lambda path: (_directory_priority(path, year_token), path.casefold()),
            )
            for child_dir in prioritized_dirs:
                if child_dir not in visited:
                    queue.append((child_dir, depth + 1))
        if collected:
            break

    deduped = sorted(set(collected))
    return deduped, selected_root


def _download_ftp_file(ftp: ftplib.FTP, remote_path: str) -> bytes:
    chunks: list[bytes] = []
    ftp.retrbinary(f"RETR {remote_path}", chunks.append)
    return b"".join(chunks)


def _load_ftp_dataframe(
    *,
    reference_year: str,
    timeout_seconds: int,
    ftp_host: str,
    ftp_port: int,
    root_candidates: tuple[str, ...],
    max_depth: int,
    max_dirs: int,
) -> tuple[pd.DataFrame | None, str | None, list[str]]:
    warnings: list[str] = []
    ftp = ftplib.FTP()
    try:
        ftp.connect(ftp_host, ftp_port, timeout=timeout_seconds)
        ftp.login()
        candidate_paths, root = _discover_ftp_candidates(
            ftp,
            reference_year=reference_year,
            root_candidates=root_candidates,
            max_depth=max_depth,
            max_dirs=max_dirs,
        )
        if root is None:
            warnings.append("MTE FTP root path not reachable.")
            return None, None, warnings
        selected_path = _select_best_ftp_file(candidate_paths, reference_year)
        if selected_path is None:
            warnings.append("No MTE FTP dataset file was discovered for the requested period.")
            return None, None, warnings
        raw_bytes = _download_ftp_file(ftp, selected_path)
        dataframe = _load_dataframe_from_bytes(raw_bytes, suffix=Path(selected_path).suffix)
        source_uri = f"ftp://{ftp_host}{selected_path}"
        return dataframe, source_uri, warnings
    except Exception as exc:
        warnings.append(f"MTE FTP access failed: {exc}")
        return None, None, warnings
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


def _pick_column(columns: list[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def _filter_municipality_rows(
    df: pd.DataFrame,
    *,
    municipality_name: str,
    municipality_ibge_code: str,
) -> pd.DataFrame:
    normalized = df.rename(columns={col: _normalize_column_name(str(col)) for col in df.columns})
    cols = [str(col) for col in normalized.columns]

    ibge7 = municipality_ibge_code
    ibge6 = (
        municipality_ibge_code[:6]
        if len(municipality_ibge_code) >= 6
        else municipality_ibge_code
    )
    code_targets = {ibge7, ibge6}

    code_col = _pick_column(
        cols,
        [
            "codigo_municipio",
            "cod_municipio",
            "municipio_codigo",
            "cod_ibge",
            "codigo_ibge",
            "id_municipio",
            "municipio_ibge",
            "codigo_municipio_ibge",
            "codmun",
            "mun_cod",
            "municipio",
        ],
    )
    if code_col:
        normalized["_code"] = normalized[code_col].map(_normalize_code)
        by_code = normalized[normalized["_code"].isin(code_targets)].copy()
        if not by_code.empty:
            return by_code

    city_col = _pick_column(cols, ["municipio", "nome_municipio", "nm_municipio", "municipio_nome"])
    uf_col = _pick_column(cols, ["uf", "sigla_uf"])
    if city_col:
        target_name = _normalize_text(municipality_name)
        city_mask = normalized[city_col].astype(str).map(_normalize_text).eq(target_name)
        if uf_col:
            uf_mask = normalized[uf_col].astype(str).str.strip().str.upper().eq("MG")
            return normalized[city_mask & uf_mask].copy()
        return normalized[city_mask].copy()
    return normalized.iloc[0:0].copy()


def _compute_mte_metrics(
    filtered_df: pd.DataFrame,
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    cols = [str(col) for col in filtered_df.columns]
    admissions_col = _pick_column(cols, ["admissoes", "admitidos", "qt_admitidos", "qtd_admissoes"])
    dismissals_col = _pick_column(
        cols,
        ["desligamentos", "desligados", "qt_desligados", "qtd_desligamentos"],
    )
    balance_col = _pick_column(
        cols,
        ["saldo", "saldo_movimentacao", "saldo_mov", "saldomovimentacao"],
    )

    admissions: Decimal | None = None
    dismissals: Decimal | None = None
    balance: Decimal | None = None
    if admissions_col:
        admissions = Decimal(str(_coerce_numeric(filtered_df[admissions_col]).sum()))
    if dismissals_col:
        dismissals = Decimal(str(_coerce_numeric(filtered_df[dismissals_col]).sum()))
    if balance_col:
        numeric_balance = _coerce_numeric(filtered_df[balance_col])
        balance = Decimal(str(numeric_balance.sum()))
        if admissions is None:
            admissions = Decimal(str(numeric_balance[numeric_balance > 0].sum()))
        if dismissals is None:
            dismissals = Decimal(str((-numeric_balance[numeric_balance < 0]).sum()))

    if balance is None and admissions is not None and dismissals is not None:
        balance = admissions - dismissals

    if admissions is None or dismissals is None:
        movement_type_col = _pick_column(
            cols,
            [
                "tipo_movimentacao",
                "tipo_movimento",
                "tipo_mov",
                "movimentacao",
                "tipo",
            ],
        )
        if movement_type_col:
            labels = filtered_df[movement_type_col].astype(str).map(_normalize_text)
            if admissions is None:
                admissions_count = labels.map(
                    lambda value: "admiss" in value or "admit" in value or "entrada" in value
                ).sum()
                admissions = Decimal(str(admissions_count))
            if dismissals is None:
                dismissals_count = labels.map(
                    lambda value: "deslig" in value or "demiss" in value or "saida" in value
                ).sum()
                dismissals = Decimal(str(dismissals_count))
            if balance is None and admissions is not None and dismissals is not None:
                balance = admissions - dismissals

    return admissions, dismissals, balance


def _build_indicator_rows(
    *,
    territory_id: str,
    reference_period: str,
    filtered_df: pd.DataFrame,
) -> list[dict[str, Any]]:
    admissions, dismissals, balance = _compute_mte_metrics(filtered_df)
    metrics: list[tuple[str, str, Decimal]] = []

    if admissions is not None:
        metrics.append(
            (
                "MTE_NOVO_CAGED_ADMISSOES_TOTAL",
                "MTE Novo CAGED admissoes totais",
                admissions,
            )
        )
    if dismissals is not None:
        metrics.append(
            (
                "MTE_NOVO_CAGED_DESLIGAMENTOS_TOTAL",
                "MTE Novo CAGED desligamentos totais",
                dismissals,
            )
        )
    if balance is not None:
        metrics.append(
            (
                "MTE_NOVO_CAGED_SALDO_TOTAL",
                "MTE Novo CAGED saldo total",
                balance,
            )
        )

    records_total = Decimal(str(len(filtered_df)))
    metrics.append(
        (
            "MTE_NOVO_CAGED_REGISTROS_TOTAL",
            "MTE Novo CAGED registros filtrados",
            records_total,
        )
    )

    return [
        {
            "territory_id": territory_id,
            "source": SOURCE,
            "dataset": DATASET_NAME,
            "indicator_code": indicator_code,
            "indicator_name": indicator_name,
            "unit": "count",
            "category": "novo_caged",
            "value": value,
            "reference_period": reference_period,
        }
        for indicator_code, indicator_name, value in metrics
    ]


def run(
    *,
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 3,
    timeout_seconds: int = 30,
    settings: Settings | None = None,
) -> dict[str, Any]:
    del force
    settings = settings or get_settings()
    logger = get_logger(JOB_NAME)
    run_id = str(uuid4())
    started_at_utc = datetime.now(UTC)
    started_at = time.perf_counter()
    warnings: list[str] = []

    try:
        parsed_reference_period = _parse_reference_period(reference_period)
    except ValueError as exc:
        return {
            "job": JOB_NAME,
            "status": "failed",
            "run_id": run_id,
            "duration_seconds": 0.0,
            "rows_extracted": 0,
            "rows_written": 0,
            "warnings": warnings,
            "errors": [str(exc)],
        }

    client = HttpClient.from_settings(
        settings,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
    try:
        (
            territory_id,
            municipality_name,
            municipality_ibge_code,
        ) = _resolve_municipality_context(settings)
        remote_probe = _probe_remote_access(client)
        ftp_host = settings.mte_ftp_host or MTE_FTP_HOST_DEFAULT
        ftp_port = settings.mte_ftp_port or MTE_FTP_PORT_DEFAULT
        root_candidates = _parse_root_candidates(settings.mte_ftp_root_candidates)
        max_depth = max(0, settings.mte_ftp_max_depth or MTE_FTP_MAX_DEPTH_DEFAULT)
        max_dirs = max(1, settings.mte_ftp_max_dirs or MTE_FTP_MAX_DIRS_DEFAULT)

        source_type: str | None = None
        source_uri: str | None = None
        source_file_name: str | None = None

        raw_df, ftp_uri, ftp_warnings = _load_ftp_dataframe(
            reference_year=parsed_reference_period,
            timeout_seconds=timeout_seconds,
            ftp_host=ftp_host,
            ftp_port=ftp_port,
            root_candidates=root_candidates,
            max_depth=max_depth,
            max_dirs=max_dirs,
        )
        warnings.extend(ftp_warnings)
        if raw_df is not None:
            source_type = "ftp"
            source_uri = ftp_uri

        manual_dir = settings.data_root / MANUAL_MTE_DIR.relative_to("data")
        manual_candidates = _list_manual_candidates(manual_dir)
        selected_manual_file = manual_candidates[0] if manual_candidates else None

        if raw_df is None and selected_manual_file is not None:
            raw_df = _load_manual_dataframe(selected_manual_file)
            source_type = "manual"
            source_uri = selected_manual_file.as_posix()
            source_file_name = selected_manual_file.name

        if raw_df is None:
            warning = (
                "No MTE dataset available automatically (FTP) and no manual file "
                "found in data/manual/mte."
            )
            if remote_probe.get("requires_login"):
                warning = (
                    "MTE portal requires login and no FTP/manual dataset was available. "
                    "Provide a CSV/TXT/ZIP in data/manual/mte."
                )
            warnings.append(warning)

            checks = [
                {
                    "name": "mte_remote_microdata_access",
                    "status": "warn" if remote_probe.get("requires_login") else "pass",
                    "details": (
                        "Remote microdata endpoint requires login."
                        if remote_probe.get("requires_login")
                        else "Remote portal reachable."
                    ),
                    "observed_value": 0 if remote_probe.get("requires_login") else 1,
                    "threshold_value": 1,
                },
                {
                    "name": "mte_ftp_dataset_available",
                    "status": "warn",
                    "details": "No FTP dataset file could be downloaded for the requested period.",
                    "observed_value": 0,
                    "threshold_value": 1,
                },
                {
                    "name": "mte_manual_dataset_available",
                    "status": "warn",
                    "details": "No manual dataset found in data/manual/mte.",
                    "observed_value": 0,
                    "threshold_value": 1,
                },
            ]

            if dry_run:
                elapsed = time.perf_counter() - started_at
                return {
                    "job": JOB_NAME,
                    "status": "blocked",
                    "run_id": run_id,
                    "duration_seconds": round(elapsed, 2),
                    "rows_extracted": 0,
                    "rows_written": 0,
                    "warnings": warnings,
                    "errors": [],
                    "preview": {
                        "remote_probe": remote_probe,
                        "manual_dir": manual_dir.as_posix(),
                        "ftp_host": ftp_host,
                        "ftp_root_candidates": list(root_candidates),
                    },
                }

            raw_bytes = json.dumps(
                {
                    "job": JOB_NAME,
                    "remote_probe": remote_probe,
                    "manual_dir": manual_dir.as_posix(),
                    "manual_candidates": [path.name for path in manual_candidates],
                    "ftp_host": ftp_host,
                    "ftp_root_candidates": list(root_candidates),
                    "warnings": warnings,
                },
                ensure_ascii=False,
            ).encode("utf-8")
            artifact = persist_raw_bytes(
                settings=settings,
                source=SOURCE,
                dataset=DATASET_NAME,
                reference_period=parsed_reference_period,
                raw_bytes=raw_bytes,
                extension=".json",
                uri=MTE_MICRODATA_URL,
                territory_scope="municipality",
                dataset_version="ftp-manual-fallback-v1",
                checks=checks,
                notes="MTE connector blocked: no FTP dataset and no manual file available.",
                run_id=run_id,
                tables_written=[],
                rows_written=[],
            )

            finished_at_utc = datetime.now(UTC)
            with session_scope(settings) as session:
                upsert_pipeline_run(
                    session=session,
                    run_id=run_id,
                    job_name=JOB_NAME,
                    source=SOURCE,
                    dataset=DATASET_NAME,
                    wave=WAVE,
                    reference_period=parsed_reference_period,
                    started_at_utc=started_at_utc,
                    finished_at_utc=finished_at_utc,
                    status="blocked",
                    rows_extracted=0,
                    rows_loaded=0,
                    warnings_count=len(warnings),
                    errors_count=0,
                    bronze_path=artifact.local_path.as_posix(),
                    manifest_path=artifact.manifest_path.as_posix(),
                    checksum_sha256=artifact.checksum_sha256,
                    details={
                        "remote_probe": remote_probe,
                        "manual_dir": manual_dir.as_posix(),
                        "ftp_host": ftp_host,
                        "ftp_root_candidates": list(root_candidates),
                    },
                )
                replace_pipeline_checks_from_dicts(session=session, run_id=run_id, checks=checks)

            elapsed = time.perf_counter() - started_at
            return {
                "job": JOB_NAME,
                "status": "blocked",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": 0,
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
                "bronze": artifact_to_dict(artifact),
            }
        
        filtered_df = _filter_municipality_rows(
            raw_df,
            municipality_name=municipality_name,
            municipality_ibge_code=municipality_ibge_code,
        )
        if filtered_df.empty:
            warnings.append(
                "MTE dataset has no rows for municipality "
                f"{municipality_name} ({municipality_ibge_code})."
            )

        load_rows = _build_indicator_rows(
            territory_id=territory_id,
            reference_period=parsed_reference_period,
            filtered_df=filtered_df,
        )

        if dry_run:
            elapsed = time.perf_counter() - started_at
            return {
                "job": JOB_NAME,
                "status": "success",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": len(filtered_df),
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
                "preview": {
                    "source_type": source_type,
                    "source_uri": source_uri,
                    "raw_rows": len(raw_df),
                    "filtered_rows": len(filtered_df),
                    "indicator_codes": [row["indicator_code"] for row in load_rows],
                },
            }

        rows_written = 0
        with session_scope(settings) as session:
            for row in load_rows:
                session.execute(
                    text(
                        """
                        INSERT INTO silver.fact_indicator (
                            territory_id,
                            source,
                            dataset,
                            indicator_code,
                            indicator_name,
                            unit,
                            category,
                            value,
                            reference_period
                        )
                        VALUES (
                            CAST(:territory_id AS uuid),
                            :source,
                            :dataset,
                            :indicator_code,
                            :indicator_name,
                            :unit,
                            :category,
                            :value,
                            :reference_period
                        )
                        ON CONFLICT (
                            territory_id,
                            source,
                            dataset,
                            indicator_code,
                            category,
                            reference_period
                        )
                        DO UPDATE SET
                            indicator_name = EXCLUDED.indicator_name,
                            unit = EXCLUDED.unit,
                            value = EXCLUDED.value,
                            updated_at = NOW()
                        """
                    ),
                    {
                        **row,
                        "value": str(row["value"]),
                    },
                )
                rows_written += 1

        checks = [
            {
                "name": "mte_data_source_resolved",
                "status": "pass",
                "details": f"MTE dataset loaded from {source_type}.",
                "observed_value": 1,
                "threshold_value": 1,
            },
            {
                "name": "mte_rows_filtered",
                "status": "pass" if len(filtered_df) > 0 else "warn",
                "details": f"{len(filtered_df)} rows filtered for municipality scope.",
                "observed_value": len(filtered_df),
                "threshold_value": 1,
            },
            {
                "name": "mte_indicators_loaded",
                "status": "pass" if rows_written > 0 else "warn",
                "details": f"{rows_written} indicators upserted into silver.fact_indicator.",
                "observed_value": rows_written,
                "threshold_value": 1,
            },
        ]

        bronze_payload = {
            "job": JOB_NAME,
            "source_type": source_type,
            "source_uri": source_uri,
            "source_file_name": source_file_name,
            "remote_probe": remote_probe,
            "rows_raw": len(raw_df),
            "rows_filtered": len(filtered_df),
            "columns": [str(col) for col in raw_df.columns],
            "indicators": [
                {
                    "indicator_code": row["indicator_code"],
                    "value": str(row["value"]),
                }
                for row in load_rows
            ],
        }
        raw_bytes = json.dumps(bronze_payload, ensure_ascii=False).encode("utf-8")
        artifact = persist_raw_bytes(
            settings=settings,
            source=SOURCE,
            dataset=DATASET_NAME,
            reference_period=parsed_reference_period,
            raw_bytes=raw_bytes,
            extension=".json",
            uri=source_uri or MTE_MICRODATA_URL,
            territory_scope="municipality",
            dataset_version="ftp-manual-fallback-v1",
            checks=checks,
            notes="MTE dataset parsed (FTP or manual fallback) and indicators upserted.",
            run_id=run_id,
            tables_written=["silver.fact_indicator"],
            rows_written=[{"table": "silver.fact_indicator", "rows": rows_written}],
        )

        finished_at_utc = datetime.now(UTC)
        with session_scope(settings) as session:
            upsert_pipeline_run(
                session=session,
                run_id=run_id,
                job_name=JOB_NAME,
                source=SOURCE,
                dataset=DATASET_NAME,
                wave=WAVE,
                reference_period=parsed_reference_period,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
                status="success",
                rows_extracted=len(filtered_df),
                rows_loaded=rows_written,
                warnings_count=len(warnings),
                errors_count=0,
                bronze_path=artifact.local_path.as_posix(),
                manifest_path=artifact.manifest_path.as_posix(),
                checksum_sha256=artifact.checksum_sha256,
                details={
                    "source_type": source_type,
                    "source_uri": source_uri,
                    "rows_raw": len(raw_df),
                    "rows_filtered": len(filtered_df),
                },
            )
            replace_pipeline_checks_from_dicts(session=session, run_id=run_id, checks=checks)

        elapsed = time.perf_counter() - started_at
        logger.info(
            "MTE labor job finished.",
            run_id=run_id,
            source_type=source_type,
            rows_extracted=len(filtered_df),
            rows_written=rows_written,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": JOB_NAME,
            "status": "success",
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": len(filtered_df),
            "rows_written": rows_written,
            "warnings": warnings,
            "errors": [],
            "bronze": artifact_to_dict(artifact),
        }
    except Exception as exc:  # pragma: no cover - runtime logging path
        elapsed = time.perf_counter() - started_at
        if not dry_run:
            try:
                with session_scope(settings) as session:
                    upsert_pipeline_run(
                        session=session,
                        run_id=run_id,
                        job_name=JOB_NAME,
                        source=SOURCE,
                        dataset=DATASET_NAME,
                        wave=WAVE,
                        reference_period=parsed_reference_period,
                        started_at_utc=started_at_utc,
                        finished_at_utc=datetime.now(UTC),
                        status="failed",
                        rows_extracted=0,
                        rows_loaded=0,
                        warnings_count=len(warnings),
                        errors_count=1,
                        details={"error": str(exc)},
                    )
            except Exception:
                logger.exception(
                    "Could not persist failed pipeline run in ops tables.",
                    run_id=run_id,
                )

        logger.exception(
            "MTE labor job failed.",
            run_id=run_id,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": JOB_NAME,
            "status": "failed",
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": 0,
            "rows_written": 0,
            "warnings": warnings,
            "errors": [str(exc)],
        }
    finally:
        client.close()
