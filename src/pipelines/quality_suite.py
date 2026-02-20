from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.db import session_scope
from app.logging import get_logger
from app.settings import get_settings
from pipelines.common.observability import replace_pipeline_checks, upsert_pipeline_run
from pipelines.common.quality import (
    CheckResult,
    check_dim_territory,
    check_dim_territory_electoral_zone_integrity,
    check_map_layers,
    check_fact_election_result_temporal_coverage,
    check_fact_election_result,
    check_fact_electorate_temporal_coverage,
    check_fact_electorate,
    check_fact_indicator_source_temporal_coverage,
    check_fact_indicator_temporal_coverage,
    check_fact_indicator,
    check_fact_social_assistance_network,
    check_fact_social_protection,
    check_fact_indicator_source_rows,
    check_urban_domain,
    check_ops_pipeline_runs,
)
from pipelines.common.quality_thresholds import load_quality_thresholds

JOB_NAME = "quality_suite"


def _serialize(results: list[CheckResult]) -> list[dict[str, Any]]:
    return [
        {
            "name": result.name,
            "status": result.status,
            "details": result.details,
            "observed_value": result.observed_value,
            "threshold_value": result.threshold_value,
        }
        for result in results
    ]


def run(
    *,
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 3,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    del force, max_retries, timeout_seconds
    logger = get_logger(JOB_NAME)
    run_id = str(uuid4())
    settings = get_settings()
    started_at = datetime.now(UTC)
    if dry_run:
        return {
            "job": JOB_NAME,
            "run_id": run_id,
            "status": "success",
            "results": [],
            "warnings": ["Dry run mode - quality checks skipped."],
            "errors": [],
        }

    thresholds = load_quality_thresholds()
    with session_scope(settings) as session:
        results: list[CheckResult] = []
        results.extend(check_dim_territory(session, settings.municipality_ibge_code, thresholds))
        results.extend(
            check_dim_territory_electoral_zone_integrity(
                session,
                settings.municipality_ibge_code,
                thresholds,
            )
        )
        results.extend(check_map_layers(session, settings.municipality_ibge_code, thresholds))
        results.extend(check_fact_electorate(session, settings.municipality_ibge_code, thresholds))
        results.extend(check_fact_electorate_temporal_coverage(session, thresholds))
        results.extend(check_fact_election_result(session, thresholds))
        results.extend(check_fact_election_result_temporal_coverage(session, thresholds))
        results.extend(check_fact_indicator(session, thresholds))
        results.extend(check_fact_indicator_temporal_coverage(session, thresholds))
        results.extend(check_fact_indicator_source_rows(session, reference_period, thresholds))
        results.extend(check_fact_indicator_source_temporal_coverage(session, thresholds))
        results.extend(check_fact_social_protection(session, thresholds))
        results.extend(check_fact_social_assistance_network(session, thresholds))
        results.extend(check_urban_domain(session, thresholds))
        results.extend(check_ops_pipeline_runs(session, reference_period, thresholds))

    has_fail = any(result.status == "fail" for result in results)
    finished_at = datetime.now(UTC)
    with session_scope(settings) as session:
        upsert_pipeline_run(
            session=session,
            run_id=run_id,
            job_name=JOB_NAME,
            source="INTERNAL",
            dataset="quality_suite",
            wave="MVP-1",
            reference_period=reference_period,
            started_at_utc=started_at,
            finished_at_utc=finished_at,
            status="failed" if has_fail else "success",
            rows_extracted=len(results),
            rows_loaded=len(results),
            warnings_count=sum(1 for result in results if result.status == "warn"),
            errors_count=sum(1 for result in results if result.status == "fail"),
            details={"checks": _serialize(results)},
        )
        replace_pipeline_checks(
            session=session,
            run_id=run_id,
            checks=results,
        )

    logger.info(
        "Quality suite finished.",
        run_id=run_id,
        total_checks=len(results),
        failed_checks=sum(1 for result in results if result.status == "fail"),
        warning_checks=sum(1 for result in results if result.status == "warn"),
    )
    return {
        "job": JOB_NAME,
        "run_id": run_id,
        "status": "failed" if has_fail else "success",
        "results": _serialize(results),
        "warnings": [],
        "errors": [],
    }
