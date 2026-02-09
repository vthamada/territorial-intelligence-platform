from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from pipelines.common.quality import CheckResult


def utc_now() -> datetime:
    return datetime.now(UTC)


def upsert_pipeline_run(
    *,
    session: Session,
    run_id: str,
    job_name: str,
    status: str,
    started_at_utc: datetime,
    finished_at_utc: datetime | None = None,
    reference_period: str | None = None,
    source: str | None = None,
    dataset: str | None = None,
    wave: str | None = None,
    rows_extracted: int = 0,
    rows_loaded: int = 0,
    warnings_count: int = 0,
    errors_count: int = 0,
    bronze_path: str | None = None,
    manifest_path: str | None = None,
    checksum_sha256: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    duration_seconds: Decimal | None = None
    if finished_at_utc is not None:
        duration_seconds = Decimal(str((finished_at_utc - started_at_utc).total_seconds()))

    session.execute(
        text(
            """
            INSERT INTO ops.pipeline_runs (
                run_id,
                job_name,
                source,
                dataset,
                wave,
                reference_period,
                started_at_utc,
                finished_at_utc,
                duration_seconds,
                status,
                rows_extracted,
                rows_loaded,
                warnings_count,
                errors_count,
                bronze_path,
                manifest_path,
                checksum_sha256,
                details
            ) VALUES (
                CAST(:run_id AS uuid),
                :job_name,
                :source,
                :dataset,
                :wave,
                :reference_period,
                :started_at_utc,
                :finished_at_utc,
                :duration_seconds,
                :status,
                :rows_extracted,
                :rows_loaded,
                :warnings_count,
                :errors_count,
                :bronze_path,
                :manifest_path,
                :checksum_sha256,
                CAST(:details AS jsonb)
            )
            ON CONFLICT (run_id) DO UPDATE SET
                job_name = EXCLUDED.job_name,
                source = EXCLUDED.source,
                dataset = EXCLUDED.dataset,
                wave = EXCLUDED.wave,
                reference_period = EXCLUDED.reference_period,
                started_at_utc = EXCLUDED.started_at_utc,
                finished_at_utc = EXCLUDED.finished_at_utc,
                duration_seconds = EXCLUDED.duration_seconds,
                status = EXCLUDED.status,
                rows_extracted = EXCLUDED.rows_extracted,
                rows_loaded = EXCLUDED.rows_loaded,
                warnings_count = EXCLUDED.warnings_count,
                errors_count = EXCLUDED.errors_count,
                bronze_path = EXCLUDED.bronze_path,
                manifest_path = EXCLUDED.manifest_path,
                checksum_sha256 = EXCLUDED.checksum_sha256,
                details = EXCLUDED.details
            """
        ),
        {
            "run_id": run_id,
            "job_name": job_name,
            "source": source,
            "dataset": dataset,
            "wave": wave,
            "reference_period": reference_period,
            "started_at_utc": started_at_utc,
            "finished_at_utc": finished_at_utc,
            "duration_seconds": duration_seconds,
            "status": status,
            "rows_extracted": rows_extracted,
            "rows_loaded": rows_loaded,
            "warnings_count": warnings_count,
            "errors_count": errors_count,
            "bronze_path": bronze_path,
            "manifest_path": manifest_path,
            "checksum_sha256": checksum_sha256,
            "details": "{}" if details is None else json.dumps(details),
        },
    )


def replace_pipeline_checks(
    *,
    session: Session,
    run_id: str,
    checks: list[CheckResult],
) -> None:
    session.execute(
        text("DELETE FROM ops.pipeline_checks WHERE run_id = CAST(:run_id AS uuid)"),
        {"run_id": run_id},
    )
    for check in checks:
        session.execute(
            text(
                """
                INSERT INTO ops.pipeline_checks (
                    run_id,
                    check_name,
                    status,
                    details,
                    observed_value,
                    threshold_value
                ) VALUES (
                    CAST(:run_id AS uuid),
                    :check_name,
                    :status,
                    :details,
                    :observed_value,
                    :threshold_value
                )
                """
            ),
            {
                "run_id": run_id,
                "check_name": check.name,
                "status": check.status,
                "details": check.details,
                "observed_value": check.observed_value,
                "threshold_value": check.threshold_value,
            },
        )


def _as_numeric(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return Decimal(str(value))
    return None


def replace_pipeline_checks_from_dicts(
    *,
    session: Session,
    run_id: str,
    checks: list[dict[str, Any]],
) -> None:
    normalized: list[CheckResult] = []
    for check in checks:
        name = str(check.get("name", "")).strip()
        status = str(check.get("status", "")).strip() or "warn"
        details = str(check.get("details", "")).strip()
        if not name:
            continue
        normalized.append(
            CheckResult(
                name=name,
                status=status,
                details=details,
                observed_value=_as_numeric(check.get("observed_value")),
                threshold_value=_as_numeric(check.get("threshold_value")),
            )
        )
    replace_pipeline_checks(session=session, run_id=run_id, checks=normalized)
