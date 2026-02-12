from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.utils import normalize_pagination
from app.schemas.responses import PaginatedResponse

router = APIRouter(prefix="/ops", tags=["ops"])


class FrontendEventIn(BaseModel):
    category: str = Field(
        pattern="^(frontend_error|web_vital|performance|lifecycle|api_request)$"
    )
    name: str = Field(min_length=1, max_length=120)
    severity: str = Field(pattern="^(info|warn|error)$")
    attributes: dict[str, Any] | None = None
    timestamp_utc: datetime


class FrontendEventIngestResponse(BaseModel):
    status: str
    event_id: int


def _aggregate_timeseries_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[datetime, dict[str, Any]] = {}
    for row in rows:
        bucket = row["bucket_start_utc"]
        status = row["status"] or "unknown"
        count = int(row["count"])

        item = buckets.setdefault(
            bucket,
            {"bucket_start_utc": bucket, "total": 0, "by_status": {}},
        )
        item["total"] += count
        by_status = item["by_status"]
        by_status[status] = by_status.get(status, 0) + count

    return [buckets[key] for key in sorted(buckets)]


@router.get("/pipeline-runs", response_model=PaginatedResponse)
def list_pipeline_runs(
    run_id: str | None = Query(default=None),
    job_name: str | None = Query(default=None),
    run_status: str | None = Query(default=None),
    status: str | None = Query(default=None),
    source: str | None = Query(default=None),
    dataset: str | None = Query(default=None),
    wave: str | None = Query(default=None),
    reference_period: str | None = Query(default=None),
    started_from: datetime | None = Query(default=None),  # noqa: B008
    started_to: datetime | None = Query(default=None),  # noqa: B008
    page: int = Query(default=1),
    page_size: int = Query(default=100),
    db: Session = Depends(get_db),  # noqa: B008
) -> PaginatedResponse:
    page, page_size, offset = normalize_pagination(page, page_size)
    effective_status = run_status if run_status is not None else status
    params = {
        "run_id": run_id,
        "job_name": job_name,
        "status": effective_status,
        "source": source,
        "dataset": dataset,
        "wave": wave,
        "reference_period": reference_period,
        "started_from": started_from,
        "started_to": started_to,
        "limit": page_size,
        "offset": offset,
    }

    total = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM ops.pipeline_runs
            WHERE (CAST(:run_id AS TEXT) IS NULL OR run_id::text = CAST(:run_id AS TEXT))
              AND (CAST(:job_name AS TEXT) IS NULL OR job_name = CAST(:job_name AS TEXT))
              AND (CAST(:status AS TEXT) IS NULL OR status = CAST(:status AS TEXT))
              AND (CAST(:source AS TEXT) IS NULL OR source = CAST(:source AS TEXT))
              AND (CAST(:dataset AS TEXT) IS NULL OR dataset = CAST(:dataset AS TEXT))
              AND (CAST(:wave AS TEXT) IS NULL OR wave = CAST(:wave AS TEXT))
              AND (
                    CAST(:reference_period AS TEXT) IS NULL
                    OR reference_period = CAST(:reference_period AS TEXT)
                  )
              AND (CAST(:started_from AS TIMESTAMPTZ) IS NULL OR started_at_utc >= CAST(:started_from AS TIMESTAMPTZ))
              AND (CAST(:started_to AS TIMESTAMPTZ) IS NULL OR started_at_utc <= CAST(:started_to AS TIMESTAMPTZ))
            """
        ),
        params,
    ).scalar_one()

    rows = db.execute(
        text(
            """
            SELECT
                run_id::text AS run_id,
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
            FROM ops.pipeline_runs
            WHERE (CAST(:run_id AS TEXT) IS NULL OR run_id::text = CAST(:run_id AS TEXT))
              AND (CAST(:job_name AS TEXT) IS NULL OR job_name = CAST(:job_name AS TEXT))
              AND (CAST(:status AS TEXT) IS NULL OR status = CAST(:status AS TEXT))
              AND (CAST(:source AS TEXT) IS NULL OR source = CAST(:source AS TEXT))
              AND (CAST(:dataset AS TEXT) IS NULL OR dataset = CAST(:dataset AS TEXT))
              AND (CAST(:wave AS TEXT) IS NULL OR wave = CAST(:wave AS TEXT))
              AND (
                    CAST(:reference_period AS TEXT) IS NULL
                    OR reference_period = CAST(:reference_period AS TEXT)
                  )
              AND (CAST(:started_from AS TIMESTAMPTZ) IS NULL OR started_at_utc >= CAST(:started_from AS TIMESTAMPTZ))
              AND (CAST(:started_to AS TIMESTAMPTZ) IS NULL OR started_at_utc <= CAST(:started_to AS TIMESTAMPTZ))
            ORDER BY started_at_utc DESC, run_id DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()

    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total=total,
        items=[dict(row) for row in rows],
    )


@router.post("/frontend-events", status_code=202, response_model=FrontendEventIngestResponse)
def ingest_frontend_event(
    payload: FrontendEventIn,
    request: Request,
    db: Session = Depends(get_db),  # noqa: B008
) -> FrontendEventIngestResponse:
    event_id = db.execute(
        text(
            """
            INSERT INTO ops.frontend_events (
                category,
                name,
                severity,
                attributes,
                event_timestamp_utc,
                request_id,
                user_agent
            ) VALUES (
                :category,
                :name,
                :severity,
                CAST(:attributes AS JSONB),
                CAST(:event_timestamp_utc AS TIMESTAMPTZ),
                CAST(:request_id AS TEXT),
                CAST(:user_agent AS TEXT)
            )
            RETURNING event_id
            """
        ),
        {
            "category": payload.category,
            "name": payload.name,
            "severity": payload.severity,
            "attributes": payload.attributes or {},
            "event_timestamp_utc": payload.timestamp_utc,
            "request_id": getattr(request.state, "request_id", None),
            "user_agent": request.headers.get("user-agent"),
        },
    ).scalar_one()
    return FrontendEventIngestResponse(status="accepted", event_id=int(event_id))


