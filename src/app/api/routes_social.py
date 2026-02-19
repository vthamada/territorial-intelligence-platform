from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.utils import normalize_pagination
from app.schemas.responses import PaginatedResponse

router = APIRouter(prefix="/social", tags=["social"])


@router.get("/protection", response_model=PaginatedResponse)
def list_social_protection(
    territory_id: str | None = Query(default=None),
    period: str | None = Query(default=None),
    source: str | None = Query(default=None),
    dataset: str | None = Query(default=None),
    page: int = Query(default=1),
    page_size: int = Query(default=100),
    db: Session = Depends(get_db),
) -> PaginatedResponse:
    page, page_size, offset = normalize_pagination(page, page_size)
    params = {
        "territory_id": territory_id,
        "period": period,
        "source": source,
        "dataset": dataset,
        "limit": page_size,
        "offset": offset,
    }

    total = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM silver.fact_social_protection
            WHERE (CAST(:territory_id AS TEXT) IS NULL OR territory_id::text = CAST(:territory_id AS TEXT))
              AND (CAST(:period AS TEXT) IS NULL OR reference_period = CAST(:period AS TEXT))
              AND (CAST(:source AS TEXT) IS NULL OR source = CAST(:source AS TEXT))
              AND (CAST(:dataset AS TEXT) IS NULL OR dataset = CAST(:dataset AS TEXT))
            """
        ),
        params,
    ).scalar_one()

    rows = db.execute(
        text(
            """
            SELECT
                fact_id::text AS fact_id,
                territory_id::text AS territory_id,
                source,
                dataset,
                reference_period,
                households_total,
                people_total,
                avg_income_per_capita,
                poverty_rate,
                extreme_poverty_rate,
                metadata_json,
                updated_at
            FROM silver.fact_social_protection
            WHERE (CAST(:territory_id AS TEXT) IS NULL OR territory_id::text = CAST(:territory_id AS TEXT))
              AND (CAST(:period AS TEXT) IS NULL OR reference_period = CAST(:period AS TEXT))
              AND (CAST(:source AS TEXT) IS NULL OR source = CAST(:source AS TEXT))
              AND (CAST(:dataset AS TEXT) IS NULL OR dataset = CAST(:dataset AS TEXT))
            ORDER BY reference_period DESC, updated_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()

    return PaginatedResponse(page=page, page_size=page_size, total=total, items=[dict(row) for row in rows])


@router.get("/assistance-network", response_model=PaginatedResponse)
def list_social_assistance_network(
    territory_id: str | None = Query(default=None),
    period: str | None = Query(default=None),
    source: str | None = Query(default=None),
    dataset: str | None = Query(default=None),
    page: int = Query(default=1),
    page_size: int = Query(default=100),
    db: Session = Depends(get_db),
) -> PaginatedResponse:
    page, page_size, offset = normalize_pagination(page, page_size)
    params = {
        "territory_id": territory_id,
        "period": period,
        "source": source,
        "dataset": dataset,
        "limit": page_size,
        "offset": offset,
    }

    total = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM silver.fact_social_assistance_network
            WHERE (CAST(:territory_id AS TEXT) IS NULL OR territory_id::text = CAST(:territory_id AS TEXT))
              AND (CAST(:period AS TEXT) IS NULL OR reference_period = CAST(:period AS TEXT))
              AND (CAST(:source AS TEXT) IS NULL OR source = CAST(:source AS TEXT))
              AND (CAST(:dataset AS TEXT) IS NULL OR dataset = CAST(:dataset AS TEXT))
            """
        ),
        params,
    ).scalar_one()

    rows = db.execute(
        text(
            """
            SELECT
                fact_id::text AS fact_id,
                territory_id::text AS territory_id,
                source,
                dataset,
                reference_period,
                cras_units,
                creas_units,
                social_units_total,
                workers_total,
                service_capacity_total,
                metadata_json,
                updated_at
            FROM silver.fact_social_assistance_network
            WHERE (CAST(:territory_id AS TEXT) IS NULL OR territory_id::text = CAST(:territory_id AS TEXT))
              AND (CAST(:period AS TEXT) IS NULL OR reference_period = CAST(:period AS TEXT))
              AND (CAST(:source AS TEXT) IS NULL OR source = CAST(:source AS TEXT))
              AND (CAST(:dataset AS TEXT) IS NULL OR dataset = CAST(:dataset AS TEXT))
            ORDER BY reference_period DESC, updated_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()

    return PaginatedResponse(page=page, page_size=page_size, total=total, items=[dict(row) for row in rows])
