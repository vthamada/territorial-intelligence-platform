from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.routes_map import (
    get_map_layer_metadata,
    get_map_layers,
    get_map_layers_coverage,
    get_map_layers_readiness,
)
from app.schemas.map import MapLayerMetadataResponse, MapLayersReadinessResponse, MapLayersCoverageResponse, MapLayersResponse

router = APIRouter(prefix="/territory/layers", tags=["territory-layers"])


@router.get("/catalog", response_model=MapLayersResponse)
def get_territory_layers_catalog() -> MapLayersResponse:
    return get_map_layers(include_urban=False)


@router.get("/coverage", response_model=MapLayersCoverageResponse)
def get_territory_layers_coverage(
    metric: str | None = Query(default=None),
    period: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> MapLayersCoverageResponse:
    return get_map_layers_coverage(metric=metric, period=period, include_urban=False, db=db)


@router.get("/{layer_id}/metadata", response_model=MapLayerMetadataResponse)
def get_territory_layer_metadata(layer_id: str) -> MapLayerMetadataResponse:
    return get_map_layer_metadata(layer_id=layer_id)


@router.get("/readiness", response_model=MapLayersReadinessResponse)
def get_territory_layers_readiness(
    metric: str | None = Query(default=None),
    period: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> MapLayersReadinessResponse:
    return get_map_layers_readiness(metric=metric, period=period, include_urban=False, db=db)