@router.get("/frontend-events", response_model=PaginatedResponse)
def list_frontend_events(
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    name: str | None = Query(default=None),
    event_from: datetime | None = Query(default=None),  # noqa: B008
    event_to: datetime | None = Query(default=None),  # noqa: B008
    page: int = Query(default=1),
    page_size: int = Query(default=100),
    db: Session = Depends(get_db),  # noqa: B008
) -> PaginatedResponse:
    page, page_size, offset = normalize_pagination(page, page_size)
    params = {
        "category": category,
        "severity": severity,
        "name": name,
        "event_from": event_from,
        "event_to": event_to,
        "limit": page_size,
        "offset": offset,
    }

    total = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM ops.frontend_events fe
            WHERE (CAST(:category AS TEXT) IS NULL OR fe.category = CAST(:category AS TEXT))
              AND (CAST(:severity AS TEXT) IS NULL OR fe.severity = CAST(:severity AS TEXT))
              AND (CAST(:name AS TEXT) IS NULL OR fe.name = CAST(:name AS TEXT))
              AND (
                    CAST(:event_from AS TIMESTAMPTZ) IS NULL
                    OR fe.event_timestamp_utc >= CAST(:event_from AS TIMESTAMPTZ)
                  )
              AND (
                    CAST(:event_to AS TIMESTAMPTZ) IS NULL
                    OR fe.event_timestamp_utc <= CAST(:event_to AS TIMESTAMPTZ)
                  )
            """
        ),
        params,
    ).scalar_one()

    rows = db.execute(
        text(
            """
            SELECT
                fe.event_id,
                fe.category,
                fe.name,
                fe.severity,
                fe.attributes,
                fe.event_timestamp_utc,
                fe.received_at_utc,
                fe.request_id,
                fe.user_agent
            FROM ops.frontend_events fe
            WHERE (CAST(:category AS TEXT) IS NULL OR fe.category = CAST(:category AS TEXT))
              AND (CAST(:severity AS TEXT) IS NULL OR fe.severity = CAST(:severity AS TEXT))
              AND (CAST(:name AS TEXT) IS NULL OR fe.name = CAST(:name AS TEXT))
              AND (
                    CAST(:event_from AS TIMESTAMPTZ) IS NULL
                    OR fe.event_timestamp_utc >= CAST(:event_from AS TIMESTAMPTZ)
                  )
              AND (
                    CAST(:event_to AS TIMESTAMPTZ) IS NULL
                    OR fe.event_timestamp_utc <= CAST(:event_to AS TIMESTAMPTZ)
                  )
            ORDER BY fe.event_timestamp_utc DESC, fe.event_id DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()

    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total=total,
        items=[dict(row) for row in rows],
    )


@router.get("/pipeline-checks", response_model=PaginatedResponse)
def list_pipeline_checks(
    run_id: str | None = Query(default=None),
    job_name: str | None = Query(default=None),
    status: str | None = Query(default=None),
    check_name: str | None = Query(default=None),
    created_from: datetime | None = Query(default=None),  # noqa: B008
    created_to: datetime | None = Query(default=None),  # noqa: B008
    page: int = Query(default=1),
    page_size: int = Query(default=100),
    db: Session = Depends(get_db),  # noqa: B008
) -> PaginatedResponse:
    page, page_size, offset = normalize_pagination(page, page_size)
    params = {
        "run_id": run_id,
        "job_name": job_name,
        "status": status,
        "check_name": check_name,
        "created_from": created_from,
        "created_to": created_to,
        "limit": page_size,
        "offset": offset,
    }

    total = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM ops.pipeline_checks pc
            JOIN ops.pipeline_runs pr ON pr.run_id = pc.run_id
            WHERE (CAST(:run_id AS TEXT) IS NULL OR pc.run_id::text = CAST(:run_id AS TEXT))
              AND (CAST(:job_name AS TEXT) IS NULL OR pr.job_name = CAST(:job_name AS TEXT))
              AND (CAST(:status AS TEXT) IS NULL OR pc.status = CAST(:status AS TEXT))
              AND (CAST(:check_name AS TEXT) IS NULL OR pc.check_name = CAST(:check_name AS TEXT))
              AND (CAST(:created_from AS TIMESTAMPTZ) IS NULL OR pc.created_at_utc >= CAST(:created_from AS TIMESTAMPTZ))
              AND (CAST(:created_to AS TIMESTAMPTZ) IS NULL OR pc.created_at_utc <= CAST(:created_to AS TIMESTAMPTZ))
            """
        ),
        params,
    ).scalar_one()

    rows = db.execute(
        text(
            """
            SELECT
                pc.check_id,
                pc.run_id::text AS run_id,
                pr.job_name,
                pr.source,
                pr.dataset,
                pr.wave,
                pr.reference_period,
                pc.check_name,
                pc.status,
                pc.details,
                pc.observed_value,
                pc.threshold_value,
                pc.created_at_utc
            FROM ops.pipeline_checks pc
            JOIN ops.pipeline_runs pr ON pr.run_id = pc.run_id
            WHERE (CAST(:run_id AS TEXT) IS NULL OR pc.run_id::text = CAST(:run_id AS TEXT))
              AND (CAST(:job_name AS TEXT) IS NULL OR pr.job_name = CAST(:job_name AS TEXT))
              AND (CAST(:status AS TEXT) IS NULL OR pc.status = CAST(:status AS TEXT))
              AND (CAST(:check_name AS TEXT) IS NULL OR pc.check_name = CAST(:check_name AS TEXT))
              AND (CAST(:created_from AS TIMESTAMPTZ) IS NULL OR pc.created_at_utc >= CAST(:created_from AS TIMESTAMPTZ))
              AND (CAST(:created_to AS TIMESTAMPTZ) IS NULL OR pc.created_at_utc <= CAST(:created_to AS TIMESTAMPTZ))
            ORDER BY pc.created_at_utc DESC, pc.check_id DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()

    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total=total,
        items=[dict(row) for row in rows],
    )


