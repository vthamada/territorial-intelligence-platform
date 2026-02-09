from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.territory_levels import normalize_level, to_external_level
from app.api.utils import normalize_pagination
from app.schemas.responses import PaginatedResponse

router = APIRouter(tags=["electorate"])

_BREAKDOWN_COLUMN = {
    "sex": "fe.sex",
    "age": "fe.age_range",
    "education": "fe.education",
}


@router.get("/electorate", response_model=PaginatedResponse)
def get_electorate(
    level: str = Query(default="municipio"),
    period: int | None = Query(default=None),
    breakdown: str | None = Query(default=None, pattern="^(sex|age|education)$"),
    page: int = Query(default=1),
    page_size: int = Query(default=100),
    db: Session = Depends(get_db),
) -> PaginatedResponse:
    level_en = normalize_level(level)
    page, page_size, offset = normalize_pagination(page, page_size)

    breakdown_col = _BREAKDOWN_COLUMN.get(breakdown or "", "NULL::text")
    breakdown_alias = breakdown or "none"
    count_sql = text(
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT 1
            FROM silver.fact_electorate fe
            JOIN silver.dim_territory dt ON dt.territory_id = fe.territory_id
            WHERE dt.level::text = :level
              AND (CAST(:period AS INTEGER) IS NULL OR fe.reference_year = CAST(:period AS INTEGER))
            GROUP BY fe.reference_year, dt.level, {breakdown_col}
        ) grouped_rows
        """
    )
    total = db.execute(count_sql, {"level": level_en, "period": period}).scalar_one()

    rows = db.execute(
        text(
            f"""
            SELECT
                fe.reference_year,
                dt.level::text AS level,
                {breakdown_col} AS breakdown_value,
                SUM(fe.voters) AS voters
            FROM silver.fact_electorate fe
            JOIN silver.dim_territory dt ON dt.territory_id = fe.territory_id
            WHERE dt.level::text = :level
              AND (CAST(:period AS INTEGER) IS NULL OR fe.reference_year = CAST(:period AS INTEGER))
            GROUP BY fe.reference_year, dt.level, {breakdown_col}
            ORDER BY fe.reference_year DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"level": level_en, "period": period, "limit": page_size, "offset": offset},
    ).mappings().all()

    items = []
    for row in rows:
        item = dict(row)
        item["level"] = to_external_level(item["level"])
        item["breakdown"] = breakdown_alias
        items.append(item)

    return PaginatedResponse(page=page, page_size=page_size, total=total, items=items)
