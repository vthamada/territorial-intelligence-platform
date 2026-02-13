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