@router.get("/connector-registry", response_model=PaginatedResponse)
def list_connector_registry(
    connector_name: str | None = Query(default=None),
    source: str | None = Query(default=None),
    wave: str | None = Query(default=None),
    status: str | None = Query(default=None),
    updated_from: datetime | None = Query(default=None),  # noqa: B008
    updated_to: datetime | None = Query(default=None),  # noqa: B008
    page: int = Query(default=1),
    page_size: int = Query(default=100),
    db: Session = Depends(get_db),  # noqa: B008
) -> PaginatedResponse:
    page, page_size, offset = normalize_pagination(page, page_size)
    params = {
        "connector_name": connector_name,
        "source": source,
        "wave": wave,
        "status": status,
        "updated_from": updated_from,
        "updated_to": updated_to,
        "limit": page_size,
        "offset": offset,
    }

    total = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM ops.connector_registry
            WHERE (
                    CAST(:connector_name AS TEXT) IS NULL
                    OR connector_name = CAST(:connector_name AS TEXT)
                  )
              AND (CAST(:source AS TEXT) IS NULL OR source = CAST(:source AS TEXT))
              AND (CAST(:wave AS TEXT) IS NULL OR wave = CAST(:wave AS TEXT))
              AND (CAST(:status AS TEXT) IS NULL OR status::text = CAST(:status AS TEXT))
              AND (CAST(:updated_from AS TIMESTAMPTZ) IS NULL OR updated_at_utc >= CAST(:updated_from AS TIMESTAMPTZ))
              AND (CAST(:updated_to AS TIMESTAMPTZ) IS NULL OR updated_at_utc <= CAST(:updated_to AS TIMESTAMPTZ))
            """
        ),
        params,
    ).scalar_one()

    rows = db.execute(
        text(
            """
            SELECT
                connector_name,
                source,
                wave,
                status::text AS status,
                notes,
                updated_at_utc
            FROM ops.connector_registry
            WHERE (
                    CAST(:connector_name AS TEXT) IS NULL
                    OR connector_name = CAST(:connector_name AS TEXT)
                  )
              AND (CAST(:source AS TEXT) IS NULL OR source = CAST(:source AS TEXT))
              AND (CAST(:wave AS TEXT) IS NULL OR wave = CAST(:wave AS TEXT))
              AND (CAST(:status AS TEXT) IS NULL OR status::text = CAST(:status AS TEXT))
              AND (CAST(:updated_from AS TIMESTAMPTZ) IS NULL OR updated_at_utc >= CAST(:updated_from AS TIMESTAMPTZ))
              AND (CAST(:updated_to AS TIMESTAMPTZ) IS NULL OR updated_at_utc <= CAST(:updated_to AS TIMESTAMPTZ))
            ORDER BY wave, connector_name
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()

    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total=total,
        items=[dict(row) for row in rows],
    )


