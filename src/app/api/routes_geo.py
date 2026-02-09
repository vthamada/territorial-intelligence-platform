from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.territory_levels import normalize_level, to_external_level
from app.api.utils import normalize_pagination
from app.schemas.responses import PaginatedResponse

router = APIRouter(prefix="/geo", tags=["geo"])


@router.get("/choropleth", response_model=PaginatedResponse)
def get_choropleth(
    metric: str = Query(...),
    period: str = Query(...),
    level: str = Query(default="municipio"),
    page: int = Query(default=1),
    page_size: int = Query(default=100),
    db: Session = Depends(get_db),
) -> PaginatedResponse:
    level_en = normalize_level(level)
    if level_en not in {"municipality", "district"}:
        raise HTTPException(
            status_code=422,
            detail="Choropleth endpoint supports only municipality or district level.",
        )
    page, page_size, offset = normalize_pagination(page, page_size)
    params = {
        "metric": metric,
        "period": period,
        "level": level_en,
        "limit": page_size,
        "offset": offset,
    }

    total = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM silver.fact_indicator fi
            JOIN silver.dim_territory dt ON dt.territory_id = fi.territory_id
            WHERE fi.indicator_code = :metric
              AND fi.reference_period = :period
              AND dt.level::text = :level
            """
        ),
        params,
    ).scalar_one()

    rows = db.execute(
        text(
            """
            SELECT
                dt.territory_id::text AS territory_id,
                dt.name AS territory_name,
                dt.level::text AS level,
                fi.indicator_code AS metric,
                fi.reference_period,
                fi.value,
                ST_AsGeoJSON(dt.geometry)::jsonb AS geometry
            FROM silver.fact_indicator fi
            JOIN silver.dim_territory dt ON dt.territory_id = fi.territory_id
            WHERE fi.indicator_code = :metric
              AND fi.reference_period = :period
              AND dt.level::text = :level
            ORDER BY dt.name
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()

    items = []
    for row in rows:
        item = dict(row)
        item["level"] = to_external_level(item["level"])
        items.append(item)
    return PaginatedResponse(page=page, page_size=page_size, total=total, items=items)
