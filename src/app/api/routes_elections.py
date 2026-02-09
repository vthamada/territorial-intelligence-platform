from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.territory_levels import normalize_level
from app.api.utils import normalize_pagination
from app.schemas.responses import PaginatedResponse

router = APIRouter(prefix="/elections", tags=["elections"])


@router.get("/results", response_model=PaginatedResponse)
def get_election_results(
    level: str = Query(default="municipio"),
    year: int | None = Query(default=None),
    office: str | None = Query(default=None),
    round: int | None = Query(default=None),
    page: int = Query(default=1),
    page_size: int = Query(default=100),
    db: Session = Depends(get_db),
) -> PaginatedResponse:
    level_en = normalize_level(level)
    page, page_size, offset = normalize_pagination(page, page_size)
    params = {
        "level": level_en,
        "year": year,
        "office": office,
        "round": round,
        "limit": page_size,
        "offset": offset,
    }

    total = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM silver.fact_election_result fr
            JOIN silver.dim_territory dt ON dt.territory_id = fr.territory_id
            WHERE dt.level::text = :level
              AND (CAST(:year AS INTEGER) IS NULL OR fr.election_year = CAST(:year AS INTEGER))
              AND (CAST(:office AS TEXT) IS NULL OR fr.office = CAST(:office AS TEXT))
              AND (CAST(:round AS INTEGER) IS NULL OR fr.election_round = CAST(:round AS INTEGER))
            """
        ),
        params,
    ).scalar_one()

    rows = db.execute(
        text(
            """
            SELECT
                fr.fact_id::text AS fact_id,
                fr.territory_id::text AS territory_id,
                fr.election_year,
                fr.election_round,
                fr.office,
                fr.metric,
                fr.value
            FROM silver.fact_election_result fr
            JOIN silver.dim_territory dt ON dt.territory_id = fr.territory_id
            WHERE dt.level::text = :level
              AND (CAST(:year AS INTEGER) IS NULL OR fr.election_year = CAST(:year AS INTEGER))
              AND (CAST(:office AS TEXT) IS NULL OR fr.office = CAST(:office AS TEXT))
              AND (CAST(:round AS INTEGER) IS NULL OR fr.election_round = CAST(:round AS INTEGER))
            ORDER BY fr.election_year DESC, fr.metric
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()

    return PaginatedResponse(page=page, page_size=page_size, total=total, items=[dict(row) for row in rows])
