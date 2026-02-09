from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from sqlalchemy import text

from app.db import session_scope
from app.logging import get_logger
from app.settings import Settings, get_settings
from pipelines.common.bronze_store import artifact_to_dict, persist_raw_bytes
from pipelines.common.http_client import HttpClient
from pipelines.common.observability import replace_pipeline_checks_from_dicts, upsert_pipeline_run

JOB_NAME = "ibge_indicators_fetch"
SOURCE = "IBGE"
DATASET_NAME = "ibge_indicadores_municipais"
FACT_DATASET_NAME = "ibge_agregados_api_v3"
WAVE = "MVP-1"
INDICATORS_CATALOG_PATH = Path("configs/indicators_catalog.yml")


def _load_indicators_catalog(path: Path = INDICATORS_CATALOG_PATH) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    indicators = payload.get("indicators", [])
    if not isinstance(indicators, list):
        raise ValueError("Invalid indicators catalog format: 'indicators' must be a list.")
    return [item for item in indicators if isinstance(item, dict)]


def _extract_path(payload: Any, dotted_path: str) -> Any:
    current = payload
    for token in dotted_path.split("."):
        token = token.strip()
        if not token:
            return None
        if isinstance(current, list):
            if not token.isdigit():
                return None
            index = int(token)
            if index < 0 or index >= len(current):
                return None
            current = current[index]
            continue
        if isinstance(current, dict):
            if token not in current:
                return None
            current = current[token]
            continue
        return None
    return current


