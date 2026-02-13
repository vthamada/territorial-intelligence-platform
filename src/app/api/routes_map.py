from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from app.schemas.map import MapLayerItem, MapLayersResponse

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/layers", response_model=MapLayersResponse)
def get_map_layers() -> MapLayersResponse:
    # MP-1 manifest for frontend layer orchestration; MVT delivery comes in MP-2.
    items = [
        MapLayerItem(
            id="territory_municipality",
            label="Municipios",
            territory_level="municipality",
            is_official=True,
            source="silver.dim_territory",
            default_visibility=True,
            zoom_min=0,
            zoom_max=8,
        ),
        MapLayerItem(
            id="territory_district",
            label="Distritos",
            territory_level="district",
            is_official=True,
            source="silver.dim_territory",
            default_visibility=True,
            zoom_min=9,
            zoom_max=11,
        ),
        MapLayerItem(
            id="territory_census_sector",
            label="Setores censitarios",
            territory_level="census_sector",
            is_official=False,
            source="silver.dim_territory",
            default_visibility=False,
            zoom_min=12,
            zoom_max=None,
        ),
    ]
    return MapLayersResponse(
        generated_at_utc=datetime.now(tz=UTC),
        default_layer_id="territory_municipality",
        fallback_endpoint="/v1/geo/choropleth",
        items=items,
    )
