from __future__ import annotations

from datetime import datetime

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


class MapLayersResponse(BaseModel):
    generated_at_utc: datetime
    default_layer_id: str
    fallback_endpoint: str
    items: list[MapLayerItem]


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
