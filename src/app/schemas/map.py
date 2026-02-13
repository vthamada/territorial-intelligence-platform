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
