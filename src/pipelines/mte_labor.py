from __future__ import annotations

import io
import json
import re
import time
import unicodedata
import zipfile
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
DATASET_NAME = "mte_novo_caged_manual"
WAVE = "MVP-3"
MTE_PORTAL_URL = "https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/novo-caged"
MTE_MICRODATA_URL = f"{MTE_PORTAL_URL}/microdados"
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


def _list_manual_candidates(manual_dir: Path) -> list[Path]:
    if not manual_dir.exists():
        return []
    candidates = [
        path
        for path in manual_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".csv", ".zip"}
    ]
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)


def _read_csv_with_fallback(csv_bytes: bytes) -> pd.DataFrame:
    for encoding in ("utf-8", "latin1"):
        for sep in (";", ","):
            try:
                return pd.read_csv(
                    io.BytesIO(csv_bytes),
                    encoding=encoding,
                    sep=sep,
                    low_memory=False,
                )
            except Exception:
                continue
    raise ValueError("Could not parse CSV from manual MTE dataset.")


def _load_manual_dataframe(path: Path) -> pd.DataFrame:
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        return _read_csv_with_fallback(path.read_bytes())
    if suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            csv_names = [name for name in archive.namelist() if name.casefold().endswith(".csv")]
            if not csv_names:
                raise ValueError("ZIP file has no CSV entry.")
            csv_bytes = archive.read(csv_names[0])
        return _read_csv_with_fallback(csv_bytes)
    raise ValueError(f"Unsupported manual dataset format '{path.suffix}'.")


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
        ],
    )
    if code_col:
        normalized["_code"] = normalized[code_col].map(_normalize_code)
        by_code = normalized[normalized["_code"].isin(code_targets)].copy()
        if not by_code.empty:
            return by_code

    city_col = _pick_column(cols, ["municipio", "nome_municipio", "nm_municipio"])
    uf_col = _pick_column(cols, ["uf", "sigla_uf"])
    if city_col:
        target_name = _normalize_text(municipality_name)
        city_mask = normalized[city_col].astype(str).map(_normalize_text).eq(target_name)
        if uf_col:
            uf_mask = normalized[uf_col].astype(str).str.strip().str.upper().eq("MG")
            return normalized[city_mask & uf_mask].copy()
        return normalized[city_mask].copy()
    return normalized.iloc[0:0].copy()


def _build_indicator_rows(
    *,
    territory_id: str,
    reference_period: str,
    filtered_df: pd.DataFrame,
) -> list[dict[str, Any]]:
    cols = [str(col) for col in filtered_df.columns]
    admissions_col = _pick_column(cols, ["admissoes", "admitidos", "qt_admitidos", "qtd_admissoes"])
    dismissals_col = _pick_column(
        cols,
        ["desligamentos", "desligados", "qt_desligados", "qtd_desligamentos"],
    )
    balance_col = _pick_column(cols, ["saldo", "saldo_movimentacao", "saldo_mov"])

    metrics: list[tuple[str, str, Decimal]] = []
    if admissions_col:
        admissions = Decimal(str(_coerce_numeric(filtered_df[admissions_col]).sum()))
        metrics.append(
            (
                "MTE_NOVO_CAGED_ADMISSOES_TOTAL",
                "MTE Novo CAGED admissoes totais",
                admissions,
            )
        )
    if dismissals_col:
        dismissals = Decimal(str(_coerce_numeric(filtered_df[dismissals_col]).sum()))
        metrics.append(
            (
                "MTE_NOVO_CAGED_DESLIGAMENTOS_TOTAL",
                "MTE Novo CAGED desligamentos totais",
                dismissals,
            )
        )
    if balance_col:
        balance = Decimal(str(_coerce_numeric(filtered_df[balance_col]).sum()))
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
            "category": "novo_caged_manual",
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
        manual_dir = settings.data_root / "manual" / "mte"
        manual_candidates = _list_manual_candidates(manual_dir)
        selected_manual_file = manual_candidates[0] if manual_candidates else None

        if selected_manual_file is None:
            warning = (
                "MTE microdata access requires login and no manual dataset found. "
                "Place a CSV/ZIP file in data/manual/mte and rerun."
            )
            if not remote_probe.get("requires_login"):
                warning = "No manual MTE dataset found in data/manual/mte."
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
                    "preview": {"remote_probe": remote_probe, "manual_dir": manual_dir.as_posix()},
                }

            raw_bytes = json.dumps(
                {
                    "job": JOB_NAME,
                    "remote_probe": remote_probe,
                    "manual_dir": manual_dir.as_posix(),
                    "manual_candidates": [path.name for path in manual_candidates],
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
                dataset_version="manual-fallback-v1",
                checks=checks,
                notes="MTE connector blocked on remote microdata access; awaiting manual dataset.",
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

        raw_df = _load_manual_dataframe(selected_manual_file)
        filtered_df = _filter_municipality_rows(
            raw_df,
            municipality_name=municipality_name,
            municipality_ibge_code=municipality_ibge_code,
        )
        if filtered_df.empty:
            warnings.append(
                f"Manual dataset '{selected_manual_file.name}' has no rows for municipality "
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
                    "manual_file": selected_manual_file.as_posix(),
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
                "name": "mte_manual_dataset_available",
                "status": "pass",
                "details": f"Manual dataset loaded from {selected_manual_file.name}.",
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
            "manual_file": selected_manual_file.name,
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
            uri=selected_manual_file.as_posix(),
            territory_scope="municipality",
            dataset_version="manual-fallback-v1",
            checks=checks,
            notes="MTE manual dataset parsing and indicator upsert.",
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
                    "manual_file": selected_manual_file.name,
                    "rows_raw": len(raw_df),
                    "rows_filtered": len(filtered_df),
                },
            )
            replace_pipeline_checks_from_dicts(session=session, run_id=run_id, checks=checks)

        elapsed = time.perf_counter() - started_at
        logger.info(
            "MTE labor job finished.",
            run_id=run_id,
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
