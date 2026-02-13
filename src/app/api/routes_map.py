from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from app.schemas.map import (
    MapLayerItem,
    MapLayersResponse,
    MapStyleDomainItem,
    MapStyleLegendRangeItem,
    MapStyleMetadataResponse,
    MapStyleSeverityItem,
)

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


@router.get("/style-metadata", response_model=MapStyleMetadataResponse)
def get_map_style_metadata() -> MapStyleMetadataResponse:
    return MapStyleMetadataResponse(
        generated_at_utc=datetime.now(tz=UTC),
        version="v1",
        default_mode="choropleth",
        severity_palette=[
            MapStyleSeverityItem(severity="critical", label="Critico", color="#b91c1c"),
            MapStyleSeverityItem(severity="attention", label="Atencao", color="#d97706"),
            MapStyleSeverityItem(severity="stable", label="Estavel", color="#0f766e"),
            MapStyleSeverityItem(severity="info", label="Informativo", color="#1d4ed8"),
        ],
        domain_palette=[
            MapStyleDomainItem(domain="saude", label="Saude", color="#0f766e"),
            MapStyleDomainItem(domain="educacao", label="Educacao", color="#2563eb"),
            MapStyleDomainItem(domain="trabalho", label="Trabalho", color="#c2410c"),
            MapStyleDomainItem(domain="seguranca", label="Seguranca", color="#b91c1c"),
            MapStyleDomainItem(domain="meio_ambiente", label="Meio ambiente", color="#15803d"),
            MapStyleDomainItem(domain="energia", label="Energia", color="#7c3aed"),
        ],
        legend_ranges=[
            MapStyleLegendRangeItem(
                key="very_low",
                label="Muito baixo",
                min_value=0.0,
                max_value=20.0,
                color="#dbeafe",
            ),
            MapStyleLegendRangeItem(
                key="low",
                label="Baixo",
                min_value=20.0,
                max_value=40.0,
                color="#93c5fd",
            ),
            MapStyleLegendRangeItem(
                key="medium",
                label="Medio",
                min_value=40.0,
                max_value=70.0,
                color="#60a5fa",
            ),
            MapStyleLegendRangeItem(
                key="high",
                label="Alto",
                min_value=70.0,
                max_value=85.0,
                color="#3b82f6",
            ),
            MapStyleLegendRangeItem(
                key="very_high",
                label="Muito alto",
                min_value=85.0,
                max_value=100.0,
                color="#1d4ed8",
            ),
        ],
        notes="style_metadata_v1_static",
    )
