from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from app.db import session_scope
from app.logging import get_logger
from app.settings import Settings, get_settings
from pipelines.common.bronze_store import artifact_to_dict, persist_raw_bytes
from pipelines.common.http_client import HttpClient
from pipelines.common.observability import replace_pipeline_checks_from_dicts, upsert_pipeline_run

JOB_NAME = "health_datasus_fetch"
SOURCE = "DATASUS"
DATASET_NAME = "datasus_cnes_estabelecimentos"
WAVE = "MVP-3"
CNES_ENDPOINT = "https://apidadosabertos.saude.gov.br/cnes/estabelecimentos"
CNES_PAGE_SIZE = 20
MAX_PAGES = 500
_CNES_QUERY_PARAM_CANDIDATES: tuple[str, ...] = ("codigo_municipio", "municipio")


def _parse_reference_year(reference_period: str) -> str:
    token = str(reference_period).strip()
    if not token:
        raise ValueError("reference_period is empty")
    return token.split("-")[0]


def _to_cnes_municipality_code(ibge_code: str) -> str:
    token = str(ibge_code).strip()
    if len(token) < 6 or not token[:6].isdigit():
        raise ValueError(f"Invalid municipality code '{ibge_code}'.")
    return token[:6]


def _is_truthy_flag(value: Any) -> bool:
    token = str(value).strip().casefold()
    return token in {"1", "s", "sim", "true", "t", "y", "yes"}


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

    territory_id = str(row[0]).strip()
    municipality_ibge_code = str(row[1]).strip()
    if not territory_id or not municipality_ibge_code:
        raise RuntimeError("Invalid municipality context in dim_territory.")
    return territory_id, municipality_ibge_code


