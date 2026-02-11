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

JOB_NAME = "snis_sanitation_fetch"
SOURCE = "SNIS"
DATASET_NAME = "snis_sanitation_catalog"
FACT_DATASET_NAME = "snis_sanitation_municipal"
WAVE = "MVP-4"
SNIS_CATALOG_PATH = Path("configs/snis_sanitation_catalog.yml")
MANUAL_SNIS_DIR = Path("data/manual/snis")

_MUNICIPALITY_CODE_COLUMNS = (
    "municipio_ibge",
    "codigo_municipio",
    "cod_municipio",
    "ibge",
    "codigo_ibge",
)
_MUNICIPALITY_NAME_COLUMNS = ("municipio", "nome_municipio", "nm_municipio", "cidade")
_WATER_COVERAGE_COLUMNS = (
    "atendimento_agua_percentual",
    "agua_atendimento_percentual",
    "indice_atendimento_agua",
    "iaa",
)
_SEWAGE_COVERAGE_COLUMNS = (
    "atendimento_esgoto_percentual",
    "esgoto_atendimento_percentual",
    "indice_atendimento_esgoto",
    "iae",
)
_WATER_LOSS_COLUMNS = (
    "perdas_agua_percentual",
    "indice_perdas_agua",
    "ipa",
)
_SOLID_WASTE_COLUMNS = (
    "coleta_residuos_percentual",
    "residuos_coleta_percentual",
    "indice_coleta_residuos",
)


def _normalize_text(value: str) -> str:
    stripped = value.strip().casefold()
    normalized = unicodedata.normalize("NFKD", stripped)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _normalize_column_name(value: str) -> str:
    base = _normalize_text(value)
    return re.sub(r"[^a-z0-9]+", "_", base).strip("_")


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
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _load_catalog(path: Path = SNIS_CATALOG_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    resources = payload.get("resources", [])
    if not isinstance(resources, list):
        raise ValueError("Invalid SNIS catalog format: 'resources' must be a list.")
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
                return pd.read_csv(io.BytesIO(raw_bytes), encoding=encoding, sep=sep, low_memory=False)
            except Exception:
                continue
    raise ValueError("Could not parse CSV/TXT with supported encodings/delimiters.")


def _load_dataframe_from_bytes(raw_bytes: bytes, *, suffix: str) -> pd.DataFrame:
    normalized_suffix = suffix.casefold()
    if normalized_suffix == ".zip":
        inner_bytes, inner_suffix = _extract_tabular_bytes_from_zip(raw_bytes)
        return _load_dataframe_from_bytes(inner_bytes, suffix=inner_suffix)
    if normalized_suffix in {".csv", ".txt"}:
        return _read_delimited_with_fallback(raw_bytes)
    if normalized_suffix in {".xlsx", ".xls"}:
        return pd.read_excel(io.BytesIO(raw_bytes))
    raise ValueError(f"Unsupported dataset format '{suffix}'.")


def _list_manual_candidates(path: Path = MANUAL_SNIS_DIR) -> list[Path]:
    if not path.exists():
        return []
    files = [p for p in path.iterdir() if p.is_file() and _is_tabular_candidate(p.name)]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def _normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={col: _normalize_column_name(str(col)) for col in df.columns})


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


