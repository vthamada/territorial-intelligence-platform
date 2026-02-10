from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.utils import normalize_pagination
from app.schemas.responses import PaginatedResponse

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/pipeline-runs", response_model=PaginatedResponse)
def list_pipeline_runs(
    run_id: str | None = Query(default=None),
    job_name: str | None = Query(default=None),
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
    params = {
        "run_id": run_id,
        "job_name": job_name,
        "status": status,
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
              AND (:started_from IS NULL OR started_at_utc >= :started_from)
              AND (:started_to IS NULL OR started_at_utc <= :started_to)
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
              AND (:started_from IS NULL OR started_at_utc >= :started_from)
              AND (:started_to IS NULL OR started_at_utc <= :started_to)
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
              AND (:created_from IS NULL OR pc.created_at_utc >= :created_from)
              AND (:created_to IS NULL OR pc.created_at_utc <= :created_to)
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
              AND (:created_from IS NULL OR pc.created_at_utc >= :created_from)
              AND (:created_to IS NULL OR pc.created_at_utc <= :created_to)
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
              AND (:updated_from IS NULL OR updated_at_utc >= :updated_from)
              AND (:updated_to IS NULL OR updated_at_utc <= :updated_to)
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
              AND (:updated_from IS NULL OR updated_at_utc >= :updated_from)
              AND (:updated_to IS NULL OR updated_at_utc <= :updated_to)
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