def _fetch_establishments(
    client: HttpClient,
    *,
    municipality_cnes_code: str,
    municipality_ibge_code: str,
    page_size: int = CNES_PAGE_SIZE,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    municipality_code_candidates = [
        municipality_cnes_code,
        municipality_ibge_code,
        f"0{municipality_cnes_code}",
    ]
    unique_codes = [code for idx, code in enumerate(municipality_code_candidates) if code and code not in municipality_code_candidates[:idx]]

    first_empty_details: dict[str, str] | None = None
    last_error: Exception | None = None

    for query_param in _CNES_QUERY_PARAM_CANDIDATES:
        for municipality_code in unique_codes:
            try:
                rows = _fetch_establishments_once(
                    client,
                    municipality_code=municipality_code,
                    query_param=query_param,
                    page_size=page_size,
                )
            except Exception as exc:
                last_error = exc
                continue

            details = {
                "query_param": query_param,
                "municipality_code": municipality_code,
            }
            if rows:
                return rows, details
            if first_empty_details is None:
                first_empty_details = details

    if first_empty_details is not None:
        return [], first_empty_details
    if last_error is not None:
        raise RuntimeError(
            "DATASUS CNES request failed for all municipality query strategies."
        ) from last_error
    return [], {"query_param": "codigo_municipio", "municipality_code": municipality_cnes_code}


def _fetch_establishments_once(
    client: HttpClient,
    *,
    municipality_code: str,
    query_param: str,
    page_size: int = CNES_PAGE_SIZE,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0

    for _ in range(MAX_PAGES):
        payload = client.get_json(
            CNES_ENDPOINT,
            params={
                query_param: municipality_code,
                "limit": str(page_size),
                "offset": str(offset),
            },
        )
        if not isinstance(payload, dict):
            raise ValueError("Invalid DATASUS CNES payload format.")

        page_rows = payload.get("estabelecimentos")
        if not isinstance(page_rows, list):
            break
        page_dict_rows = [row for row in page_rows if isinstance(row, dict)]
        if not page_dict_rows:
            break

        rows.extend(page_dict_rows)
        if len(page_dict_rows) < page_size:
            break
        offset += page_size

    return rows


def _build_indicator_rows(
    *,
    territory_id: str,
    reference_period: str,
    establishments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    unique_by_cnes: dict[str, dict[str, Any]] = {}
    for row in establishments:
        cnes = str(row.get("codigo_cnes", "")).strip()
        if not cnes:
            continue
        unique_by_cnes.setdefault(cnes, row)

    unique_rows = list(unique_by_cnes.values())
    total = len(unique_rows)
    ambulatory_sus = sum(
        1
        for row in unique_rows
        if _is_truthy_flag(row.get("estabelecimento_faz_atendimento_ambulatorial_sus"))
    )
    hospital = sum(
        1
        for row in unique_rows
        if _is_truthy_flag(row.get("estabelecimento_possui_atendimento_hospitalar"))
    )
    surgery_center = sum(
        1
        for row in unique_rows
        if _is_truthy_flag(row.get("estabelecimento_possui_centro_cirurgico"))
    )

    metrics = [
        (
            "DATASUS_CNES_ESTABLISHMENTS_TOTAL",
            "DATASUS CNES establishments total",
            total,
        ),
        (
            "DATASUS_CNES_AMBULATORY_SUS_TOTAL",
            "DATASUS CNES establishments with SUS ambulatory care",
            ambulatory_sus,
        ),
        (
            "DATASUS_CNES_HOSPITAL_CARE_TOTAL",
            "DATASUS CNES establishments with hospital care",
            hospital,
        ),
        (
            "DATASUS_CNES_SURGERY_CENTER_TOTAL",
            "DATASUS CNES establishments with surgery center",
            surgery_center,
        ),
    ]

    return [
        {
            "territory_id": territory_id,
            "source": SOURCE,
            "dataset": DATASET_NAME,
            "indicator_code": indicator_code,
            "indicator_name": indicator_name,
            "unit": "count",
            "category": "cnes_establishments",
            "value": Decimal(value),
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
        parsed_reference_period = _parse_reference_year(reference_period)
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
        territory_id, municipality_ibge_code = _resolve_municipality_context(settings)
        municipality_cnes_code = _to_cnes_municipality_code(municipality_ibge_code)
        establishments, query_details = _fetch_establishments(
            client,
            municipality_cnes_code=municipality_cnes_code,
            municipality_ibge_code=municipality_ibge_code,
        )
        if not establishments:
            warnings.append(
                f"No CNES establishments found for municipality code "
                f"{municipality_cnes_code}."
            )
        if query_details["query_param"] != "codigo_municipio" or query_details["municipality_code"] != municipality_cnes_code:
            warnings.append(
                "DATASUS query fallback used: "
                f"{query_details['query_param']}={query_details['municipality_code']}."
            )

        load_rows = _build_indicator_rows(
            territory_id=territory_id,
            reference_period=parsed_reference_period,
            establishments=establishments,
        )

        if dry_run:
            elapsed = time.perf_counter() - started_at
            return {
                "job": JOB_NAME,
                "status": "success",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": len(establishments),
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
                "preview": {
                    "municipality_ibge_code": municipality_ibge_code,
                    "municipality_cnes_code": municipality_cnes_code,
                    "query_details": query_details,
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
                "name": "cnes_rows_extracted",
                "status": "pass" if establishments else "warn",
                "details": f"{len(establishments)} CNES rows extracted.",
                "observed_value": len(establishments),
                "threshold_value": 1,
            },
            {
                "name": "cnes_indicators_loaded",
                "status": "pass" if rows_written > 0 else "warn",
                "details": f"{rows_written} indicators upserted into silver.fact_indicator.",
                "observed_value": rows_written,
                "threshold_value": 1,
            },
        ]

        bronze_payload = {
            "job": JOB_NAME,
            "municipality_ibge_code": municipality_ibge_code,
            "municipality_cnes_code": municipality_cnes_code,
            "query_details": query_details,
            "reference_period": parsed_reference_period,
            "rows_extracted": len(establishments),
            "sample_rows": establishments[:5],
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
            uri=CNES_ENDPOINT,
            territory_scope="municipality",
            dataset_version="api-v1",
            checks=checks,
            notes="DATASUS CNES establishments extraction and indicator upsert.",
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
                rows_extracted=len(establishments),
                rows_loaded=rows_written,
                warnings_count=len(warnings),
                errors_count=0,
                bronze_path=artifact.local_path.as_posix(),
                manifest_path=artifact.manifest_path.as_posix(),
                checksum_sha256=artifact.checksum_sha256,
                details={
                    "municipality_ibge_code": municipality_ibge_code,
                    "municipality_cnes_code": municipality_cnes_code,
                    "query_details": query_details,
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
            "DATASUS health job finished.",
            run_id=run_id,
            rows_extracted=len(establishments),
            rows_written=rows_written,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": JOB_NAME,
            "status": "success",
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": len(establishments),
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
            "DATASUS health job failed.",
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
