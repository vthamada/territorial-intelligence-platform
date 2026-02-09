from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from app.db import session_scope
from app.logging import get_logger
from app.settings import Settings, get_settings
from pipelines.common.bronze_store import artifact_to_dict, persist_raw_bytes
from pipelines.common.http_client import HttpClient
from pipelines.common.observability import replace_pipeline_checks_from_dicts, upsert_pipeline_run

JOB_NAME = "finance_siconfi_fetch"
SOURCE = "SICONFI"
DATASET_NAME = "siconfi_dca_finance"
WAVE = "MVP-3"
ANEXOS_ENDPOINT = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/anexos-relatorios"
DCA_ENDPOINT = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca"
DEFAULT_DCA_ANEXOS = ["DCA-Anexo I-AB"]


def _parse_reference_year(reference_period: str) -> int:
    token = str(reference_period).strip()
    if not token:
        raise ValueError("reference_period is empty")
    year_token = token.split("-")[0]
    if not year_token.isdigit() or len(year_token) != 4:
        raise ValueError(f"Invalid reference_period '{reference_period}'. Expected year (YYYY).")
    return int(year_token)


def _candidate_years(reference_year: int, lookback_years: int = 5) -> list[int]:
    return [reference_year - delta for delta in range(lookback_years + 1)]