def _parse_numeric(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return Decimal(str(value))

    text_value = str(value).strip()
    if not text_value or text_value in {"...", "-", "nan", "None"}:
        return None

    normalized = text_value.replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")

    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _extract_series(payload: Any) -> dict[str, Any]:
    series = _extract_path(payload, "0.resultados.0.series.0.serie")
    if isinstance(series, dict):
        return series
    return {}


def _sort_period_keys(periods: list[str]) -> list[str]:
    def _sort_key(period: str) -> tuple[int, str]:
        if period.isdigit():
            return (int(period), period)
        return (-1, period)

    return sorted(periods, key=_sort_key)


def _resolve_indicator_value(
    *,
    payload: Any,
    requested_period: str,
    value_path_template: str,
) -> tuple[Decimal | None, str | None, str | None]:
    explicit_path = value_path_template.format(year=requested_period)
    explicit_raw = _extract_path(payload, explicit_path)
    explicit_value = _parse_numeric(explicit_raw)
    if explicit_value is not None:
        return explicit_value, requested_period, None

    series = _extract_series(payload)
    if not series:
        return None, None, "No indicator series returned by API."

    requested_raw = series.get(requested_period)
    requested_value = _parse_numeric(requested_raw)
    if requested_value is not None:
        return requested_value, requested_period, None

    periods_desc = list(reversed(_sort_period_keys([str(period) for period in series.keys()])))
    for period in periods_desc:
        value = _parse_numeric(series.get(period))
        if value is None:
            continue
        return (
            value,
            period,
            f"Requested period {requested_period} unavailable; using latest available period {period}.",
        )
    return None, None, "Series returned without numeric values."


def _payload_has_rows(payload: Any) -> bool:
    return isinstance(payload, list) and len(payload) > 0


def _fetch_with_period_fallback(
    client: HttpClient,
    endpoint: str,
    requested_period: str,
) -> tuple[Any, str, str | None]:
    payload = client.get_json(endpoint)
    if _payload_has_rows(payload):
        return payload, endpoint, None

    fallback_endpoint = endpoint.replace(f"/periodos/{requested_period}/", "/periodos/all/")
    if fallback_endpoint == endpoint:
        return payload, endpoint, None

    fallback_payload = client.get_json(fallback_endpoint)
    if _payload_has_rows(fallback_payload):
        return (
            fallback_payload,
            fallback_endpoint,
            (
                f"Endpoint for period {requested_period} returned no rows; "
                "used /periodos/all/ fallback."
            ),
        )
    return payload, endpoint, None


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

    catalog = _load_indicators_catalog()
    client = HttpClient.from_settings(
        settings,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
    try:
        with session_scope(settings) as session:
            territory_row = session.execute(
                text(
                    """
                    SELECT territory_id::text
                    FROM silver.dim_territory
                    WHERE level = 'municipality'
                      AND municipality_ibge_code = :municipality_ibge_code
                    ORDER BY updated_at DESC, created_at DESC
                    LIMIT 1
                    """
                ),
                {"municipality_ibge_code": settings.municipality_ibge_code},
            ).first()
        if territory_row is None:
            raise RuntimeError(
                (
                    "Municipality territory not found in silver.dim_territory. "
                    "Run ibge_admin_fetch first."
                )
            )
        municipality_territory_id = str(territory_row[0])

        raw_items: list[dict[str, Any]] = []
        load_rows: list[dict[str, Any]] = []

        for item in catalog:
            indicator_code = str(item.get("indicator_code", "")).strip()
            level = str(item.get("level", "")).strip().lower()
            endpoint_template = str(item.get("endpoint", "")).strip()
            transform_rules = item.get("transform_rules", {})
            value_path_template = (
                str(transform_rules.get("value_path", "")).strip()
                if isinstance(transform_rules, dict)
                else ""
            )
            indicator_name = (
                str(transform_rules.get("indicator_name", "")).strip()
                if isinstance(transform_rules, dict)
                else ""
            )

            if not indicator_code or not endpoint_template or not value_path_template:
                warnings.append(f"Catalog entry skipped due to missing required fields: {item}")
                continue
            if level not in {"municipio", "municipality"}:
                warnings.append(
                    (
                        f"Indicator {indicator_code} skipped: unsupported level '{level}'. "
                        "Current implementation supports municipality level only."
                    )
                )
                continue

            endpoint = endpoint_template.format(
                year=reference_period,
                municipality_ibge_code=settings.municipality_ibge_code,
            )
            try:
                payload, used_endpoint, endpoint_warning = _fetch_with_period_fallback(
                    client,
                    endpoint,
                    reference_period,
                )
                if endpoint_warning:
                    warnings.append(f"{indicator_code}: {endpoint_warning}")
                value, effective_period, value_warning = _resolve_indicator_value(
                    payload=payload,
                    requested_period=reference_period,
                    value_path_template=value_path_template,
                )
                if value_warning:
                    warnings.append(f"{indicator_code}: {value_warning}")

                raw_items.append(
                    {
                        "indicator_code": indicator_code,
                        "requested_endpoint": endpoint,
                        "used_endpoint": used_endpoint,
                        "payload": payload,
                        "status": "ok",
                    }
                )

                if value is None or effective_period is None:
                    continue

                load_rows.append(
                    {
                        "territory_id": municipality_territory_id,
                        "source": SOURCE,
                        "dataset": FACT_DATASET_NAME,
                        "indicator_code": indicator_code,
                        "indicator_name": indicator_name or indicator_code,
                        "unit": str(item.get("unit", "")).strip() or None,
                        "category": str(item.get("periodicity", "")).strip() or None,
                        "value": value,
                        "reference_period": effective_period,
                    }
                )
            except Exception as exc:
                raw_items.append(
                    {
                        "indicator_code": indicator_code,
                        "requested_endpoint": endpoint,
                        "status": "error",
                        "error": str(exc),
                    }
                )
                warnings.append(f"{indicator_code}: request failed ({exc}).")

        if dry_run:
            elapsed = time.perf_counter() - started_at
            return {
                "job": JOB_NAME,
                "status": "success",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": len(raw_items),
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
                "preview": {
                    "indicators_catalog_size": len(catalog),
                    "load_rows_preview": [
                        {
                            "indicator_code": row["indicator_code"],
                            "reference_period": row["reference_period"],
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
                            **row,
                            "value": str(row["value"]),
                        },
                    )
                    rows_written += 1

        bronze_payload = {
            "job": JOB_NAME,
            "requested_reference_period": reference_period,
            "municipality_ibge_code": settings.municipality_ibge_code,
            "catalog_size": len(catalog),
            "rows_extracted": len(raw_items),
            "rows_written": rows_written,
            "items": raw_items,
        }
        raw_bytes = json.dumps(bronze_payload, ensure_ascii=False).encode("utf-8")
        checks = [
            {
                "name": "indicators_catalog_loaded",
                "status": "pass",
                "details": f"{len(catalog)} indicators declared in catalog.",
            },
            {
                "name": "rows_extracted",
                "status": "pass" if raw_items else "warn",
                "details": f"{len(raw_items)} indicators fetched from source.",
            },
            {
                "name": "rows_loaded",
                "status": "pass" if rows_written > 0 else "warn",
                "details": f"{rows_written} rows written to silver.fact_indicator.",
            },
        ]

        artifact = persist_raw_bytes(
            settings=settings,
            source=SOURCE,
            dataset=DATASET_NAME,
            reference_period=reference_period,
            raw_bytes=raw_bytes,
            extension=".json",
            uri="catalog://configs/indicators_catalog.yml",
            territory_scope="municipality",
            dataset_version="api-v3",
            checks=checks,
            notes="IBGE indicators extraction + upsert into silver.fact_indicator.",
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
                reference_period=reference_period,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
                status="success",
                rows_extracted=len(raw_items),
                rows_loaded=rows_written,
                warnings_count=len(warnings),
                errors_count=0,
                bronze_path=artifact.local_path.as_posix(),
                manifest_path=artifact.manifest_path.as_posix(),
                checksum_sha256=artifact.checksum_sha256,
                details={
                    "catalog_size": len(catalog),
                    "rows_written": rows_written,
                },
            )
            replace_pipeline_checks_from_dicts(
                session=session,
                run_id=run_id,
                checks=[
                    {
                        "name": check["name"],
                        "status": check["status"],
                        "details": check["details"],
                    }
                    for check in checks
                ],
            )

        elapsed = time.perf_counter() - started_at
        logger.info(
            "IBGE indicators job finished.",
            run_id=run_id,
            rows_extracted=len(raw_items),
            rows_written=rows_written,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": JOB_NAME,
            "status": "success",
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": len(raw_items),
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
                        reference_period=reference_period,
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
                logger.exception("Could not persist failed pipeline run in ops tables.", run_id=run_id)

        logger.exception(
            "IBGE indicators job failed.",
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
