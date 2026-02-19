from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import text

from app.db import session_scope
from app.logging import get_logger
from app.settings import Settings, get_settings
from pipelines.common.bronze_store import artifact_to_dict, persist_raw_bytes
from pipelines.common.http_client import HttpClient
from pipelines.common.observability import replace_pipeline_checks_from_dicts, upsert_pipeline_run
from pipelines.common import tabular_indicator_connector as tabular

_VALID_SQL_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_VALID_SQL_TABLE = re.compile(r"^silver\.[a-z][a-z0-9_]*$")

_DEFAULT_MUNICIPALITY_CODE_COLUMNS = (
    "municipio_ibge",
    "codigo_municipio",
    "cod_municipio",
    "codmunres",
    "cod_ibge",
    "codigo_ibge",
    "codigo_ibge_7",
    "id_municipio",
    "ibge",
)
_DEFAULT_MUNICIPALITY_NAME_COLUMNS = (
    "municipio",
    "nome_municipio",
    "nm_municipio",
    "cidade",
    "localidade",
)


@dataclass(frozen=True)
class SocialMetricSpec:
    field_name: str
    indicator_code: str
    indicator_name: str
    unit: str
    category: str
    candidates: tuple[str, ...]
    aggregator: Literal["sum", "avg", "max", "min", "first"] = "sum"
    row_filters: dict[str, tuple[str, ...]] | None = None


@dataclass(frozen=True)
class SocialConnectorDefinition:
    job_name: str
    source: str
    dataset_name: str
    fact_dataset_name: str
    wave: str
    catalog_path: Path
    manual_dir: Path
    dataset_version: str
    notes: str
    fact_table: str
    metric_specs: tuple[SocialMetricSpec, ...]
    territory_scope: str = "municipality"
    municipality_code_columns: tuple[str, ...] = _DEFAULT_MUNICIPALITY_CODE_COLUMNS
    municipality_name_columns: tuple[str, ...] = _DEFAULT_MUNICIPALITY_NAME_COLUMNS
    reference_year_columns: tuple[str, ...] = ()
    prefer_manual_first: bool = False


def _to_tabular_definition(definition: SocialConnectorDefinition) -> tabular.TabularConnectorDefinition:
    return tabular.TabularConnectorDefinition(
        job_name=definition.job_name,
        source=definition.source,
        dataset_name=definition.dataset_name,
        fact_dataset_name=definition.fact_dataset_name,
        wave=definition.wave,
        catalog_path=definition.catalog_path,
        manual_dir=definition.manual_dir,
        indicator_specs=(),
        dataset_version=definition.dataset_version,
        notes=definition.notes,
        territory_scope=definition.territory_scope,
        municipality_code_columns=definition.municipality_code_columns,
        municipality_name_columns=definition.municipality_name_columns,
        reference_year_columns=definition.reference_year_columns,
        prefer_manual_first=definition.prefer_manual_first,
    )


def _validate_sql_identifiers(definition: SocialConnectorDefinition) -> None:
    if not _VALID_SQL_TABLE.match(definition.fact_table):
        raise ValueError(f"Invalid fact_table '{definition.fact_table}'.")
    for metric in definition.metric_specs:
        if not _VALID_SQL_NAME.match(metric.field_name):
            raise ValueError(f"Invalid metric field name '{metric.field_name}'.")


def _aggregate_metric(
    municipality_rows: list[dict[str, Any]],
    *,
    candidates: tuple[str, ...],
    aggregator: str,
    row_filters: dict[str, tuple[str, ...]] | None,
) -> Decimal | None:
    values = tabular._extract_candidate_values_with_filters(
        municipality_rows,
        candidates=candidates,
        row_filters=row_filters,
    )
    if not values:
        return None
    return tabular._aggregate_values(values, aggregator)


def _build_metrics_output(
    definition: SocialConnectorDefinition,
    *,
    territory_id: str,
    reference_period: str,
    municipality_rows: list[dict[str, Any]],
) -> tuple[dict[str, Decimal | None], list[dict[str, Any]]]:
    metric_values: dict[str, Decimal | None] = {}
    indicator_rows: list[dict[str, Any]] = []

    for metric in definition.metric_specs:
        value = _aggregate_metric(
            municipality_rows,
            candidates=metric.candidates,
            aggregator=metric.aggregator,
            row_filters=metric.row_filters,
        )
        metric_values[metric.field_name] = value
        if value is None:
            continue
        indicator_rows.append(
            {
                "territory_id": territory_id,
                "source": definition.source,
                "dataset": definition.fact_dataset_name,
                "indicator_code": metric.indicator_code,
                "indicator_name": metric.indicator_name,
                "unit": metric.unit,
                "category": metric.category,
                "value": value,
                "reference_period": reference_period,
            }
        )

    return metric_values, indicator_rows