def _build_indicator_rows(
    *,
    territory_id: str,
    reference_period: str,
    municipality_row: dict[str, Any],
) -> list[dict[str, Any]]:
    indicators: list[tuple[str, str, Decimal, str]] = []

    water_coverage = _first_numeric(municipality_row, _WATER_COVERAGE_COLUMNS)
    if water_coverage is not None:
        indicators.append(
            (
                "SNIS_ATENDIMENTO_AGUA_PERCENTUAL",
                "SNIS percentual de atendimento de agua",
                water_coverage,
                "percent",
            )
        )

    sewage_coverage = _first_numeric(municipality_row, _SEWAGE_COVERAGE_COLUMNS)
    if sewage_coverage is not None:
        indicators.append(
            (
                "SNIS_ATENDIMENTO_ESGOTO_PERCENTUAL",
                "SNIS percentual de atendimento de esgoto",
                sewage_coverage,
                "percent",
            )
        )

    water_loss = _first_numeric(municipality_row, _WATER_LOSS_COLUMNS)
    if water_loss is not None:
        indicators.append(
            (
                "SNIS_PERDAS_AGUA_PERCENTUAL",
                "SNIS percentual de perdas de agua",
                water_loss,
                "percent",
            )
        )

    solid_waste = _first_numeric(municipality_row, _SOLID_WASTE_COLUMNS)
    if solid_waste is not None:
        indicators.append(
            (
                "SNIS_COLETA_RESIDUOS_PERCENTUAL",
                "SNIS percentual de coleta de residuos",
                solid_waste,
                "percent",
            )
        )

    rows: list[dict[str, Any]] = []
    for indicator_code, indicator_name, value, unit in indicators:
        rows.append(
            {
                "territory_id": territory_id,
                "source": SOURCE,
                "dataset": FACT_DATASET_NAME,
                "indicator_code": indicator_code,
                "indicator_name": indicator_name,
                "unit": unit,
                "category": "saneamento",
                "value": value,
                "reference_period": reference_period,
            }
        )
    return rows


def _render_uri_template(template: str, *, reference_period: str) -> str:
    return template.format(reference_period=reference_period)


def _resolve_dataset(
    *,
    reference_period: str,
    client: HttpClient,
) -> tuple[pd.DataFrame, bytes, str, str, str, str, list[str]] | None:
    warnings: list[str] = []
    resources = _load_catalog()

    for resource in resources:
        uri_template = str(resource.get("uri", "")).strip()
        if not uri_template:
            continue
        uri = _render_uri_template(uri_template, reference_period=reference_period)
        suffix = str(resource.get("extension", "")).strip().casefold() or Path(uri).suffix.casefold()
        try:
            raw_bytes, _content_type = client.download_bytes(uri, min_bytes=32)
            df = _load_dataframe_from_bytes(raw_bytes, suffix=suffix)
            return df, raw_bytes, suffix, "remote", uri, Path(uri).name, warnings
        except Exception as exc:
            warnings.append(f"SNIS remote source failed for '{uri}': {exc}")

    for candidate in _list_manual_candidates():
        try:
            raw_bytes = candidate.read_bytes()
            suffix = candidate.suffix.casefold()
            df = _load_dataframe_from_bytes(raw_bytes, suffix=suffix)
            return df, raw_bytes, suffix, "manual", candidate.resolve().as_uri(), candidate.name, warnings
        except Exception as exc:
            warnings.append(f"SNIS manual source failed for '{candidate.name}': {exc}")

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
        dataset = _resolve_dataset(reference_period=parsed_reference_period, client=client)
        if dataset is None:
            warnings.append("No SNIS source available (remote catalog and manual directory failed).")
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
                                "name": "snis_source_resolved",
                                "status": "warn",
                                "details": "No SNIS source available (remote catalog and manual directory failed).",
                                "observed_value": 0,
                                "threshold_value": 1,
                            },
                            {
                                "name": "snis_indicator_rows_loaded",
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
                f"SNIS row not found for municipality code/name ({municipality_ibge_code}/{municipality_name})."
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
                "name": "snis_source_resolved",
                "status": "pass" if source_type in {"remote", "manual"} else "warn",
                "details": f"Source type resolved as {source_type}.",
                "observed_value": 1 if source_type in {"remote", "manual"} else 0,
                "threshold_value": 1,
            },
            {
                "name": "snis_municipality_row_found",
                "status": "pass" if municipality_row is not None else "warn",
                "details": "Municipality row should be present in SNIS dataset.",
                "observed_value": 1 if municipality_row is not None else 0,
                "threshold_value": 1,
            },
            {
                "name": "snis_indicator_rows_loaded",
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
            dataset_version="snis-sanitation-v1",
            checks=checks,
            notes="SNIS sanitation extraction and indicator upsert.",
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
            "SNIS sanitation job finished.",
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
                                "name": "snis_job_exception",
                                "status": "fail",
                                "details": f"SNIS connector failed with exception: {exc}",
                                "observed_value": 1,
                                "threshold_value": 0,
                            }
                        ],
                    )
            except Exception:
                logger.exception("Could not persist failed pipeline run in ops tables.", run_id=run_id)

        logger.exception(
            "SNIS sanitation job failed.",
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
