from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from app.db import session_scope
from app.logging import get_logger
from app.settings import Settings
from pipelines.common.bronze_store import artifact_to_dict, persist_raw_bytes
from pipelines.common.http_client import HttpClient
from pipelines.common.observability import replace_pipeline_checks_from_dicts, upsert_pipeline_run


def _resolve_municipality(settings: Settings) -> tuple[str, str]:
    with session_scope(settings) as session:
        row = session.execute(
            text(
                """
                SELECT territory_id::text, name
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
    return str(row[0]), str(row[1]).strip()


def _extract_numeric_probe_value(payload: Any) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        if isinstance(payload.get("items"), list):
            return len(payload["items"])
        result = payload.get("result")
        if isinstance(result, dict):
            if isinstance(result.get("results"), list):
                return len(result["results"])
            if isinstance(result.get("count"), (int, float)):
                return int(result["count"])
        if isinstance(payload.get("count"), (int, float)):
            return int(payload["count"])
    return 0


def _extract_html_probe_value(text_payload: str) -> int:
    matches = re.findall(r"<a\b", text_payload, flags=re.IGNORECASE)
    return len(matches)


def run_source_probe_job(
    *,
    job_name: str,
    source: str,
    dataset_name: str,
    indicator_code: str,
    indicator_name: str,
    probe_urls: list[str],
    reference_period: str,
    wave: str,
    settings: Settings,
    dry_run: bool,
    max_retries: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    logger = get_logger(job_name)
    run_id = str(uuid4())
    started_at_utc = datetime.now(UTC)
    started_at = time.perf_counter()
    warnings: list[str] = []

    territory_id, municipality_name = _resolve_municipality(settings)
    client = HttpClient.from_settings(
        settings,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
    try:
        probes: list[dict[str, Any]] = []
        successful_values: list[int] = []

        for url in probe_urls:
            try:
                response = client._request("GET", url)  # noqa: SLF001 - shared low-level probe
                content_type = response.headers.get("content-type", "").lower()
                body_text = response.text

                if "json" in content_type:
                    parsed = response.json()
                    value = _extract_numeric_probe_value(parsed)
                    sample = json.dumps(parsed, ensure_ascii=False)[:300]
                else:
                    value = _extract_html_probe_value(body_text)
                    sample = body_text[:300]

                successful_values.append(max(value, 0))
                probes.append(
                    {
                        "url": url,
                        "status": "ok",
                        "status_code": response.status_code,
                        "content_type": content_type,
                        "observed_value": value,
                        "sample": sample,
                    }
                )
            except Exception as exc:
                warnings.append(f"Probe failed for {url}: {exc}")
                probes.append(
                    {
                        "url": url,
                        "status": "error",
                        "error": str(exc),
                    }
                )

        observed_value = max(successful_values) if successful_values else 0
        if not successful_values:
            warnings.append("No probe endpoint succeeded; storing value=0.")

        bronze_payload = {
            "job": job_name,
            "source": source,
            "reference_period": reference_period,
            "municipality": municipality_name,
            "probes": probes,
            "observed_value": observed_value,
        }
        raw_bytes = json.dumps(bronze_payload, ensure_ascii=False).encode("utf-8")

        if dry_run:
            elapsed = time.perf_counter() - started_at
            return {
                "job": job_name,
                "status": "success",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": len(probes),
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
                "preview": {
                    "indicator_code": indicator_code,
                    "value": observed_value,
                    "successful_probes": len(successful_values),
                },
            }

        with session_scope(settings) as session:
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
                    "territory_id": territory_id,
                    "source": source,
                    "dataset": dataset_name,
                    "indicator_code": indicator_code,
                    "indicator_name": indicator_name,
                    "unit": "count",
                    "category": "source_probe",
                    "value": str(Decimal(observed_value)),
                    "reference_period": reference_period,
                },
            )

        checks = [
            {
                "name": "probe_success_count",
                "status": "pass" if successful_values else "warn",
                "details": f"{len(successful_values)} successful probes.",
            },
            {
                "name": "indicator_value_non_negative",
                "status": "pass" if observed_value >= 0 else "fail",
                "details": f"Observed value={observed_value}.",
            },
        ]
        artifact = persist_raw_bytes(
            settings=settings,
            source=source,
            dataset=dataset_name,
            reference_period=reference_period,
            raw_bytes=raw_bytes,
            extension=".json",
            uri=probe_urls[0] if probe_urls else "probe://none",
            territory_scope="municipality",
            dataset_version="source-probe-v1",
            checks=checks,
            notes=f"{job_name} probe snapshot and indicator upsert.",
            run_id=run_id,
            tables_written=["silver.fact_indicator"],
            rows_written=[{"table": "silver.fact_indicator", "rows": 1}],
        )

        finished_at_utc = datetime.now(UTC)
        with session_scope(settings) as session:
            upsert_pipeline_run(
                session=session,
                run_id=run_id,
                job_name=job_name,
                source=source,
                dataset=dataset_name,
                wave=wave,
                reference_period=reference_period,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
                status="success",
                rows_extracted=len(probes),
                rows_loaded=1,
                warnings_count=len(warnings),
                errors_count=0,
                bronze_path=artifact.local_path.as_posix(),
                manifest_path=artifact.manifest_path.as_posix(),
                checksum_sha256=artifact.checksum_sha256,
                details={
                    "indicator_code": indicator_code,
                    "observed_value": observed_value,
                    "successful_probes": len(successful_values),
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
            f"{job_name} finished.",
            run_id=run_id,
            rows_extracted=len(probes),
            rows_written=1,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": job_name,
            "status": "success",
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": len(probes),
            "rows_written": 1,
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
                        job_name=job_name,
                        source=source,
                        dataset=dataset_name,
                        wave=wave,
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
            f"{job_name} failed.",
            run_id=run_id,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": job_name,
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