@router.get("/summary")
def get_ops_summary(
    job_name: str | None = Query(default=None),
    source: str | None = Query(default=None),
    dataset: str | None = Query(default=None),
    wave: str | None = Query(default=None),
    reference_period: str | None = Query(default=None),
    run_status: str | None = Query(default=None),
    check_status: str | None = Query(default=None),
    connector_status: str | None = Query(default=None),
    started_from: datetime | None = Query(default=None),  # noqa: B008
    started_to: datetime | None = Query(default=None),  # noqa: B008
    created_from: datetime | None = Query(default=None),  # noqa: B008
    created_to: datetime | None = Query(default=None),  # noqa: B008
    updated_from: datetime | None = Query(default=None),  # noqa: B008
    updated_to: datetime | None = Query(default=None),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    params = {
        "job_name": job_name,
        "source": source,
        "dataset": dataset,
        "wave": wave,
        "reference_period": reference_period,
        "run_status": run_status,
        "check_status": check_status,
        "connector_status": connector_status,
        "started_from": started_from,
        "started_to": started_to,
        "created_from": created_from,
        "created_to": created_to,
        "updated_from": updated_from,
        "updated_to": updated_to,
    }

    runs_total = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM ops.pipeline_runs pr
            WHERE (CAST(:job_name AS TEXT) IS NULL OR pr.job_name = CAST(:job_name AS TEXT))
              AND (CAST(:source AS TEXT) IS NULL OR pr.source = CAST(:source AS TEXT))
              AND (CAST(:dataset AS TEXT) IS NULL OR pr.dataset = CAST(:dataset AS TEXT))
              AND (CAST(:wave AS TEXT) IS NULL OR pr.wave = CAST(:wave AS TEXT))
              AND (
                    CAST(:reference_period AS TEXT) IS NULL
                    OR pr.reference_period = CAST(:reference_period AS TEXT)
                  )
              AND (CAST(:run_status AS TEXT) IS NULL OR pr.status = CAST(:run_status AS TEXT))
              AND (CAST(:started_from AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc >= CAST(:started_from AS TIMESTAMPTZ))
              AND (CAST(:started_to AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc <= CAST(:started_to AS TIMESTAMPTZ))
            """
        ),
        params,
    ).scalar_one()

    runs_by_status_rows = db.execute(
        text(
            """
            SELECT pr.status, COUNT(*) AS count
            FROM ops.pipeline_runs pr
            WHERE (CAST(:job_name AS TEXT) IS NULL OR pr.job_name = CAST(:job_name AS TEXT))
              AND (CAST(:source AS TEXT) IS NULL OR pr.source = CAST(:source AS TEXT))
              AND (CAST(:dataset AS TEXT) IS NULL OR pr.dataset = CAST(:dataset AS TEXT))
              AND (CAST(:wave AS TEXT) IS NULL OR pr.wave = CAST(:wave AS TEXT))
              AND (
                    CAST(:reference_period AS TEXT) IS NULL
                    OR pr.reference_period = CAST(:reference_period AS TEXT)
                  )
              AND (CAST(:run_status AS TEXT) IS NULL OR pr.status = CAST(:run_status AS TEXT))
              AND (CAST(:started_from AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc >= CAST(:started_from AS TIMESTAMPTZ))
              AND (CAST(:started_to AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc <= CAST(:started_to AS TIMESTAMPTZ))
            GROUP BY pr.status
            ORDER BY pr.status
            """
        ),
        params,
    ).mappings().all()

    runs_by_wave_rows = db.execute(
        text(
            """
            SELECT COALESCE(pr.wave, 'unknown') AS wave, COUNT(*) AS count
            FROM ops.pipeline_runs pr
            WHERE (CAST(:job_name AS TEXT) IS NULL OR pr.job_name = CAST(:job_name AS TEXT))
              AND (CAST(:source AS TEXT) IS NULL OR pr.source = CAST(:source AS TEXT))
              AND (CAST(:dataset AS TEXT) IS NULL OR pr.dataset = CAST(:dataset AS TEXT))
              AND (CAST(:wave AS TEXT) IS NULL OR pr.wave = CAST(:wave AS TEXT))
              AND (
                    CAST(:reference_period AS TEXT) IS NULL
                    OR pr.reference_period = CAST(:reference_period AS TEXT)
                  )
              AND (CAST(:run_status AS TEXT) IS NULL OR pr.status = CAST(:run_status AS TEXT))
              AND (CAST(:started_from AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc >= CAST(:started_from AS TIMESTAMPTZ))
              AND (CAST(:started_to AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc <= CAST(:started_to AS TIMESTAMPTZ))
            GROUP BY COALESCE(pr.wave, 'unknown')
            ORDER BY wave
            """
        ),
        params,
    ).mappings().all()

    runs_latest_started_at_utc = db.execute(
        text(
            """
            SELECT MAX(pr.started_at_utc)
            FROM ops.pipeline_runs pr
            WHERE (CAST(:job_name AS TEXT) IS NULL OR pr.job_name = CAST(:job_name AS TEXT))
              AND (CAST(:source AS TEXT) IS NULL OR pr.source = CAST(:source AS TEXT))
              AND (CAST(:dataset AS TEXT) IS NULL OR pr.dataset = CAST(:dataset AS TEXT))
              AND (CAST(:wave AS TEXT) IS NULL OR pr.wave = CAST(:wave AS TEXT))
              AND (
                    CAST(:reference_period AS TEXT) IS NULL
                    OR pr.reference_period = CAST(:reference_period AS TEXT)
                  )
              AND (CAST(:run_status AS TEXT) IS NULL OR pr.status = CAST(:run_status AS TEXT))
              AND (CAST(:started_from AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc >= CAST(:started_from AS TIMESTAMPTZ))
              AND (CAST(:started_to AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc <= CAST(:started_to AS TIMESTAMPTZ))
            """
        ),
        params,
    ).scalar_one()

    checks_total = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM ops.pipeline_checks pc
            JOIN ops.pipeline_runs pr ON pr.run_id = pc.run_id
            WHERE (CAST(:job_name AS TEXT) IS NULL OR pr.job_name = CAST(:job_name AS TEXT))
              AND (CAST(:source AS TEXT) IS NULL OR pr.source = CAST(:source AS TEXT))
              AND (CAST(:dataset AS TEXT) IS NULL OR pr.dataset = CAST(:dataset AS TEXT))
              AND (CAST(:wave AS TEXT) IS NULL OR pr.wave = CAST(:wave AS TEXT))
              AND (
                    CAST(:reference_period AS TEXT) IS NULL
                    OR pr.reference_period = CAST(:reference_period AS TEXT)
                  )
              AND (CAST(:run_status AS TEXT) IS NULL OR pr.status = CAST(:run_status AS TEXT))
              AND (CAST(:check_status AS TEXT) IS NULL OR pc.status = CAST(:check_status AS TEXT))
              AND (CAST(:started_from AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc >= CAST(:started_from AS TIMESTAMPTZ))
              AND (CAST(:started_to AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc <= CAST(:started_to AS TIMESTAMPTZ))
              AND (CAST(:created_from AS TIMESTAMPTZ) IS NULL OR pc.created_at_utc >= CAST(:created_from AS TIMESTAMPTZ))
              AND (CAST(:created_to AS TIMESTAMPTZ) IS NULL OR pc.created_at_utc <= CAST(:created_to AS TIMESTAMPTZ))
            """
        ),
        params,
    ).scalar_one()

    checks_by_status_rows = db.execute(
        text(
            """
            SELECT pc.status, COUNT(*) AS count
            FROM ops.pipeline_checks pc
            JOIN ops.pipeline_runs pr ON pr.run_id = pc.run_id
            WHERE (CAST(:job_name AS TEXT) IS NULL OR pr.job_name = CAST(:job_name AS TEXT))
              AND (CAST(:source AS TEXT) IS NULL OR pr.source = CAST(:source AS TEXT))
              AND (CAST(:dataset AS TEXT) IS NULL OR pr.dataset = CAST(:dataset AS TEXT))
              AND (CAST(:wave AS TEXT) IS NULL OR pr.wave = CAST(:wave AS TEXT))
              AND (
                    CAST(:reference_period AS TEXT) IS NULL
                    OR pr.reference_period = CAST(:reference_period AS TEXT)
                  )
              AND (CAST(:run_status AS TEXT) IS NULL OR pr.status = CAST(:run_status AS TEXT))
              AND (CAST(:check_status AS TEXT) IS NULL OR pc.status = CAST(:check_status AS TEXT))
              AND (CAST(:started_from AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc >= CAST(:started_from AS TIMESTAMPTZ))
              AND (CAST(:started_to AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc <= CAST(:started_to AS TIMESTAMPTZ))
              AND (CAST(:created_from AS TIMESTAMPTZ) IS NULL OR pc.created_at_utc >= CAST(:created_from AS TIMESTAMPTZ))
              AND (CAST(:created_to AS TIMESTAMPTZ) IS NULL OR pc.created_at_utc <= CAST(:created_to AS TIMESTAMPTZ))
            GROUP BY pc.status
            ORDER BY pc.status
            """
        ),
        params,
    ).mappings().all()

    checks_latest_created_at_utc = db.execute(
        text(
            """
            SELECT MAX(pc.created_at_utc)
            FROM ops.pipeline_checks pc
            JOIN ops.pipeline_runs pr ON pr.run_id = pc.run_id
            WHERE (CAST(:job_name AS TEXT) IS NULL OR pr.job_name = CAST(:job_name AS TEXT))
              AND (CAST(:source AS TEXT) IS NULL OR pr.source = CAST(:source AS TEXT))
              AND (CAST(:dataset AS TEXT) IS NULL OR pr.dataset = CAST(:dataset AS TEXT))
              AND (CAST(:wave AS TEXT) IS NULL OR pr.wave = CAST(:wave AS TEXT))
              AND (
                    CAST(:reference_period AS TEXT) IS NULL
                    OR pr.reference_period = CAST(:reference_period AS TEXT)
                  )
              AND (CAST(:run_status AS TEXT) IS NULL OR pr.status = CAST(:run_status AS TEXT))
              AND (CAST(:check_status AS TEXT) IS NULL OR pc.status = CAST(:check_status AS TEXT))
              AND (CAST(:started_from AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc >= CAST(:started_from AS TIMESTAMPTZ))
              AND (CAST(:started_to AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc <= CAST(:started_to AS TIMESTAMPTZ))
              AND (CAST(:created_from AS TIMESTAMPTZ) IS NULL OR pc.created_at_utc >= CAST(:created_from AS TIMESTAMPTZ))
              AND (CAST(:created_to AS TIMESTAMPTZ) IS NULL OR pc.created_at_utc <= CAST(:created_to AS TIMESTAMPTZ))
            """
        ),
        params,
    ).scalar_one()

    connectors_total = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM ops.connector_registry cr
            WHERE (CAST(:source AS TEXT) IS NULL OR cr.source = CAST(:source AS TEXT))
              AND (CAST(:wave AS TEXT) IS NULL OR cr.wave = CAST(:wave AS TEXT))
              AND (
                    CAST(:connector_status AS TEXT) IS NULL
                    OR cr.status::text = CAST(:connector_status AS TEXT)
                  )
              AND (CAST(:updated_from AS TIMESTAMPTZ) IS NULL OR cr.updated_at_utc >= CAST(:updated_from AS TIMESTAMPTZ))
              AND (CAST(:updated_to AS TIMESTAMPTZ) IS NULL OR cr.updated_at_utc <= CAST(:updated_to AS TIMESTAMPTZ))
            """
        ),
        params,
    ).scalar_one()

    connectors_by_status_rows = db.execute(
        text(
            """
            SELECT cr.status::text AS status, COUNT(*) AS count
            FROM ops.connector_registry cr
            WHERE (CAST(:source AS TEXT) IS NULL OR cr.source = CAST(:source AS TEXT))
              AND (CAST(:wave AS TEXT) IS NULL OR cr.wave = CAST(:wave AS TEXT))
              AND (
                    CAST(:connector_status AS TEXT) IS NULL
                    OR cr.status::text = CAST(:connector_status AS TEXT)
                  )
              AND (CAST(:updated_from AS TIMESTAMPTZ) IS NULL OR cr.updated_at_utc >= CAST(:updated_from AS TIMESTAMPTZ))
              AND (CAST(:updated_to AS TIMESTAMPTZ) IS NULL OR cr.updated_at_utc <= CAST(:updated_to AS TIMESTAMPTZ))
            GROUP BY cr.status::text
            ORDER BY status
            """
        ),
        params,
    ).mappings().all()

    connectors_by_wave_rows = db.execute(
        text(
            """
            SELECT cr.wave, COUNT(*) AS count
            FROM ops.connector_registry cr
            WHERE (CAST(:source AS TEXT) IS NULL OR cr.source = CAST(:source AS TEXT))
              AND (CAST(:wave AS TEXT) IS NULL OR cr.wave = CAST(:wave AS TEXT))
              AND (
                    CAST(:connector_status AS TEXT) IS NULL
                    OR cr.status::text = CAST(:connector_status AS TEXT)
                  )
              AND (CAST(:updated_from AS TIMESTAMPTZ) IS NULL OR cr.updated_at_utc >= CAST(:updated_from AS TIMESTAMPTZ))
              AND (CAST(:updated_to AS TIMESTAMPTZ) IS NULL OR cr.updated_at_utc <= CAST(:updated_to AS TIMESTAMPTZ))
            GROUP BY cr.wave
            ORDER BY cr.wave
            """
        ),
        params,
    ).mappings().all()

    connectors_latest_updated_at_utc = db.execute(
        text(
            """
            SELECT MAX(cr.updated_at_utc)
            FROM ops.connector_registry cr
            WHERE (CAST(:source AS TEXT) IS NULL OR cr.source = CAST(:source AS TEXT))
              AND (CAST(:wave AS TEXT) IS NULL OR cr.wave = CAST(:wave AS TEXT))
              AND (
                    CAST(:connector_status AS TEXT) IS NULL
                    OR cr.status::text = CAST(:connector_status AS TEXT)
                  )
              AND (CAST(:updated_from AS TIMESTAMPTZ) IS NULL OR cr.updated_at_utc >= CAST(:updated_from AS TIMESTAMPTZ))
              AND (CAST(:updated_to AS TIMESTAMPTZ) IS NULL OR cr.updated_at_utc <= CAST(:updated_to AS TIMESTAMPTZ))
            """
        ),
        params,
    ).scalar_one()

    return {
        "runs": {
            "total": runs_total,
            "by_status": {row["status"]: int(row["count"]) for row in runs_by_status_rows},
            "by_wave": {row["wave"]: int(row["count"]) for row in runs_by_wave_rows},
            "latest_started_at_utc": runs_latest_started_at_utc,
        },
        "checks": {
            "total": checks_total,
            "by_status": {row["status"]: int(row["count"]) for row in checks_by_status_rows},
            "latest_created_at_utc": checks_latest_created_at_utc,
        },
        "connectors": {
            "total": connectors_total,
            "by_status": {
                row["status"]: int(row["count"])
                for row in connectors_by_status_rows
            },
            "by_wave": {row["wave"]: int(row["count"]) for row in connectors_by_wave_rows},
            "latest_updated_at_utc": connectors_latest_updated_at_utc,
        },
    }


@router.get("/source-coverage")
def get_ops_source_coverage(
    source: str | None = Query(default=None),
    wave: str | None = Query(default=None),
    reference_period: str | None = Query(default=None),
    started_from: datetime | None = Query(default=None),  # noqa: B008
    started_to: datetime | None = Query(default=None),  # noqa: B008
    include_internal: bool = Query(default=False),
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    params = {
        "source": source,
        "wave": wave,
        "reference_period": reference_period,
        "started_from": started_from,
        "started_to": started_to,
        "include_internal": include_internal,
    }

    rows = db.execute(
        text(
            """
            WITH registry AS (
                SELECT
                    cr.source,
                    cr.wave,
                    COUNT(*) AS implemented_connectors
                FROM ops.connector_registry cr
                WHERE cr.status = 'implemented'
                  AND (CAST(:source AS TEXT) IS NULL OR cr.source = CAST(:source AS TEXT))
                  AND (CAST(:wave AS TEXT) IS NULL OR cr.wave = CAST(:wave AS TEXT))
                  AND (:include_internal OR cr.source <> 'INTERNAL')
                GROUP BY cr.source, cr.wave
            ),
            runs AS (
                SELECT
                    pr.source,
                    pr.wave,
                    COUNT(*) AS runs_total,
                    COUNT(*) FILTER (WHERE pr.status = 'success') AS runs_success,
                    COUNT(*) FILTER (WHERE pr.status = 'blocked') AS runs_blocked,
                    COUNT(*) FILTER (WHERE pr.status = 'failed') AS runs_failed,
                    COALESCE(SUM(pr.rows_loaded), 0) AS rows_loaded_total,
                    MAX(pr.started_at_utc) AS latest_run_started_at_utc,
                    MAX(pr.reference_period) FILTER (WHERE pr.reference_period IS NOT NULL) AS latest_reference_period
                FROM ops.pipeline_runs pr
                WHERE (CAST(:source AS TEXT) IS NULL OR pr.source = CAST(:source AS TEXT))
                  AND (CAST(:wave AS TEXT) IS NULL OR pr.wave = CAST(:wave AS TEXT))
                  AND (
                        CAST(:reference_period AS TEXT) IS NULL
                        OR pr.reference_period = CAST(:reference_period AS TEXT)
                      )
                  AND (CAST(:started_from AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc >= CAST(:started_from AS TIMESTAMPTZ))
                  AND (CAST(:started_to AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc <= CAST(:started_to AS TIMESTAMPTZ))
                  AND (:include_internal OR pr.source <> 'INTERNAL')
                GROUP BY pr.source, pr.wave
            ),
            fact AS (
                SELECT
                    fi.source,
                    COUNT(*) AS fact_indicator_rows,
                    COUNT(DISTINCT fi.indicator_code) AS fact_indicator_codes,
                    MAX(fi.updated_at) AS latest_indicator_updated_at
                FROM silver.fact_indicator fi
                WHERE (CAST(:source AS TEXT) IS NULL OR fi.source = CAST(:source AS TEXT))
                  AND (
                        CAST(:reference_period AS TEXT) IS NULL
                        OR fi.reference_period = CAST(:reference_period AS TEXT)
                      )
                  AND (:include_internal OR fi.source <> 'INTERNAL')
                GROUP BY fi.source
            )
            SELECT
                r.source,
                r.wave,
                r.implemented_connectors,
                COALESCE(ru.runs_total, 0) AS runs_total,
                COALESCE(ru.runs_success, 0) AS runs_success,
                COALESCE(ru.runs_blocked, 0) AS runs_blocked,
                COALESCE(ru.runs_failed, 0) AS runs_failed,
                COALESCE(ru.rows_loaded_total, 0) AS rows_loaded_total,
                ru.latest_run_started_at_utc,
                ru.latest_reference_period,
                COALESCE(f.fact_indicator_rows, 0) AS fact_indicator_rows,
                COALESCE(f.fact_indicator_codes, 0) AS fact_indicator_codes,
                f.latest_indicator_updated_at,
                CASE
                    WHEN COALESCE(f.fact_indicator_rows, 0) > 0
                         AND COALESCE(ru.runs_success, 0) > 0 THEN 'ready'
                    WHEN COALESCE(ru.runs_total, 0) = 0 THEN 'idle'
                    WHEN COALESCE(ru.runs_failed, 0) > 0
                         AND COALESCE(ru.runs_success, 0) = 0
                         AND COALESCE(ru.runs_blocked, 0) = 0 THEN 'failed'
                    WHEN COALESCE(ru.runs_blocked, 0) > 0
                         AND COALESCE(ru.runs_success, 0) = 0 THEN 'blocked'
                    WHEN COALESCE(f.fact_indicator_rows, 0) = 0
                         AND COALESCE(ru.runs_success, 0) > 0 THEN 'no_fact_rows'
                    ELSE 'partial'
                END AS coverage_status
            FROM registry r
            LEFT JOIN runs ru
              ON ru.source = r.source
             AND ru.wave = r.wave
            LEFT JOIN fact f
              ON f.source = r.source
            ORDER BY r.wave ASC, r.source ASC
            """
        ),
        params,
    ).mappings().all()

    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["implemented_connectors"] = int(item["implemented_connectors"])
        item["runs_total"] = int(item["runs_total"])
        item["runs_success"] = int(item["runs_success"])
        item["runs_blocked"] = int(item["runs_blocked"])
        item["runs_failed"] = int(item["runs_failed"])
        item["rows_loaded_total"] = int(item["rows_loaded_total"])
        item["fact_indicator_rows"] = int(item["fact_indicator_rows"])
        item["fact_indicator_codes"] = int(item["fact_indicator_codes"])
        items.append(item)

    return {
        "source": source,
        "wave": wave,
        "reference_period": reference_period,
        "include_internal": include_internal,
        "items": items,
    }


@router.get("/sla")
def get_ops_sla(
    job_name: str | None = Query(default=None),
    source: str | None = Query(default=None),
    dataset: str | None = Query(default=None),
    wave: str | None = Query(default=None),
    reference_period: str | None = Query(default=None),
    run_status: str | None = Query(default=None),
    started_from: datetime | None = Query(default=None),  # noqa: B008
    started_to: datetime | None = Query(default=None),  # noqa: B008
    include_blocked_as_success: bool = Query(default=False),
    min_total_runs: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    params = {
        "job_name": job_name,
        "source": source,
        "dataset": dataset,
        "wave": wave,
        "reference_period": reference_period,
        "run_status": run_status,
        "started_from": started_from,
        "started_to": started_to,
        "include_blocked_as_success": include_blocked_as_success,
        "min_total_runs": min_total_runs,
    }

    rows = db.execute(
        text(
            """
            SELECT
                pr.job_name,
                COALESCE(pr.source, 'unknown') AS source,
                COALESCE(pr.dataset, 'unknown') AS dataset,
                COALESCE(pr.wave, 'unknown') AS wave,
                COUNT(*) AS total_runs,
                COUNT(*) FILTER (
                    WHERE CASE
                        WHEN :include_blocked_as_success
                            THEN pr.status IN ('success', 'blocked')
                        ELSE pr.status = 'success'
                    END
                ) AS successful_runs,
                ROUND(
                    COALESCE(
                        (
                            COUNT(*) FILTER (
                                WHERE CASE
                                    WHEN :include_blocked_as_success
                                        THEN pr.status IN ('success', 'blocked')
                                    ELSE pr.status = 'success'
                                END
                            )
                        )::numeric / NULLIF(COUNT(*), 0),
                        0
                    ),
                    6
                ) AS success_rate,
                percentile_cont(0.95) WITHIN GROUP (ORDER BY pr.duration_seconds)
                    FILTER (WHERE pr.duration_seconds IS NOT NULL) AS p95_duration_seconds,
                AVG(pr.duration_seconds)
                    FILTER (WHERE pr.duration_seconds IS NOT NULL) AS avg_duration_seconds,
                MAX(pr.started_at_utc) AS latest_started_at_utc
            FROM ops.pipeline_runs pr
            WHERE (CAST(:job_name AS TEXT) IS NULL OR pr.job_name = CAST(:job_name AS TEXT))
              AND (CAST(:source AS TEXT) IS NULL OR pr.source = CAST(:source AS TEXT))
              AND (CAST(:dataset AS TEXT) IS NULL OR pr.dataset = CAST(:dataset AS TEXT))
              AND (CAST(:wave AS TEXT) IS NULL OR pr.wave = CAST(:wave AS TEXT))
              AND (
                    CAST(:reference_period AS TEXT) IS NULL
                    OR pr.reference_period = CAST(:reference_period AS TEXT)
                  )
              AND (CAST(:run_status AS TEXT) IS NULL OR pr.status = CAST(:run_status AS TEXT))
              AND (CAST(:started_from AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc >= CAST(:started_from AS TIMESTAMPTZ))
              AND (CAST(:started_to AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc <= CAST(:started_to AS TIMESTAMPTZ))
            GROUP BY
                pr.job_name,
                COALESCE(pr.source, 'unknown'),
                COALESCE(pr.dataset, 'unknown'),
                COALESCE(pr.wave, 'unknown')
            HAVING COUNT(*) >= :min_total_runs
            ORDER BY wave ASC, pr.job_name ASC
            """
        ),
        params,
    ).mappings().all()

    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["total_runs"] = int(item["total_runs"])
        item["successful_runs"] = int(item["successful_runs"])
        if item["success_rate"] is not None:
            item["success_rate"] = float(item["success_rate"])
        if item["p95_duration_seconds"] is not None:
            item["p95_duration_seconds"] = float(item["p95_duration_seconds"])
        if item["avg_duration_seconds"] is not None:
            item["avg_duration_seconds"] = float(item["avg_duration_seconds"])
        items.append(item)

    return {
        "include_blocked_as_success": include_blocked_as_success,
        "min_total_runs": min_total_runs,
        "items": items,
    }


@router.get("/timeseries")
def get_ops_timeseries(
    entity: str = Query(default="runs", pattern="^(runs|checks)$"),
    granularity: str = Query(default="day", pattern="^(day|hour)$"),
    job_name: str | None = Query(default=None),
    source: str | None = Query(default=None),
    dataset: str | None = Query(default=None),
    wave: str | None = Query(default=None),
    reference_period: str | None = Query(default=None),
    run_status: str | None = Query(default=None),
    check_status: str | None = Query(default=None),
    started_from: datetime | None = Query(default=None),  # noqa: B008
    started_to: datetime | None = Query(default=None),  # noqa: B008
    created_from: datetime | None = Query(default=None),  # noqa: B008
    created_to: datetime | None = Query(default=None),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    params = {
        "job_name": job_name,
        "source": source,
        "dataset": dataset,
        "wave": wave,
        "reference_period": reference_period,
        "run_status": run_status,
        "check_status": check_status,
        "started_from": started_from,
        "started_to": started_to,
        "created_from": created_from,
        "created_to": created_to,
    }

    bucket_expr_by_entity = {
        "runs": {
            "day": "date_trunc('day', pr.started_at_utc)",
            "hour": "date_trunc('hour', pr.started_at_utc)",
        },
        "checks": {
            "day": "date_trunc('day', pc.created_at_utc)",
            "hour": "date_trunc('hour', pc.created_at_utc)",
        },
    }
    bucket_expr = bucket_expr_by_entity[entity][granularity]

    if entity == "runs":
        rows = db.execute(
            text(
                f"""
                SELECT
                    {bucket_expr} AS bucket_start_utc,
                    pr.status,
                    COUNT(*) AS count
                FROM ops.pipeline_runs pr
                WHERE (CAST(:job_name AS TEXT) IS NULL OR pr.job_name = CAST(:job_name AS TEXT))
                  AND (CAST(:source AS TEXT) IS NULL OR pr.source = CAST(:source AS TEXT))
                  AND (CAST(:dataset AS TEXT) IS NULL OR pr.dataset = CAST(:dataset AS TEXT))
                  AND (CAST(:wave AS TEXT) IS NULL OR pr.wave = CAST(:wave AS TEXT))
                  AND (
                        CAST(:reference_period AS TEXT) IS NULL
                        OR pr.reference_period = CAST(:reference_period AS TEXT)
                      )
                  AND (CAST(:run_status AS TEXT) IS NULL OR pr.status = CAST(:run_status AS TEXT))
                  AND (CAST(:started_from AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc >= CAST(:started_from AS TIMESTAMPTZ))
                  AND (CAST(:started_to AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc <= CAST(:started_to AS TIMESTAMPTZ))
                GROUP BY bucket_start_utc, pr.status
                ORDER BY bucket_start_utc ASC, pr.status ASC
                """
            ),
            params,
        ).mappings().all()
    else:
        rows = db.execute(
            text(
                f"""
                SELECT
                    {bucket_expr} AS bucket_start_utc,
                    pc.status,
                    COUNT(*) AS count
                FROM ops.pipeline_checks pc
                JOIN ops.pipeline_runs pr ON pr.run_id = pc.run_id
                WHERE (CAST(:job_name AS TEXT) IS NULL OR pr.job_name = CAST(:job_name AS TEXT))
                  AND (CAST(:source AS TEXT) IS NULL OR pr.source = CAST(:source AS TEXT))
                  AND (CAST(:dataset AS TEXT) IS NULL OR pr.dataset = CAST(:dataset AS TEXT))
                  AND (CAST(:wave AS TEXT) IS NULL OR pr.wave = CAST(:wave AS TEXT))
                  AND (
                        CAST(:reference_period AS TEXT) IS NULL
                        OR pr.reference_period = CAST(:reference_period AS TEXT)
                      )
                  AND (CAST(:run_status AS TEXT) IS NULL OR pr.status = CAST(:run_status AS TEXT))
                  AND (
                        CAST(:check_status AS TEXT) IS NULL
                        OR pc.status = CAST(:check_status AS TEXT)
                      )
                  AND (CAST(:started_from AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc >= CAST(:started_from AS TIMESTAMPTZ))
                  AND (CAST(:started_to AS TIMESTAMPTZ) IS NULL OR pr.started_at_utc <= CAST(:started_to AS TIMESTAMPTZ))
                  AND (CAST(:created_from AS TIMESTAMPTZ) IS NULL OR pc.created_at_utc >= CAST(:created_from AS TIMESTAMPTZ))
                  AND (CAST(:created_to AS TIMESTAMPTZ) IS NULL OR pc.created_at_utc <= CAST(:created_to AS TIMESTAMPTZ))
                GROUP BY bucket_start_utc, pc.status
                ORDER BY bucket_start_utc ASC, pc.status ASC
                """
            ),
            params,
        ).mappings().all()

    return {
        "entity": entity,
        "granularity": granularity,
        "items": _aggregate_timeseries_rows([dict(row) for row in rows]),
    }