def _upsert_social_fact_row(
    settings: Settings,
    *,
    definition: SocialConnectorDefinition,
    territory_id: str,
    reference_period: str,
    metric_values: dict[str, Decimal | None],
    metadata_json: dict[str, Any],
) -> int:
    fields = [spec.field_name for spec in definition.metric_specs]
    insert_columns = ", ".join(["territory_id", "source", "dataset", "reference_period", *fields, "metadata_json"])
    insert_values = ", ".join(
        ["CAST(:territory_id AS uuid)", ":source", ":dataset", ":reference_period", *[f":{field}" for field in fields], "CAST(:metadata_json AS jsonb)"]
    )
    update_set = ", ".join([f"{field} = EXCLUDED.{field}" for field in fields] + ["metadata_json = EXCLUDED.metadata_json", "updated_at = NOW()"])
    sql = f"""
        INSERT INTO {definition.fact_table} ({insert_columns})
        VALUES ({insert_values})
        ON CONFLICT (territory_id, source, dataset, reference_period)
        DO UPDATE SET {update_set}
    """

    params: dict[str, Any] = {
        "territory_id": territory_id,
        "source": definition.source,
        "dataset": definition.fact_dataset_name,
        "reference_period": reference_period,
        "metadata_json": json.dumps(metadata_json, ensure_ascii=False),
    }
    for field, value in metric_values.items():
        params[field] = str(value) if value is not None else None

    with session_scope(settings) as session:
        session.execute(text(sql), params)
    return 1


