from __future__ import annotations

import io
import json
import re
import time
import unicodedata
import zipfile
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin
from uuid import uuid4

import pandas as pd
import yaml
from sqlalchemy import text

from app.db import session_scope
from app.logging import get_logger
from app.settings import Settings, get_settings
from pipelines.common.bronze_store import artifact_to_dict, persist_raw_bytes
from pipelines.common.http_client import HttpClient
from pipelines.common.observability import replace_pipeline_checks_from_dicts, upsert_pipeline_run

JOB_NAME = "senatran_fleet_fetch"
SOURCE = "SENATRAN"
DATASET_NAME = "senatran_fleet_catalog"
FACT_DATASET_NAME = "senatran_fleet_municipal"
WAVE = "MVP-4"
SENATRAN_CATALOG_PATH = Path("configs/senatran_fleet_catalog.yml")
MANUAL_SENATRAN_DIR = Path("data/manual/senatran")
SENATRAN_PAGE_TEMPLATE = (
    "https://www.gov.br/transportes/pt-br/assuntos/transito/"
    "conteudo-Senatran/frota-de-veiculos-{reference_period}"
)
SENATRAN_REMOTE_CSV_TOKEN = "frotapormunicipioetipo"
SENATRAN_FALLBACK_2025_CSV = (
    "https://www.gov.br/transportes/pt-br/assuntos/transito/"
    "conteudo-Senatran/FrotaporMunicipioetipoJulho2025.csv"
)
_YEAR_TOKEN_RE = re.compile(r"(?:19|20)\d{2}")

_MUNICIPALITY_CODE_COLUMNS = (
    "municipio_ibge",
    "codigo_municipio",
    "cod_municipio",
    "codmunres",
    "ibge",
    "codigo_ibge",
)
_MUNICIPALITY_NAME_COLUMNS = ("municipio", "nome_municipio", "nm_municipio", "munic")
_TOTAL_VALUE_COLUMNS = (
    "frota_total",
    "total_veiculos",
    "total_de_veiculos",
    "total",
    "frota",
)
_MOTORCYCLE_COLUMNS = ("motocicleta", "motocicletas", "moto", "motos", "motoneta", "motonetas")
_CAR_COLUMNS = ("automovel", "automoveis", "carro", "carros")
_BUS_COLUMNS = ("onibus", "autobus")


def _normalize_text(value: str) -> str:
    stripped = value.strip().casefold()
    normalized = unicodedata.normalize("NFKD", stripped)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _normalize_column_name(value: str) -> str:
    base = _normalize_text(value)
    return re.sub(r"[^a-z0-9]+", "_", base).strip("_")


def _extract_year_tokens(value: str) -> set[str]:
    return {match.group(0) for match in _YEAR_TOKEN_RE.finditer(value)}


def _manual_year_rank(path: Path, *, reference_period: str) -> int:
    years = _extract_year_tokens(path.name)
    if reference_period in years:
        return 0
    if not years:
        return 1
    return 2


def _parse_reference_year(reference_period: str) -> str:
    token = str(reference_period).strip()
    if not token:
        raise ValueError("reference_period is empty")
    year = token.split("-")[0]
    if not year.isdigit() or len(year) != 4:
        raise ValueError(f"Invalid reference_period '{reference_period}'. Expected year (YYYY).")
    return year