def _parse_numeric(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return Decimal(str(value))

    token = str(value).strip()
    if not token:
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


def _normalize_indicator_code(*, cod_conta: Any, anexo: str, conta: Any) -> str:
    base = str(cod_conta or "").strip()
    if not base:
        fallback = str(conta or "").strip() or anexo
        base = fallback
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_")
    cleaned = cleaned.upper() if cleaned else "UNKNOWN"
    return f"DCA_{cleaned}"


def _extract_dca_anexos(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    items = payload.get("items")
    if not isinstance(items, list):
        return []
    anexos: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        demonstrativo = str(item.get("demonstrativo", "")).strip().upper()
        anexo = str(item.get("anexo", "")).strip()
        if demonstrativo != "DCA":
            continue
        if not anexo.startswith("DCA-"):
            continue
        anexos.add(anexo)
    return sorted(anexos)


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


def _fetch_dca_items(
    client: HttpClient,
    *,
    municipality_ibge_code: str,
    year: int,
    anexo: str,
    limit: int = 1000,
) -> tuple[list[dict[str, Any]], bool]:
    offset = 0
    items: list[dict[str, Any]] = []
    while True:
        payload = client.get_json(
            DCA_ENDPOINT,
            params={
                "id_ente": municipality_ibge_code,
                "an_exercicio": str(year),
                "co_tipo_demonstrativo": "DCA",
                "no_anexo": anexo,
                "limit": str(limit),
                "offset": str(offset),
            },
        )
        if not isinstance(payload, dict):
            raise ValueError("Invalid SICONFI DCA payload format.")
        page_items = payload.get("items")
        if not isinstance(page_items, list):
            break
        page_rows = [row for row in page_items if isinstance(row, dict)]
        items.extend(page_rows)
        has_more = bool(payload.get("hasMore"))
        if not has_more or not page_rows:
            return items, has_more
        offset += len(page_rows)


def _build_indicator_rows(
    *,
    territory_id: str,
    items: list[dict[str, Any]],
    anexo: str,
    fallback_reference_period: str,
) -> list[dict[str, Any]]:
    aggregated: dict[tuple[str, str, str, str], Decimal] = {}
    for item in items:
        value = _parse_numeric(item.get("valor"))
        if value is None:
            continue
        reference_period = str(item.get("exercicio") or fallback_reference_period).strip()
        indicator_name = str(item.get("conta") or anexo).strip() or anexo
        indicator_code = _normalize_indicator_code(
            cod_conta=item.get("cod_conta"),
            anexo=anexo,
            conta=indicator_name,
        )
        category = f"DCA:{anexo}"
        key = (indicator_code, indicator_name, category, reference_period)
        aggregated[key] = aggregated.get(key, Decimal("0")) + value

    rows: list[dict[str, Any]] = []
    for (indicator_code, indicator_name, category, reference_period), value in sorted(
        aggregated.items(),
        key=lambda entry: entry[0],
    ):
        rows.append(
            {
                "territory_id": territory_id,
                "source": SOURCE,
                "dataset": DATASET_NAME,
                "indicator_code": indicator_code,
                "indicator_name": indicator_name,
                "unit": "BRL",
                "category": category,
                "value": value,
                "reference_period": reference_period,
            }
        )
    return rows


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
        requested_year = _parse_reference_year(reference_period)
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
        anexos_payload = client.get_json(ANEXOS_ENDPOINT, params={"limit": "500"})
        dca_anexos = _extract_dca_anexos(anexos_payload)
        if not dca_anexos:
            dca_anexos = DEFAULT_DCA_ANEXOS[:]
            warnings.append("DCA annex catalog returned empty list; using default annex fallback.")

        rows_extracted = 0
        load_rows: list[dict[str, Any]] = []
        selected_year: int | None = None
        attempts: list[dict[str, Any]] = []
        for year in _candidate_years(requested_year):
            year_rows: list[dict[str, Any]] = []
            year_attempts: list[dict[str, Any]] = []
            for anexo in dca_anexos:
                try:
                    items, has_more = _fetch_dca_items(
                        client,
                        municipality_ibge_code=municipality_ibge_code,
                        year=year,
                        anexo=anexo,
                    )
                    rows_extracted += len(items)
                    built_rows = _build_indicator_rows(
                        territory_id=territory_id,
                        items=items,
                        anexo=anexo,
                        fallback_reference_period=str(year),
                    )
                    year_rows.extend(built_rows)
                    year_attempts.append(
                        {
                            "anexo": anexo,
                            "items_count": len(items),
                            "has_more": has_more,
                            "sample_item": items[0] if items else None,
                        }
                    )
                except Exception as exc:
                    warnings.append(f"year={year} anexo='{anexo}': request failed ({exc}).")
                    year_attempts.append(
                        {
                            "anexo": anexo,
                            "error": str(exc),
                        }
                    )
            attempts.append({"year": year, "anexos": year_attempts})
            if year_rows:
                load_rows = year_rows
                selected_year = year
                if year != requested_year:
                    warnings.append(
                        f"Requested year {requested_year} has no usable data "
                        f"for the municipality; fallback to {year}."
                    )
                break

        if dry_run:
            elapsed = time.perf_counter() - started_at
            return {
                "job": JOB_NAME,
                "status": "success",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": rows_extracted,
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
                "preview": {
                    "requested_year": requested_year,
                    "effective_year": selected_year,
                    "dca_anexos_count": len(dca_anexos),
                    "indicators_count": len(load_rows),
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

        checks = [
            {
                "name": "dca_anexos_loaded",
                "status": "pass" if dca_anexos else "warn",
                "details": f"{len(dca_anexos)} DCA annexes considered for extraction.",
                "observed_value": len(dca_anexos),
                "threshold_value": 1,
            },
            {
                "name": "dca_rows_extracted",
                "status": "pass" if rows_extracted > 0 else "warn",
                "details": f"{rows_extracted} raw rows extracted from SICONFI DCA endpoint.",
                "observed_value": rows_extracted,
                "threshold_value": 1,
            },
            {
                "name": "dca_rows_loaded",
                "status": "pass" if rows_written > 0 else "warn",
                "details": f"{rows_written} rows upserted into silver.fact_indicator.",
                "observed_value": rows_written,
                "threshold_value": 1,
            },
        ]

        bronze_payload = {
            "job": JOB_NAME,
            "municipality_ibge_code": municipality_ibge_code,
            "requested_year": requested_year,
            "effective_year": selected_year,
            "dca_anexos": dca_anexos,
            "attempts": attempts,
            "rows_extracted": rows_extracted,
            "rows_written": rows_written,
        }
        raw_bytes = json.dumps(bronze_payload, ensure_ascii=False).encode("utf-8")
        artifact = persist_raw_bytes(
            settings=settings,
            source=SOURCE,
            dataset=DATASET_NAME,
            reference_period=reference_period,
            raw_bytes=raw_bytes,
            extension=".json",
            uri=DCA_ENDPOINT,
            territory_scope="municipality",
            dataset_version="ords-tt-v1",
            checks=checks,
            notes="SICONFI DCA extraction and Silver upsert for municipality scope.",
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
                rows_extracted=rows_extracted,
                rows_loaded=rows_written,
                warnings_count=len(warnings),
                errors_count=0,
                bronze_path=artifact.local_path.as_posix(),
                manifest_path=artifact.manifest_path.as_posix(),
                checksum_sha256=artifact.checksum_sha256,
                details={
                    "requested_year": requested_year,
                    "effective_year": selected_year,
                    "rows_written": rows_written,
                    "dca_anexos_count": len(dca_anexos),
                },
            )
            replace_pipeline_checks_from_dicts(
                session=session,
                run_id=run_id,
                checks=checks,
            )

        elapsed = time.perf_counter() - started_at
        logger.info(
            "SICONFI finance job finished.",
            run_id=run_id,
            rows_extracted=rows_extracted,
            rows_written=rows_written,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": JOB_NAME,
            "status": "success",
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
                logger.exception(
                    "Could not persist failed pipeline run in ops tables.",
                    run_id=run_id,
                )

        logger.exception(
            "SICONFI finance job failed.",
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
