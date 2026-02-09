from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.territory_levels import normalize_level, to_external_level
from app.api.utils import normalize_pagination
from app.schemas.responses import PaginatedResponse

router = APIRouter(prefix="/territories", tags=["territories"])


@router.get("", response_model=PaginatedResponse)
def list_territories(
    level: str | None = Query(default=None),
    include_geometry: bool = Query(default=False),
    page: int = Query(default=1),
    page_size: int = Query(default=100),
    db: Session = Depends(get_db),
) -> PaginatedResponse:
    level_en = normalize_level(level)
    page, page_size, offset = normalize_pagination(page, page_size)
    total = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM silver.dim_territory
            WHERE (CAST(:level AS TEXT) IS NULL OR level::text = CAST(:level AS TEXT))
            """
        ),
        {"level": level_en},
    ).scalar_one()

    geometry_select = "ST_AsGeoJSON(geometry)::jsonb AS geometry" if include_geometry else "NULL::jsonb AS geometry"
    rows = db.execute(
        text(
            f"""
            SELECT
                territory_id::text AS territory_id,
                level::text AS level,
                parent_territory_id::text AS parent_territory_id,
                canonical_key,
                source_system,
                source_entity_id,
                ibge_geocode,
                tse_zone,
                tse_section,
                name,
                normalized_name,
                uf,
                municipality_ibge_code,
                valid_from,
                valid_to,
                {geometry_select}
            FROM silver.dim_territory
            WHERE (CAST(:level AS TEXT) IS NULL OR level::text = CAST(:level AS TEXT))
            ORDER BY level, name
            LIMIT :limit OFFSET :offset
            """
        ),
        {"level": level_en, "limit": page_size, "offset": offset},
    ).mappings().all()

    items: list[dict] = []
    for row in rows:
        item = dict(row)
        item["level"] = to_external_level(item["level"])
        items.append(item)
    return PaginatedResponse(page=page, page_size=page_size, total=total, items=items)


@router.get("/{territory_id}")
def get_territory(
    territory_id: str,
    include_geometry: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> dict:
    geometry_select = "ST_AsGeoJSON(geometry)::jsonb AS geometry" if include_geometry else "NULL::jsonb AS geometry"
    row = db.execute(
        text(
            f"""
            SELECT
                territory_id::text AS territory_id,
                level::text AS level,
                parent_territory_id::text AS parent_territory_id,
                canonical_key,
                source_system,
                source_entity_id,
                ibge_geocode,
                tse_zone,
                tse_section,
                name,
                normalized_name,
                uf,
                municipality_ibge_code,
                valid_from,
                valid_to,
                {geometry_select}
            FROM silver.dim_territory
            WHERE territory_id::text = :territory_id
            """
        ),
        {"territory_id": territory_id},
    ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Territory not found")
    payload = dict(row)
    payload["level"] = to_external_level(payload["level"])
    return payload
