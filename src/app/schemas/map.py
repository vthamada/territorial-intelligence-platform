from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class MapLayerItem(BaseModel):
    id: str
    label: str
    territory_level: str
    is_official: bool
    source: str
    default_visibility: bool
    zoom_min: int
    zoom_max: int | None
    official_status: Literal["official", "proxy", "hybrid"] = "official"
    layer_kind: Literal["polygon", "point", "grid"] = "polygon"
    proxy_method: str | None = None
    notes: str | None = None


class MapLayersResponse(BaseModel):
    generated_at_utc: datetime
    default_layer_id: str
    fallback_endpoint: str
    items: list[MapLayerItem]


class MapLayerCoverageItem(BaseModel):
    layer_id: str
    territory_level: str
    territories_total: int
    territories_with_geometry: int
    territories_with_indicator: int
    is_ready: bool
    notes: str | None = None


class MapLayersCoverageResponse(BaseModel):
    generated_at_utc: datetime
    metric: str | None
    period: str | None
    items: list[MapLayerCoverageItem]


class MapLayerMetadataResponse(BaseModel):
    generated_at_utc: datetime
    layer: MapLayerItem
    methodology: str
    limitations: list[str]


class MapLayerCheckStatus(BaseModel):
    check_name: str
    status: str
    details: str
    observed_value: float | int | None = None
    threshold_value: float | int | None = None


class MapLayerReadinessItem(BaseModel):
    layer: MapLayerItem
    coverage: MapLayerCoverageItem
    readiness_status: str
    readiness_reason: str | None = None
    row_check: MapLayerCheckStatus | None = None
    geometry_check: MapLayerCheckStatus | None = None


class MapLayersReadinessResponse(BaseModel):
    generated_at_utc: datetime
    metric: str | None
    period: str | None
    quality_run_id: str | None = None
    quality_run_started_at_utc: datetime | None = None
    items: list[MapLayerReadinessItem]


class MapStyleSeverityItem(BaseModel):
    severity: str
    label: str
    color: str


class MapStyleDomainItem(BaseModel):
    domain: str
    label: str
    color: str


class MapStyleLegendRangeItem(BaseModel):
    key: str
    label: str
    min_value: float
    max_value: float
    color: str


class MapStyleMetadataResponse(BaseModel):
    generated_at_utc: datetime
    version: str
    default_mode: str
    severity_palette: list[MapStyleSeverityItem]
    domain_palette: list[MapStyleDomainItem]
    legend_ranges: list[MapStyleLegendRangeItem]
    notes: str


class UrbanRoadFeatureItem(BaseModel):
    road_id: str
    source: str
    name: str | None
    road_class: str | None
    length_m: float
    geometry: dict


class UrbanRoadCollectionResponse(BaseModel):
    generated_at_utc: datetime
    count: int
    items: list[UrbanRoadFeatureItem]


class UrbanPoiFeatureItem(BaseModel):
    poi_id: str
    source: str
    name: str | None
    category: str | None
    subcategory: str | None
    geometry: dict


class UrbanPoiCollectionResponse(BaseModel):
    generated_at_utc: datetime
    count: int
    items: list[UrbanPoiFeatureItem]


class UrbanNearbyPoiItem(BaseModel):
    poi_id: str
    source: str
    name: str | None
    category: str | None
    subcategory: str | None
    distance_m: float
    geometry: dict


class UrbanNearbyPoisResponse(BaseModel):
    generated_at_utc: datetime
    center: dict
    radius_m: float
    count: int
    items: list[UrbanNearbyPoiItem]


class UrbanGeocodeItem(BaseModel):
    feature_type: str
    feature_id: str
    source: str
    name: str | None
    category: str | None
    subcategory: str | None
    score: int
    geometry: dict


class UrbanGeocodeResponse(BaseModel):
    generated_at_utc: datetime
    query: str
    count: int
    items: list[UrbanGeocodeItem]
