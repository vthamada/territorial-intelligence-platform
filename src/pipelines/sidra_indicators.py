from __future__ import annotations

import json
import re
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

JOB_NAME = "sidra_indicators_fetch"
SOURCE = "SIDRA"
DATASET_NAME = "sidra_indicators_catalog"
FACT_DATASET_NAME = "sidra_api_values"
WAVE = "MVP-4"
SIDRA_INDICATORS_CATALOG_PATH = Path("configs/sidra_indicators_catalog.yml")


def _load_indicators_catalog(
    path: Path = SIDRA_INDICATORS_CATALOG_PATH,
) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    indicators = payload.get("indicators", [])
    if not isinstance(indicators, list):
        raise ValueError("Invalid SIDRA catalog format: 'indicators' must be a list.")
    return [item for item in indicators if isinstance(item, dict)]


def _parse_numeric(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return Decimal(str(value))

    token = str(value).strip()
    if not token or token in {"...", "-", "nan", "None"}:
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


def _normalize_period_token(raw_period: Any, fallback_period: str) -> str:
    token = str(raw_period or "").strip()
    if not token:
        return fallback_period

    year_match = re.search(r"(19|20)\d{2}", token)
    if year_match:
        return year_match.group(0)
    return fallback_period


def _extract_sidra_value(payload: Any, requested_period: str) -> tuple[Decimal | None, str | None]:
    if not isinstance(payload, list):
        return None, None

    # SIDRA /values endpoints usually return tabular rows; the first row may be metadata.
    for row in reversed(payload):
        if not isinstance(row, dict):
            continue
        value = _parse_numeric(row.get("V"))
        if value is None:
            value = _parse_numeric(row.get("Valor"))
        if value is None:
            continue
        period = _normalize_period_token(row.get("D2N") or row.get("D3N"), requested_period)
        return value, period
    return None, None


def _render_endpoint(
    template: str,
    *,
    municipality_ibge_code: str,
    reference_period: str,
    fallback_period: str,
) -> str:
    return template.format(
        municipality_ibge_code=municipality_ibge_code,
        reference_period=reference_period,
        fallback_period=fallback_period,
    )


def _resolve_municipality_context(settings: Settings) -> tuple[str, str]:
    with session_scope(settings) as session:
        row = session.execute(
            text(
                """
                SELECT territory_id::text, municipality_ibge_code
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
    return str(row[0]).strip(), str(row[1]).strip()


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

    requested_period = str(reference_period).strip()
    if not requested_period:
        return {
            "job": JOB_NAME,
            "status": "failed",
            "run_id": run_id,
            "duration_seconds": 0.0,
            "rows_extracted": 0,
            "rows_written": 0,
            "warnings": warnings,
            "errors": ["reference_period is empty."],
        }

    try:
        catalog = _load_indicators_catalog()
        territory_id, municipality_ibge_code = _resolve_municipality_context(settings)
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
        raw_items: list[dict[str, Any]] = []
        load_rows: list[dict[str, Any]] = []
        request_failures = 0

        for item in catalog:
            indicator_code = str(item.get("indicator_code", "")).strip()
            indicator_name = str(item.get("indicator_name", "")).strip() or indicator_code
            endpoint_template = str(item.get("endpoint", "")).strip()
            fallback_endpoint_template = str(item.get("fallback_endpoint", "")).strip()
            unit = str(item.get("unit", "")).strip() or None
            category = str(item.get("category", "")).strip() or "sidra"

            if not indicator_code or not endpoint_template:
                warnings.append(f"Catalog entry skipped due to missing required fields: {item}")
                continue

            endpoint = _render_endpoint(
                endpoint_template,
                municipality_ibge_code=municipality_ibge_code,
                reference_period=requested_period,
                fallback_period="last%201",
            )

            payload: Any = None
            used_endpoint = endpoint
            try:
                payload = client.get_json(endpoint)
            except Exception as exc:
                if not fallback_endpoint_template:
                    request_failures += 1
                    warnings.append(f"{indicator_code}: primary request failed ({exc}).")
                    raw_items.append(
                        {
                            "indicator_code": indicator_code,
                            "status": "error",
                            "requested_endpoint": endpoint,
                            "error": str(exc),
                        }
                    )
                    continue

                fallback_endpoint = _render_endpoint(
                    fallback_endpoint_template,
                    municipality_ibge_code=municipality_ibge_code,
                    reference_period=requested_period,
                    fallback_period="last%201",
                )
                try:
                    payload = client.get_json(fallback_endpoint)
                    used_endpoint = fallback_endpoint
                    warnings.append(
                        f"{indicator_code}: primary request failed; fallback endpoint used."
                    )
                except Exception as fallback_exc:
                    request_failures += 1
                    warnings.append(
                        f"{indicator_code}: primary and fallback requests failed ({fallback_exc})."
                    )
                    raw_items.append(
                        {
                            "indicator_code": indicator_code,
                            "status": "error",
                            "requested_endpoint": endpoint,
                            "fallback_endpoint": fallback_endpoint,
                            "error": str(fallback_exc),
                        }
                    )
                    continue

            value, effective_period = _extract_sidra_value(payload, requested_period)
            raw_items.append(
                {
                    "indicator_code": indicator_code,
                    "status": "ok" if value is not None else "no_value",
                    "requested_endpoint": endpoint,
                    "used_endpoint": used_endpoint,
                    "rows_count": len(payload) if isinstance(payload, list) else 0,
                }
            )

            if value is None or effective_period is None:
                warnings.append(f"{indicator_code}: no numeric value found in SIDRA payload.")
                continue

            load_rows.append(
                {
                    "territory_id": territory_id,
                    "source": SOURCE,
                    "dataset": FACT_DATASET_NAME,
                    "indicator_code": indicator_code,
                    "indicator_name": indicator_name,
                    "unit": unit,
                    "category": category,
                    "value": value,
                    "reference_period": effective_period,
                }
            )

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
                    "catalog_size": len(catalog),
                    "request_failures": request_failures,
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
                "name": "sidra_catalog_entries",
                "status": "pass" if len(catalog) > 0 else "warn",
                "details": f"{len(catalog)} indicators configured in catalog.",
                "observed_value": len(catalog),
                "threshold_value": 1,
            },
            {
                "name": "sidra_indicator_values_loaded",
                "status": "pass" if rows_written > 0 else "warn",
                "details": f"{rows_written} indicator values loaded into silver.fact_indicator.",
                "observed_value": rows_written,
                "threshold_value": 1,
            },
            {
                "name": "sidra_request_failures",
                "status": "pass" if request_failures == 0 else "warn",
                "details": f"{request_failures} indicator requests failed.",
                "observed_value": request_failures,
                "threshold_value": 0,
            },
        ]

        bronze_payload = {
            "job": JOB_NAME,
            "source": SOURCE,
            "reference_period": requested_period,
            "municipality_ibge_code": municipality_ibge_code,
            "raw_items": raw_items,
            "rows_written": rows_written,
        }
        raw_bytes = json.dumps(bronze_payload, ensure_ascii=False).encode("utf-8")
        artifact = persist_raw_bytes(
            settings=settings,
            source=SOURCE,
            dataset=DATASET_NAME,
            reference_period=requested_period,
            raw_bytes=raw_bytes,
            extension=".json",
            uri="https://apisidra.ibge.gov.br/values",
            territory_scope="municipality",
            dataset_version="sidra-values-v1",
            checks=checks,
            notes="SIDRA values extraction and indicator upsert.",
            run_id=run_id,
            tables_written=["silver.fact_indicator"] if rows_written > 0 else [],
            rows_written=(
                [{"table": "silver.fact_indicator", "rows": rows_written}]
                if rows_written > 0
                else []
            ),
        )

        final_status = "success" if rows_written > 0 else "blocked"
        finished_at_utc = datetime.now(UTC)
        with session_scope(settings) as session:
            upsert_pipeline_run(
                session=session,
                run_id=run_id,
                job_name=JOB_NAME,
                source=SOURCE,
                dataset=DATASET_NAME,
                wave=WAVE,
                reference_period=requested_period,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
                status=final_status,
                rows_extracted=len(raw_items),
                rows_loaded=rows_written,
                warnings_count=len(warnings),
                errors_count=0,
                bronze_path=artifact.local_path.as_posix(),
                manifest_path=artifact.manifest_path.as_posix(),
                checksum_sha256=artifact.checksum_sha256,
                details={
                    "catalog_size": len(catalog),
                    "request_failures": request_failures,
                    "rows_written": rows_written,
                },
            )
            replace_pipeline_checks_from_dicts(
                session=session,
                run_id=run_id,
                checks=checks,
            )

        elapsed = time.perf_counter() - started_at
        logger.info(
            "SIDRA indicators job finished.",
            run_id=run_id,
            status=final_status,
            rows_extracted=len(raw_items),
            rows_written=rows_written,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": JOB_NAME,
            "status": final_status,
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
                        reference_period=requested_period,
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
                                "name": "sidra_job_exception",
                                "status": "fail",
                                "details": f"SIDRA connector failed with exception: {exc}",
                                "observed_value": 1,
                                "threshold_value": 0,
                            }
                        ],
                    )
            except Exception:
                logger.exception(
                    "Could not persist failed pipeline run in ops tables.",
                    run_id=run_id,
                )

        logger.exception(
            "SIDRA indicators job failed.",
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