def _parse_numeric(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return Decimal(str(value))

    token = str(value).strip()
    if not token or token in {"-", "...", "nan", "None"}:
        return None
    normalized = token.replace(" ", "")
    if normalized.count(",") > 1 and "." not in normalized:
        normalized = normalized.replace(",", "")
    elif "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _load_catalog(path: Path = SENATRAN_CATALOG_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    resources = payload.get("resources", [])
    if not isinstance(resources, list):
        raise ValueError("Invalid SENATRAN catalog format: 'resources' must be a list.")
    return [item for item in resources if isinstance(item, dict)]


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
    return str(row[0]).strip(), str(row[1]).strip(), str(row[2]).strip()


def _is_tabular_candidate(path_or_name: str) -> bool:
    suffix = Path(path_or_name).suffix.casefold()
    return suffix in {".csv", ".txt", ".xlsx", ".xls", ".zip"}


def _extract_tabular_bytes_from_zip(zip_bytes: bytes) -> tuple[bytes, str]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        names = [name for name in archive.namelist() if _is_tabular_candidate(name)]
        if not names:
            raise ValueError("ZIP file has no tabular entry.")
        selected = sorted(names)[0]
        return archive.read(selected), Path(selected).suffix.casefold()


def _read_delimited_with_fallback(raw_bytes: bytes) -> pd.DataFrame:
    for encoding in ("utf-8", "latin1"):
        for sep in (";", ",", "\t", "|"):
            try:
                dataframe = pd.read_csv(io.BytesIO(raw_bytes), encoding=encoding, sep=sep, low_memory=False)
                if dataframe.shape[1] == 1:
                    sample = str(dataframe.iloc[0, 0]) if not dataframe.empty else ""
                    if any(token in sample for token in (";", ",", "\t", "|")):
                        continue
                return dataframe
            except Exception:
                continue
    raise ValueError("Could not parse CSV/TXT with supported encodings/delimiters.")


def _load_senatran_structured_csv(raw_bytes: bytes) -> pd.DataFrame:
    for encoding in ("utf-8", "latin1"):
        try:
            payload = raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
        lines = payload.splitlines()
        header_index = next(
            (
                index
                for index, line in enumerate(lines)
                if _normalize_text(line).startswith("uf,municipio,total")
            ),
            None,
        )
        if header_index is None:
            continue

        clean_csv = "\n".join(lines[header_index:])
        dataframe = pd.read_csv(io.StringIO(clean_csv), sep=",", dtype=str, low_memory=False)
        if "UF" not in dataframe.columns or "MUNICIPIO" not in dataframe.columns:
            continue
        return dataframe[dataframe["UF"].astype(str).str.upper() != "UF"].copy()
    raise ValueError("Could not identify SENATRAN CSV header row.")


def _load_dataframe_from_bytes(raw_bytes: bytes, *, suffix: str) -> pd.DataFrame:
    normalized_suffix = suffix.casefold()
    if normalized_suffix == ".zip":
        inner_bytes, inner_suffix = _extract_tabular_bytes_from_zip(raw_bytes)
        return _load_dataframe_from_bytes(inner_bytes, suffix=inner_suffix)
    if normalized_suffix in {".csv", ".txt"}:
        try:
            return _load_senatran_structured_csv(raw_bytes)
        except Exception:
            pass
        return _read_delimited_with_fallback(raw_bytes)
    if normalized_suffix in {".xlsx", ".xls"}:
        return pd.read_excel(io.BytesIO(raw_bytes))
    raise ValueError(f"Unsupported dataset format '{suffix}'.")


def _list_manual_candidates(
    *,
    reference_period: str,
    path: Path = MANUAL_SENATRAN_DIR,
) -> list[Path]:
    if not path.exists():
        return []
    files = [p for p in path.iterdir() if p.is_file() and _is_tabular_candidate(p.name)]
    return sorted(
        files,
        key=lambda candidate: (
            _manual_year_rank(candidate, reference_period=reference_period),
            -candidate.stat().st_mtime,
        ),
    )


def _normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.rename(columns={col: _normalize_column_name(str(col)) for col in df.columns})
    return renamed


def _to_digits(value: Any) -> str:
    text_value = str(value).strip()
    if text_value.endswith(".0"):
        text_value = text_value[:-2]
    return "".join(ch for ch in text_value if ch.isdigit())


def _resolve_municipality_row(
    df: pd.DataFrame,
    *,
    municipality_ibge_code: str,
    municipality_name: str,
) -> dict[str, Any] | None:
    if df.empty:
        return None
    normalized_df = _normalize_dataframe_columns(df)
    target_name = _normalize_text(municipality_name)
    code_candidates = {municipality_ibge_code}
    if len(municipality_ibge_code) >= 6:
        code_candidates.add(municipality_ibge_code[:6])

    for column in _MUNICIPALITY_CODE_COLUMNS:
        if column not in normalized_df.columns:
            continue
        for _, row in normalized_df.iterrows():
            if _to_digits(row.get(column)) in code_candidates:
                return row.to_dict()

    for column in _MUNICIPALITY_NAME_COLUMNS:
        if column not in normalized_df.columns:
            continue
        for _, row in normalized_df.iterrows():
            if _normalize_text(str(row.get(column, ""))) == target_name:
                return row.to_dict()
    return None


def _first_numeric(row: dict[str, Any], candidates: tuple[str, ...]) -> Decimal | None:
    for key in candidates:
        if key not in row:
            continue
        value = _parse_numeric(row.get(key))
        if value is not None:
            return value
    return None


def _fallback_sum_numeric(row: dict[str, Any]) -> Decimal:
    ignored = set(_MUNICIPALITY_CODE_COLUMNS + _MUNICIPALITY_NAME_COLUMNS + ("ano", "year"))
    total = Decimal("0")
    for key, value in row.items():
        if key in ignored:
            continue
        numeric = _parse_numeric(value)
        if numeric is not None:
            total += numeric
    return total


def _build_indicator_rows(
    *,
    territory_id: str,
    reference_period: str,
    municipality_row: dict[str, Any],
) -> list[dict[str, Any]]:
    total = _first_numeric(municipality_row, _TOTAL_VALUE_COLUMNS)
    if total is None:
        total = _fallback_sum_numeric(municipality_row)

    indicators = [
        (
            "SENATRAN_FROTA_TOTAL",
            "SENATRAN frota total de veiculos",
            total,
        )
    ]

    motorcycles = _first_numeric(municipality_row, _MOTORCYCLE_COLUMNS)
    if motorcycles is not None:
        indicators.append(
            (
                "SENATRAN_FROTA_MOTOCICLETAS",
                "SENATRAN frota de motocicletas",
                motorcycles,
            )
        )

    cars = _first_numeric(municipality_row, _CAR_COLUMNS)
    if cars is not None:
        indicators.append(
            (
                "SENATRAN_FROTA_AUTOMOVEIS",
                "SENATRAN frota de automoveis",
                cars,
            )
        )

    buses = _first_numeric(municipality_row, _BUS_COLUMNS)
    if buses is not None:
        indicators.append(
            (
                "SENATRAN_FROTA_ONIBUS",
                "SENATRAN frota de onibus",
                buses,
            )
        )

    rows: list[dict[str, Any]] = []
    for indicator_code, indicator_name, value in indicators:
        rows.append(
            {
                "territory_id": territory_id,
                "source": SOURCE,
                "dataset": FACT_DATASET_NAME,
                "indicator_code": indicator_code,
                "indicator_name": indicator_name,
                "unit": "count",
                "category": "frota_veiculos",
                "value": value,
                "reference_period": reference_period,
            }
        )
    return rows


def _render_uri_template(template: str, *, reference_period: str) -> str:
    return template.format(reference_period=reference_period, year=reference_period)


def _discover_remote_resources(*, reference_period: str, client: HttpClient) -> list[dict[str, Any]]:
    page_url = SENATRAN_PAGE_TEMPLATE.format(reference_period=reference_period)
    payload, _content_type = client.download_bytes(page_url, min_bytes=128)

    try:
        page_html = payload.decode("utf-8")
    except UnicodeDecodeError:
        page_html = payload.decode("latin1", errors="ignore")

    links = re.findall(r'href="([^"]+)"', page_html, flags=re.IGNORECASE)
    discovered_uris: set[str] = set()
    for raw_link in links:
        absolute = urljoin(page_url, raw_link)
        normalized_link = _normalize_text(unquote(absolute))
        if SENATRAN_REMOTE_CSV_TOKEN not in normalized_link:
            continue
        if not absolute.casefold().endswith(".csv"):
            continue
        years = _extract_year_tokens(absolute)
        if years and reference_period not in years:
            continue
        discovered_uris.add(absolute)

    if reference_period == "2025":
        discovered_uris.add(SENATRAN_FALLBACK_2025_CSV)

    return [{"uri": uri, "extension": ".csv"} for uri in sorted(discovered_uris)]


def _resolve_dataset(
    *,
    settings: Settings,
    reference_period: str,
    client: HttpClient,
) -> tuple[pd.DataFrame, bytes, str, str, str, str, list[str]] | None:
    warnings: list[str] = []
    resources = _load_catalog()
    try:
        resources.extend(
            _discover_remote_resources(
                reference_period=reference_period,
                client=client,
            )
        )
    except Exception as exc:
        warnings.append(f"SENATRAN remote discovery failed: {exc}")

    deduped_resources: list[dict[str, Any]] = []
    seen_uris: set[str] = set()
    for resource in resources:
        uri = str(resource.get("uri", "")).strip()
        if not uri or uri in seen_uris:
            continue
        seen_uris.add(uri)
        deduped_resources.append(resource)

    for resource in deduped_resources:
        uri_template = str(resource.get("uri", "")).strip()
        if not uri_template:
            continue
        uri = _render_uri_template(uri_template, reference_period=reference_period)
        resource_years = _extract_year_tokens(uri)
        if resource_years and reference_period not in resource_years:
            warnings.append(
                f"SENATRAN remote source skipped for year mismatch "
                f"(reference_period={reference_period}, uri={uri})."
            )
            continue
        suffix = str(resource.get("extension", "")).strip().casefold() or Path(uri).suffix.casefold()
        try:
            raw_bytes, _content_type = client.download_bytes(uri, min_bytes=32)
            df = _load_dataframe_from_bytes(raw_bytes, suffix=suffix)
            return df, raw_bytes, suffix, "remote", uri, Path(uri).name, warnings
        except Exception as exc:
            warnings.append(f"SENATRAN remote source failed for '{uri}': {exc}")

    for candidate in _list_manual_candidates(reference_period=reference_period):
        try:
            if _manual_year_rank(candidate, reference_period=reference_period) == 2:
                warnings.append(
                    f"SENATRAN manual source skipped for year mismatch "
                    f"(reference_period={reference_period}, file={candidate.name})."
                )
                continue
            raw_bytes = candidate.read_bytes()
            suffix = candidate.suffix.casefold()
            df = _load_dataframe_from_bytes(raw_bytes, suffix=suffix)
            return df, raw_bytes, suffix, "manual", candidate.resolve().as_uri(), candidate.name, warnings
        except Exception as exc:
            warnings.append(f"SENATRAN manual source failed for '{candidate.name}': {exc}")

    return None


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
        parsed_reference_period = _parse_reference_year(reference_period)
        territory_id, municipality_name, municipality_ibge_code = _resolve_municipality_context(settings)
    except Exception as exc:
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
        dataset = _resolve_dataset(
            settings=settings,
            reference_period=parsed_reference_period,
            client=client,
        )
        if dataset is None:
            warnings.append("No SENATRAN source available (remote catalog and manual directory failed).")
            elapsed = time.perf_counter() - started_at
            if not dry_run:
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
                        status="blocked",
                        rows_extracted=0,
                        rows_loaded=0,
                        warnings_count=len(warnings),
                        errors_count=0,
                        details={"reason": "source_unavailable"},
                    )
                    replace_pipeline_checks_from_dicts(
                        session=session,
                        run_id=run_id,
                        checks=[
                            {
                                "name": "senatran_source_resolved",
                                "status": "warn",
                                "details": "No SENATRAN source available (remote catalog and manual directory failed).",
                                "observed_value": 0,
                                "threshold_value": 1,
                            },
                            {
                                "name": "senatran_indicator_rows_loaded",
                                "status": "warn",
                                "details": "0 indicator rows written because no source was available.",
                                "observed_value": 0,
                                "threshold_value": 1,
                            },
                        ],
                    )
            return {
                "job": JOB_NAME,
                "status": "blocked",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": 0,
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
            }

        df, raw_bytes, source_suffix, source_type, source_uri, source_file_name, source_warnings = dataset
        warnings.extend(source_warnings)
        rows_extracted = len(df)

        municipality_row = _resolve_municipality_row(
            df,
            municipality_ibge_code=municipality_ibge_code,
            municipality_name=municipality_name,
        )
        if municipality_row is None:
            warnings.append(
                f"SENATRAN row not found for municipality code/name ({municipality_ibge_code}/{municipality_name})."
            )
            load_rows: list[dict[str, Any]] = []
        else:
            load_rows = _build_indicator_rows(
                territory_id=territory_id,
                reference_period=parsed_reference_period,
                municipality_row=municipality_row,
            )

        if dry_run:
            elapsed = time.perf_counter() - started_at
            return {
                "job": JOB_NAME,
                "status": "success" if load_rows else "blocked",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": rows_extracted,
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
                "preview": {
                    "source_type": source_type,
                    "source_uri": source_uri,
                    "source_file_name": source_file_name,
                    "indicators": [
                        {
                            "indicator_code": row["indicator_code"],
                            "value": str(row["value"]),
                        }
                        for row in load_rows
                    ],
                },
            }

        rows_written = 0
        if load_rows:
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
                            "territory_id": row["territory_id"],
                            "source": row["source"],
                            "dataset": row["dataset"],
                            "indicator_code": row["indicator_code"],
                            "indicator_name": row["indicator_name"],
                            "unit": row["unit"],
                            "category": row["category"],
                            "value": str(row["value"]),
                            "reference_period": row["reference_period"],
                        },
                    )
            rows_written = len(load_rows)

        checks = [
            {
                "name": "senatran_source_resolved",
                "status": "pass" if source_type in {"remote", "manual"} else "warn",
                "details": f"Source type resolved as {source_type}.",
                "observed_value": 1 if source_type in {"remote", "manual"} else 0,
                "threshold_value": 1,
            },
            {
                "name": "senatran_municipality_row_found",
                "status": "pass" if municipality_row is not None else "warn",
                "details": "Municipality row should be present in SENATRAN dataset.",
                "observed_value": 1 if municipality_row is not None else 0,
                "threshold_value": 1,
            },
            {
                "name": "senatran_indicator_rows_loaded",
                "status": "pass" if rows_written > 0 else "warn",
                "details": f"{rows_written} indicator rows written.",
                "observed_value": rows_written,
                "threshold_value": 1,
            },
        ]

        bronze_payload = {
            "job": JOB_NAME,
            "source": SOURCE,
            "reference_period": parsed_reference_period,
            "source_type": source_type,
            "source_uri": source_uri,
            "source_file_name": source_file_name,
            "rows_extracted": rows_extracted,
            "rows_written": rows_written,
            "warnings": warnings,
        }
        artifact = persist_raw_bytes(
            settings=settings,
            source=SOURCE,
            dataset=DATASET_NAME,
            reference_period=parsed_reference_period,
            raw_bytes=raw_bytes
            if source_suffix in {".csv", ".txt", ".xlsx", ".xls", ".zip"}
            else json.dumps(bronze_payload, ensure_ascii=False).encode("utf-8"),
            extension=source_suffix if source_suffix else ".json",
            uri=source_uri,
            territory_scope="municipality",
            dataset_version="senatran-fleet-v1",
            checks=checks,
            notes="SENATRAN fleet extraction and indicator upsert.",
            run_id=run_id,
            tables_written=["silver.fact_indicator"] if rows_written > 0 else [],
            rows_written=(
                [{"table": "silver.fact_indicator", "rows": rows_written}] if rows_written > 0 else []
            ),
        )

        status = "success" if rows_written > 0 else "blocked"
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
                status=status,
                rows_extracted=rows_extracted,
                rows_loaded=rows_written,
                warnings_count=len(warnings),
                errors_count=0,
                bronze_path=artifact.local_path.as_posix(),
                manifest_path=artifact.manifest_path.as_posix(),
                checksum_sha256=artifact.checksum_sha256,
                details={
                    "source_type": source_type,
                    "source_file_name": source_file_name,
                    "rows_written": rows_written,
                },
            )
            replace_pipeline_checks_from_dicts(session=session, run_id=run_id, checks=checks)

        elapsed = time.perf_counter() - started_at
        logger.info(
            "SENATRAN fleet job finished.",
            run_id=run_id,
            status=status,
            rows_extracted=rows_extracted,
            rows_written=rows_written,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": JOB_NAME,
            "status": status,
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": rows_extracted,
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
                    replace_pipeline_checks_from_dicts(
                        session=session,
                        run_id=run_id,
                        checks=[
                            {
                                "name": "senatran_job_exception",
                                "status": "fail",
                                "details": f"SENATRAN connector failed with exception: {exc}",
                                "observed_value": 1,
                                "threshold_value": 0,
                            }
                        ],
                    )
            except Exception:
                logger.exception("Could not persist failed pipeline run in ops tables.", run_id=run_id)

        logger.exception(
            "SENATRAN fleet job failed.",
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
