from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.db import session_scope
from app.logging import get_logger
from app.settings import Settings, get_settings
from pipelines.common.bronze_store import artifact_to_dict, persist_raw_bytes
from pipelines.common.http_client import HttpClient
from pipelines.common.observability import replace_pipeline_checks_from_dicts, upsert_pipeline_run

JOB_NAME = "tse_catalog_discovery"
SOURCE = "TSE"
DATASET_NAME = "tse_catalog_discovery"
WAVE = "MVP-2"


def _search_catalog(client: HttpClient, base_url: str, query: str, rows: int = 20) -> dict[str, Any]:
    url = f"{base_url}/package_search?q={query}&rows={rows}"
    payload = client.get_json(url)
    if not isinstance(payload, dict):
        raise ValueError("Invalid CKAN response payload.")
    return payload


def _summarize(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = payload.get("result", {})
    if not isinstance(result, dict):
        return []
    packages = result.get("results", [])
    if not isinstance(packages, list):
        return []

    summary: list[dict[str, Any]] = []
    for package in packages:
        if not isinstance(package, dict):
            continue
        resources = package.get("resources", [])
        resources_count = len(resources) if isinstance(resources, list) else 0
        summary.append(
            {
                "id": package.get("id"),
                "name": package.get("name"),
                "title": package.get("title"),
                "resources_count": resources_count,
            }
        )
    return summary


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

    client = HttpClient.from_settings(
        settings,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
    try:
        electorate_query = f"eleitorado {reference_period}"
        results_query = f"resultados {reference_period}"

        electorate_payload = _search_catalog(client, settings.tse_ckan_base_url, electorate_query)
        results_payload = _search_catalog(client, settings.tse_ckan_base_url, results_query)

        electorate_summary = _summarize(electorate_payload)
        results_summary = _summarize(results_payload)
        if not electorate_summary:
            warnings.append(f"No catalog entries returned for query '{electorate_query}'.")
        if not results_summary:
            warnings.append(f"No catalog entries returned for query '{results_query}'.")

        bronze_payload = {
            "job": JOB_NAME,
            "reference_period": reference_period,
            "queries": {
                "electorate": electorate_query,
                "results": results_query,
            },
            "catalog": {
                "electorate": electorate_payload,
                "results": results_payload,
            },
            "summary": {
                "electorate": electorate_summary,
                "results": results_summary,
            },
        }
        raw_bytes = json.dumps(bronze_payload, ensure_ascii=False).encode("utf-8")

        rows_extracted = len(electorate_summary) + len(results_summary)
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
                "summary": bronze_payload["summary"],
            }

        checks = [
            {
                "name": "electorate_catalog_results",
                "status": "pass" if electorate_summary else "warn",
                "details": f"{len(electorate_summary)} catalog entries found for electorate query.",
            },
            {
                "name": "results_catalog_results",
                "status": "pass" if results_summary else "warn",
                "details": f"{len(results_summary)} catalog entries found for results query.",
            },
        ]
        artifact = persist_raw_bytes(
            settings=settings,
            source=SOURCE,
            dataset=DATASET_NAME,
            reference_period=reference_period,
            raw_bytes=raw_bytes,
            extension=".json",
            uri=f"ckan://package_search?period={reference_period}",
            territory_scope="national",
            dataset_version="api-v3",
            checks=checks,
            notes="TSE CKAN discovery payload for electorate and election results datasets.",
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
                reference_period=reference_period,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
                status="success",
                rows_extracted=rows_extracted,
                rows_loaded=0,
                warnings_count=len(warnings),
                errors_count=0,
                bronze_path=artifact.local_path.as_posix(),
                manifest_path=artifact.manifest_path.as_posix(),
                checksum_sha256=artifact.checksum_sha256,
                details={
                    "electorate_matches": len(electorate_summary),
                    "results_matches": len(results_summary),
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
            "TSE catalog discovery finished.",
            run_id=run_id,
            rows_extracted=rows_extracted,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": JOB_NAME,
            "status": "success",
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": rows_extracted,
            "rows_written": 0,
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
            "TSE catalog discovery failed.",
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