def run_social_connector(
    definition: SocialConnectorDefinition,
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
    logger = get_logger(definition.job_name)
    run_id = str(uuid4())
    started_at_utc = datetime.now(UTC)
    started_at = time.perf_counter()
    warnings: list[str] = []
    errors: list[str] = []
    check_prefix = tabular._normalize_column_name(definition.source)

    try:
        _validate_sql_identifiers(definition)
        parsed_reference_period = tabular._parse_reference_year(reference_period)
        territory_id, municipality_name, municipality_ibge_code = tabular._resolve_municipality_context(settings)
    except Exception as exc:
        return {
            "job": definition.job_name,
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
        dataset = tabular._resolve_dataset(
            definition=_to_tabular_definition(definition),
            reference_period=parsed_reference_period,
            municipality_name=municipality_name,
            municipality_ibge_code=municipality_ibge_code,
            client=client,
        )
        if dataset is None:
            warnings.append(
                f"No {definition.source} source available (remote catalog and manual directory failed)."
            )
            elapsed = time.perf_counter() - started_at
            if not dry_run:
                with session_scope(settings) as session:
                    upsert_pipeline_run(
                        session=session,
                        run_id=run_id,
                        job_name=definition.job_name,
                        source=definition.source,
                        dataset=definition.dataset_name,
                        wave=definition.wave,
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
                                "name": f"{check_prefix}_source_resolved",
                                "status": "warn",
                                "details": warnings[-1],
                                "observed_value": 0,
                                "threshold_value": 1,
                            },
                            {
                                "name": f"{check_prefix}_social_row_upserted",
                                "status": "warn",
                                "details": "0 social rows written because no source was available.",
                                "observed_value": 0,
                                "threshold_value": 1,
                            },
                        ],
                    )

            return {
                "job": definition.job_name,
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
        rows_extracted = int(len(df))

        municipality_rows = tabular._resolve_municipality_rows(
            df,
            municipality_ibge_code=municipality_ibge_code,
            municipality_name=municipality_name,
            code_columns=definition.municipality_code_columns,
            name_columns=definition.municipality_name_columns,
            source_file_name=source_file_name,
        )
        municipality_rows = tabular._filter_rows_by_reference_year(
            municipality_rows,
            year=parsed_reference_period,
            year_columns=definition.reference_year_columns,
        )
        if not municipality_rows:
            warnings.append(
                f"{definition.source} row not found for municipality code/name "
                f"({municipality_ibge_code}/{municipality_name})."
            )

        metric_values, indicator_rows = _build_metrics_output(
            definition,
            territory_id=territory_id,
            reference_period=parsed_reference_period,
            municipality_rows=municipality_rows,
        )
        social_metrics_populated = sum(1 for value in metric_values.values() if value is not None)

        if dry_run:
            elapsed = time.perf_counter() - started_at
            return {
                "job": definition.job_name,
                "status": "success" if social_metrics_populated > 0 else "blocked",
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
                    "municipality_matches": len(municipality_rows),
                    "metrics_populated": social_metrics_populated,
                    "metrics": {key: (str(value) if value is not None else None) for key, value in metric_values.items()},
                    "indicators": [
                        {"indicator_code": row["indicator_code"], "value": str(row["value"])}
                        for row in indicator_rows
                    ],
                },
            }

        social_rows_written = 0
        if social_metrics_populated > 0:
            social_rows_written = _upsert_social_fact_row(
                settings,
                definition=definition,
                territory_id=territory_id,
                reference_period=parsed_reference_period,
                metric_values=metric_values,
                metadata_json={
                    "source_type": source_type,
                    "source_uri": source_uri,
                    "source_file_name": source_file_name,
                    "rows_extracted": rows_extracted,
                    "municipality_matches": len(municipality_rows),
                },
            )

        indicator_rows_written = tabular._upsert_fact_indicator_rows(settings, indicator_rows)
        total_rows_written = social_rows_written + indicator_rows_written
        status = "success" if social_rows_written > 0 else "blocked"

        checks = [
            {
                "name": f"{check_prefix}_source_resolved",
                "status": "pass" if source_type in {"remote", "manual"} else "warn",
                "details": f"Source type resolved as {source_type}.",
                "observed_value": 1 if source_type in {"remote", "manual"} else 0,
                "threshold_value": 1,
            },
            {
                "name": f"{check_prefix}_municipality_rows_found",
                "status": "pass" if municipality_rows else "warn",
                "details": f"Municipality rows matched: {len(municipality_rows)}.",
                "observed_value": len(municipality_rows),
                "threshold_value": 1,
            },
            {
                "name": f"{check_prefix}_social_row_upserted",
                "status": "pass" if social_rows_written > 0 else "warn",
                "details": f"{social_rows_written} social row(s) written in {definition.fact_table}.",
                "observed_value": social_rows_written,
                "threshold_value": 1,
            },
            {
                "name": f"{check_prefix}_indicator_rows_loaded",
                "status": "pass" if indicator_rows_written > 0 else "warn",
                "details": f"{indicator_rows_written} rows written in silver.fact_indicator.",
                "observed_value": indicator_rows_written,
                "threshold_value": 1,
            },
        ]

        artifact = persist_raw_bytes(
            settings=settings,
            source=definition.source,
            dataset=definition.dataset_name,
            reference_period=parsed_reference_period,
            raw_bytes=raw_bytes,
            extension=source_suffix if source_suffix else ".json",
            uri=source_uri,
            territory_scope=definition.territory_scope,
            dataset_version=definition.dataset_version,
            checks=checks,
            notes=definition.notes,
            run_id=run_id,
            tables_written=(
                [definition.fact_table, "silver.fact_indicator"]
                if social_rows_written > 0
                else ["silver.fact_indicator"] if indicator_rows_written > 0 else []
            ),
            rows_written=(
                [
                    {"table": definition.fact_table, "rows": social_rows_written},
                    {"table": "silver.fact_indicator", "rows": indicator_rows_written},
                ]
                if total_rows_written > 0
                else []
            ),
        )

        finished_at_utc = datetime.now(UTC)
        with session_scope(settings) as session:
            upsert_pipeline_run(
                session=session,
                run_id=run_id,
                job_name=definition.job_name,
                source=definition.source,
                dataset=definition.dataset_name,
                wave=definition.wave,
                reference_period=parsed_reference_period,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
                status=status,
                rows_extracted=rows_extracted,
                rows_loaded=total_rows_written,
                warnings_count=len(warnings),
                errors_count=0,
                bronze_path=artifact.local_path.as_posix(),
                manifest_path=artifact.manifest_path.as_posix(),
                checksum_sha256=artifact.checksum_sha256,
                details={
                    "source_type": source_type,
                    "source_file_name": source_file_name,
                    "social_rows_written": social_rows_written,
                    "indicator_rows_written": indicator_rows_written,
                    "metrics_populated": social_metrics_populated,
                },
            )
            replace_pipeline_checks_from_dicts(session=session, run_id=run_id, checks=checks)

        elapsed = time.perf_counter() - started_at
        logger.info(
            f"{definition.source} social connector finished.",
            run_id=run_id,
            status=status,
            rows_extracted=rows_extracted,
            rows_written=total_rows_written,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": definition.job_name,
            "status": status,
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": rows_extracted,
            "rows_written": total_rows_written,
            "warnings": warnings,
            "errors": errors,
            "bronze": artifact_to_dict(artifact),
        }
    except Exception as exc:  # pragma: no cover - runtime branch
        elapsed = time.perf_counter() - started_at
        errors.append(str(exc))
        if not dry_run:
            try:
                with session_scope(settings) as session:
                    upsert_pipeline_run(
                        session=session,
                        run_id=run_id,
                        job_name=definition.job_name,
                        source=definition.source,
                        dataset=definition.dataset_name,
                        wave=definition.wave,
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
                                "name": f"{check_prefix}_job_exception",
                                "status": "fail",
                                "details": f"{definition.source} connector failed with exception: {exc}",
                                "observed_value": 1,
                                "threshold_value": 0,
                            }
                        ],
                    )
            except Exception:
                logger.exception("Could not persist failed pipeline run in ops tables.", run_id=run_id)

        logger.exception(
            f"{definition.source} social connector failed.",
            run_id=run_id,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": definition.job_name,
            "status": "failed",
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": 0,
            "rows_written": 0,
            "warnings": warnings,
            "errors": errors,
        }
    finally:
        client.close()
