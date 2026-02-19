from __future__ import annotations

import hashlib
import json
import math
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.map import (
    MapLayerCoverageItem,
    MapLayerReadinessItem,
    MapLayerItem,
    MapLayerMetadataResponse,
    MapLayersReadinessResponse,
    MapLayersResponse,
    MapLayersCoverageResponse,
    MapStyleDomainItem,
    MapStyleLegendRangeItem,
    MapStyleMetadataResponse,
    MapStyleSeverityItem,
    UrbanGeocodeItem,
    UrbanGeocodeResponse,
    UrbanNearbyPoiItem,
    UrbanNearbyPoisResponse,
    UrbanPoiCollectionResponse,
    UrbanPoiFeatureItem,
    UrbanRoadCollectionResponse,
    UrbanRoadFeatureItem,
)

router = APIRouter(prefix="/map", tags=["map"])
_STATIC_METADATA_GENERATED_AT = datetime.now(tz=UTC)
_BASE_LAYER_ITEMS: list[MapLayerItem] = [
    MapLayerItem(
        id="territory_municipality",
        label="Municipios",
        territory_level="municipality",
        is_official=True,
        official_status="official",
        layer_kind="polygon",
        source="silver.dim_territory",
        default_visibility=True,
        zoom_min=0,
        zoom_max=8,
        notes="Camada administrativa oficial do municipio.",
    ),
    MapLayerItem(
        id="territory_district",
        label="Distritos",
        territory_level="district",
        is_official=True,
        official_status="official",
        layer_kind="polygon",
        source="silver.dim_territory",
        default_visibility=True,
        zoom_min=9,
        zoom_max=11,
        notes="Camada administrativa oficial por distrito.",
    ),
    MapLayerItem(
        id="territory_census_sector",
        label="Setores censitarios",
        territory_level="census_sector",
        is_official=False,
        official_status="proxy",
        layer_kind="polygon",
        source="silver.dim_territory",
        default_visibility=False,
        zoom_min=12,
        zoom_max=None,
        proxy_method="Malha setorial simplificada com recorte municipal.",
        notes="Cobertura depende da disponibilidade da malha setorial para o recorte.",
    ),
    MapLayerItem(
        id="territory_electoral_zone",
        label="Zonas eleitorais",
        territory_level="electoral_zone",
        is_official=False,
        official_status="proxy",
        layer_kind="polygon",
        source="silver.dim_territory",
        default_visibility=False,
        zoom_min=9,
        zoom_max=12,
        proxy_method="Agregacao eleitoral territorializada quando houver zona carregada no Silver.",
        notes="Disponibilidade depende de consolidacao territorial da base eleitoral.",
    ),
    MapLayerItem(
        id="territory_electoral_section",
        label="Secoes eleitorais",
        territory_level="electoral_section",
        is_official=False,
        official_status="proxy",
        layer_kind="point",
        source="silver.dim_territory",
        default_visibility=False,
        zoom_min=12,
        zoom_max=None,
        proxy_method="Representacao agregada por secao, com geometria de precisao limitada.",
        notes="Camada fina com supressao recomendada para baixo volume.",
    ),
    MapLayerItem(
        id="territory_polling_place",
        label="Locais de votacao",
        territory_level="electoral_section",
        is_official=False,
        official_status="proxy",
        layer_kind="point",
        source="silver.dim_territory",
        default_visibility=False,
        zoom_min=12,
        zoom_max=None,
        proxy_method="Pontos derivados da secao eleitoral com nome de local detectado no payload oficial.",
        notes="Camada de apoio para base eleitoral; geocodificacao fina de endereco segue como evolucao futura.",
    ),
]
_URBAN_LAYER_ITEMS: list[MapLayerItem] = [
    MapLayerItem(
        id="urban_roads",
        label="Viario urbano",
        territory_level="urban",
        is_official=False,
        official_status="hybrid",
        layer_kind="line",
        source="map.urban_road_segment",
        default_visibility=False,
        zoom_min=12,
        zoom_max=None,
        notes="Rede viaria urbana para navegacao operacional e contexto de mobilidade.",
    ),
    MapLayerItem(
        id="urban_pois",
        label="Pontos de interesse urbanos",
        territory_level="urban",
        is_official=False,
        official_status="hybrid",
        layer_kind="point",
        source="map.urban_poi",
        default_visibility=False,
        zoom_min=12,
        zoom_max=None,
        notes="POIs operacionais para leitura territorial de servicos e equipamentos.",
    ),
]
_ALL_LAYER_ITEMS: list[MapLayerItem] = [*_BASE_LAYER_ITEMS, *_URBAN_LAYER_ITEMS]
_LAYER_INDEX: dict[str, MapLayerItem] = {item.id: item for item in _ALL_LAYER_ITEMS}

_LAYER_EXTRA_WHERE: dict[str, str] = {
    "territory_polling_place": "AND dt.metadata ? 'polling_place_name'",
}

_LAYER_NAME_EXPR: dict[str, str] = {
    "territory_polling_place": "COALESCE(NULLIF(dt.metadata->>'polling_place_name', ''), dt.name)",
}


def _parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    if not bbox:
        return None
    raw = [token.strip() for token in bbox.split(",")]
    if len(raw) != 4:
        raise HTTPException(
            status_code=422,
            detail="Invalid bbox format. Expected: minx,miny,maxx,maxy",
        )
    try:
        minx, miny, maxx, maxy = (float(token) for token in raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid bbox numeric values.") from exc
    if minx >= maxx or miny >= maxy:
        raise HTTPException(
            status_code=422,
            detail="Invalid bbox range. Ensure minx<maxx and miny<maxy.",
        )
    return minx, miny, maxx, maxy


def _parse_geojson(raw: str | None) -> dict:
    if not raw:
        return {"type": "GeometryCollection", "geometries": []}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"type": "GeometryCollection", "geometries": []}
    return parsed if isinstance(parsed, dict) else {"type": "GeometryCollection", "geometries": []}


@router.get("/layers", response_model=MapLayersResponse)
def get_map_layers(
    include_urban: bool = Query(default=False, description="Inclui camadas urbanas no catalogo."),
) -> MapLayersResponse:
    items = _ALL_LAYER_ITEMS if include_urban else _BASE_LAYER_ITEMS
    return MapLayersResponse(
        generated_at_utc=_STATIC_METADATA_GENERATED_AT,
        default_layer_id="territory_municipality",
        fallback_endpoint="/v1/geo/choropleth",
        items=items,
    )


@router.get("/layers/coverage", response_model=MapLayersCoverageResponse)
def get_map_layers_coverage(
    metric: str | None = Query(default=None),
    period: str | None = Query(default=None),
    include_urban: bool = Query(default=False, description="Inclui cobertura das camadas urbanas."),
    db: Session = Depends(get_db),
) -> MapLayersCoverageResponse:
    items: list[MapLayerCoverageItem] = []
    filters_applied = metric is not None or period is not None
    catalog = _ALL_LAYER_ITEMS if include_urban else _BASE_LAYER_ITEMS
    for layer in catalog:
        if layer.id == "urban_roads":
            try:
                coverage_row = db.execute(
                    text(
                        """
                        SELECT
                            COUNT(*)::int AS territories_total,
                            COUNT(*) FILTER (WHERE geom IS NOT NULL)::int AS territories_with_geometry
                        FROM map.urban_road_segment
                        """
                    )
                ).mappings().first()
            except SQLAlchemyError:
                coverage_row = None
            territories_total = int(coverage_row["territories_total"]) if coverage_row else 0
            territories_with_geometry = int(coverage_row["territories_with_geometry"]) if coverage_row else 0
            territories_with_indicator = territories_with_geometry
            is_ready = territories_with_geometry > 0
            notes: str | None = None
            if territories_total == 0:
                notes = "Sem segmentos viarios urbanos carregados."
            elif territories_with_geometry == 0:
                notes = "Segmentos viarios sem geometria valida."
            items.append(
                MapLayerCoverageItem(
                    layer_id=layer.id,
                    territory_level=layer.territory_level,
                    territories_total=territories_total,
                    territories_with_geometry=territories_with_geometry,
                    territories_with_indicator=territories_with_indicator,
                    is_ready=is_ready,
                    notes=notes,
                )
            )
            continue

        if layer.id == "urban_pois":
            try:
                coverage_row = db.execute(
                    text(
                        """
                        SELECT
                            COUNT(*)::int AS territories_total,
                            COUNT(*) FILTER (WHERE geom IS NOT NULL)::int AS territories_with_geometry
                        FROM map.urban_poi
                        """
                    )
                ).mappings().first()
            except SQLAlchemyError:
                coverage_row = None
            territories_total = int(coverage_row["territories_total"]) if coverage_row else 0
            territories_with_geometry = int(coverage_row["territories_with_geometry"]) if coverage_row else 0
            territories_with_indicator = territories_with_geometry
            is_ready = territories_with_geometry > 0
            notes = None
            if territories_total == 0:
                notes = "Sem POIs urbanos carregados."
            elif territories_with_geometry == 0:
                notes = "POIs urbanos sem geometria valida."
            items.append(
                MapLayerCoverageItem(
                    layer_id=layer.id,
                    territory_level=layer.territory_level,
                    territories_total=territories_total,
                    territories_with_geometry=territories_with_geometry,
                    territories_with_indicator=territories_with_indicator,
                    is_ready=is_ready,
                    notes=notes,
                )
            )
            continue

        layer_filter = _LAYER_EXTRA_WHERE.get(layer.id, "")
        level = layer.territory_level
        coverage_row = db.execute(
            text(
                f"""
                SELECT
                    COUNT(*)::int AS territories_total,
                    COUNT(*) FILTER (WHERE dt.geometry IS NOT NULL)::int AS territories_with_geometry
                FROM silver.dim_territory dt
                WHERE dt.level::text = :level
                  {layer_filter}
                """
            ),
            {"level": level},
        ).mappings().first()
        territories_total = int(coverage_row["territories_total"]) if coverage_row else 0
        territories_with_geometry = (
            int(coverage_row["territories_with_geometry"]) if coverage_row else 0
        )

        indicator_row = db.execute(
            text(
                f"""
                SELECT
                    COUNT(DISTINCT dt.territory_id)::int AS territories_with_indicator
                FROM silver.dim_territory dt
                JOIN silver.fact_indicator fi ON fi.territory_id = dt.territory_id
                WHERE dt.level::text = :level
                  {layer_filter}
                  AND (CAST(:metric AS TEXT) IS NULL OR fi.indicator_code = CAST(:metric AS TEXT))
                  AND (CAST(:period AS TEXT) IS NULL OR fi.reference_period = CAST(:period AS TEXT))
                """
            ),
            {"level": level, "metric": metric, "period": period},
        ).mappings().first()
        territories_with_indicator = (
            int(indicator_row["territories_with_indicator"]) if indicator_row else 0
        )
        is_ready = territories_with_geometry > 0 and (
            not filters_applied or territories_with_indicator > 0
        )

        notes: str | None = None
        if territories_total == 0:
            notes = "Sem territorios carregados para esta camada."
        elif territories_with_geometry == 0:
            notes = "Territorios sem geometria valida para renderizacao."
        elif filters_applied and territories_with_indicator == 0:
            notes = "Sem indicadores para o recorte de metrica/periodo informado."

        items.append(
            MapLayerCoverageItem(
                layer_id=layer.id,
                territory_level=level,
                territories_total=territories_total,
                territories_with_geometry=territories_with_geometry,
                territories_with_indicator=territories_with_indicator,
                is_ready=is_ready,
                notes=notes,
            )
        )

    return MapLayersCoverageResponse(
        generated_at_utc=_STATIC_METADATA_GENERATED_AT,
        metric=metric,
        period=period,
        items=items,
    )


@router.get("/layers/readiness", response_model=MapLayersReadinessResponse)
def get_map_layers_readiness(
    metric: str | None = Query(default=None),
    period: str | None = Query(default=None),
    include_urban: bool = Query(default=False, description="Inclui readiness das camadas urbanas."),
    db: Session = Depends(get_db),
) -> MapLayersReadinessResponse:
    catalog = get_map_layers(include_urban=include_urban)
    coverage = get_map_layers_coverage(metric=metric, period=period, include_urban=include_urban, db=db)

    latest_quality_run = db.execute(
        text(
            """
            SELECT run_id::text AS run_id, started_at_utc
            FROM ops.pipeline_runs
            WHERE job_name = 'quality_suite'
            ORDER BY started_at_utc DESC, run_id DESC
            LIMIT 1
            """
        )
    ).mappings().first()

    checks_by_name: dict[str, dict] = {}
    quality_run_id: str | None = None
    quality_run_started_at_utc: datetime | None = None
    if latest_quality_run is not None:
        quality_run_id = str(latest_quality_run["run_id"])
        quality_run_started_at_utc = latest_quality_run["started_at_utc"]
        check_rows = db.execute(
            text(
                """
                SELECT check_name, status, details, observed_value, threshold_value
                FROM ops.pipeline_checks
                WHERE run_id = CAST(:run_id AS uuid)
                  AND (
                    check_name LIKE 'map_layer_rows_%'
                    OR check_name LIKE 'map_layer_geometry_ratio_%'
                    OR check_name LIKE 'urban\\_%\\_rows\\_after\\_filter' ESCAPE '\\'
                    OR check_name LIKE 'urban\\_%\\_invalid\\_geometry\\_rows' ESCAPE '\\'
                  )
                ORDER BY check_id DESC
                """
            ),
            {"run_id": quality_run_id},
        ).mappings().all()
        checks_by_name = {str(row["check_name"]): dict(row) for row in check_rows}

    catalog_by_id = {item.id: item for item in catalog.items}
    items: list[MapLayerReadinessItem] = []
    for coverage_item in coverage.items:
        layer = catalog_by_id[coverage_item.layer_id]

        if coverage_item.territory_level == "urban":
            row_check_name = f"{coverage_item.layer_id}_rows_after_filter"
            geometry_check_name = f"{coverage_item.layer_id}_invalid_geometry_rows"
        else:
            row_check_name = f"map_layer_rows_{coverage_item.territory_level}"
            geometry_check_name = f"map_layer_geometry_ratio_{coverage_item.territory_level}"

        row_check = checks_by_name.get(row_check_name)
        geometry_check = checks_by_name.get(geometry_check_name)

        row_status = str(row_check["status"]) if row_check else None
        geometry_status = str(geometry_check["status"]) if geometry_check else None
        statuses = [status for status in (row_status, geometry_status) if status]

        if "fail" in statuses:
            readiness_status = "fail"
            readiness_reason = "Check de qualidade com falha para a camada."
        elif "warn" in statuses:
            readiness_status = "warn"
            readiness_reason = "Camada com aviso de qualidade; revisar cobertura e geometria."
        elif coverage_item.is_ready:
            readiness_status = "pass"
            readiness_reason = None
        else:
            readiness_status = "pending"
            readiness_reason = coverage_item.notes or "Camada ainda sem cobertura operacional completa."

        items.append(
            MapLayerReadinessItem(
                layer=layer,
                coverage=coverage_item,
                readiness_status=readiness_status,
                readiness_reason=readiness_reason,
                row_check=row_check,
                geometry_check=geometry_check,
            )
        )

    return MapLayersReadinessResponse(
        generated_at_utc=datetime.now(tz=UTC),
        metric=metric,
        period=period,
        quality_run_id=quality_run_id,
        quality_run_started_at_utc=quality_run_started_at_utc,
        items=items,
    )


@router.get("/layers/{layer_id}/metadata", response_model=MapLayerMetadataResponse)
def get_map_layer_metadata(layer_id: str) -> MapLayerMetadataResponse:
    layer = _LAYER_INDEX.get(layer_id)
    if layer is None:
        raise HTTPException(status_code=404, detail={"reason": "Unknown layer", "layer": layer_id})

    methodology_by_layer = {
        "territory_municipality": "Recorte oficial municipal em silver.dim_territory com geometria PostGIS.",
        "territory_district": "Recorte oficial distrital consolidado a partir da malha territorial IBGE.",
        "territory_census_sector": "Setores censitarios carregados no Silver e simplificados para uso vetorial por zoom.",
        "territory_electoral_zone": "Agregacao por zona eleitoral dependente da consolidacao territorial em dim_territory.",
        "territory_electoral_section": "Representacao agregada por secao eleitoral com precisao geometrica limitada.",
        "territory_polling_place": "Local de votacao detectado no payload eleitoral e associado a geometria de secao.",
        "urban_roads": "Camada vetorial urbana de segmentos viarios consolidada em map.urban_road_segment.",
        "urban_pois": "Camada vetorial urbana de pontos de interesse consolidada em map.urban_poi.",
    }
    limitations_by_layer = {
        "territory_municipality": [
            "Dependente de atualizacao do recorte oficial no ciclo de ingestao.",
        ],
        "territory_district": [
            "Pode variar conforme disponibilidade da malha distrital por UF.",
        ],
        "territory_census_sector": [
            "Cobertura parcial em algumas janelas de dados.",
            "Recomenda-se supressao para volumes muito baixos.",
        ],
        "territory_electoral_zone": [
            "Camada depende de consolidacao da chave territorial eleitoral no Silver.",
            "Pode nao ter indicador associado no recorte atual.",
        ],
        "territory_electoral_section": [
            "Granularidade fina com risco de baixa cobertura de dados.",
            "Geometria pode ser proxy para representacao visual.",
        ],
        "territory_polling_place": [
            "Cobertura depende da presenca de nome de local de votacao na base eleitoral.",
            "Geometria segue proxy de secao; geocodificacao de endereco nao esta inclusa nesta fase.",
        ],
        "urban_roads": [
            "Dependente da atualizacao do conector urbano e da abrangencia do recorte espacial.",
        ],
        "urban_pois": [
            "Dependente da atualizacao do conector urbano e da qualidade semantica de categorias.",
        ],
    }
    return MapLayerMetadataResponse(
        generated_at_utc=_STATIC_METADATA_GENERATED_AT,
        layer=layer,
        methodology=methodology_by_layer.get(layer_id, "Metodologia nao registrada."),
        limitations=limitations_by_layer.get(layer_id, ["Sem limitacoes registradas."]),
    )


@router.get("/style-metadata", response_model=MapStyleMetadataResponse)
def get_map_style_metadata() -> MapStyleMetadataResponse:
    return MapStyleMetadataResponse(
        generated_at_utc=_STATIC_METADATA_GENERATED_AT,
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


@router.get("/urban/roads", response_model=UrbanRoadCollectionResponse)
def get_urban_roads(
    bbox: str | None = Query(default=None, description="minx,miny,maxx,maxy in EPSG:4326."),
    road_class: str | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> UrbanRoadCollectionResponse:
    parsed_bbox = _parse_bbox(bbox)
    minx = miny = maxx = maxy = None
    if parsed_bbox is not None:
        minx, miny, maxx, maxy = parsed_bbox

    sql = """
        SELECT
            road_id::text AS road_id,
            source,
            name,
            road_class,
            COALESCE(ST_Length(ST_Transform(geom, 31983)), 0)::double precision AS length_m,
            ST_AsGeoJSON(geom)::text AS geometry_json
        FROM map.urban_road_segment
        WHERE (
                CAST(:road_class AS TEXT) IS NULL
                OR lower(COALESCE(road_class, '')) = lower(CAST(:road_class AS TEXT))
            )
          AND (
                CAST(:minx AS double precision) IS NULL
                OR ST_Intersects(
                    geom,
                    ST_MakeEnvelope(
                        CAST(:minx AS double precision),
                        CAST(:miny AS double precision),
                        CAST(:maxx AS double precision),
                        CAST(:maxy AS double precision),
                        4326
                    )
                )
            )
        ORDER BY road_id
        LIMIT :limit
    """
    try:
        rows = db.execute(
            text(sql),
            {
                "road_class": road_class,
                "minx": minx,
                "miny": miny,
                "maxx": maxx,
                "maxy": maxy,
                "limit": limit,
            },
        ).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Urban road layer is unavailable. Ensure urban SQL objects are applied "
                "with scripts/init_db.py."
            ),
        ) from exc

    items = [
        UrbanRoadFeatureItem(
            road_id=str(row["road_id"]),
            source=str(row["source"]),
            name=row.get("name"),
            road_class=row.get("road_class"),
            length_m=float(row.get("length_m") or 0.0),
            geometry=_parse_geojson(row.get("geometry_json")),
        )
        for row in rows
    ]
    return UrbanRoadCollectionResponse(
        generated_at_utc=datetime.now(tz=UTC),
        count=len(items),
        items=items,
    )


@router.get("/urban/pois", response_model=UrbanPoiCollectionResponse)
def get_urban_pois(
    bbox: str | None = Query(default=None, description="minx,miny,maxx,maxy in EPSG:4326."),
    category: str | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> UrbanPoiCollectionResponse:
    parsed_bbox = _parse_bbox(bbox)
    minx = miny = maxx = maxy = None
    if parsed_bbox is not None:
        minx, miny, maxx, maxy = parsed_bbox

    sql = """
        SELECT
            poi_id::text AS poi_id,
            source,
            name,
            category,
            subcategory,
            ST_AsGeoJSON(geom)::text AS geometry_json
        FROM map.urban_poi
        WHERE (
                CAST(:category AS TEXT) IS NULL
                OR lower(COALESCE(category, '')) = lower(CAST(:category AS TEXT))
            )
          AND (
                CAST(:minx AS double precision) IS NULL
                OR ST_Intersects(
                    geom,
                    ST_MakeEnvelope(
                        CAST(:minx AS double precision),
                        CAST(:miny AS double precision),
                        CAST(:maxx AS double precision),
                        CAST(:maxy AS double precision),
                        4326
                    )
                )
            )
        ORDER BY poi_id
        LIMIT :limit
    """
    try:
        rows = db.execute(
            text(sql),
            {
                "category": category,
                "minx": minx,
                "miny": miny,
                "maxx": maxx,
                "maxy": maxy,
                "limit": limit,
            },
        ).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Urban POI layer is unavailable. Ensure urban SQL objects are applied "
                "with scripts/init_db.py."
            ),
        ) from exc

    items = [
        UrbanPoiFeatureItem(
            poi_id=str(row["poi_id"]),
            source=str(row["source"]),
            name=row.get("name"),
            category=row.get("category"),
            subcategory=row.get("subcategory"),
            geometry=_parse_geojson(row.get("geometry_json")),
        )
        for row in rows
    ]
    return UrbanPoiCollectionResponse(
        generated_at_utc=datetime.now(tz=UTC),
        count=len(items),
        items=items,
    )


@router.get("/urban/nearby-pois", response_model=UrbanNearbyPoisResponse)
def get_urban_nearby_pois(
    lon: float = Query(..., ge=-180.0, le=180.0),
    lat: float = Query(..., ge=-90.0, le=90.0),
    radius_m: float = Query(default=1000.0, gt=0.0, le=50000.0),
    category: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> UrbanNearbyPoisResponse:
    sql = """
        WITH center AS (
            SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) AS geom
        )
        SELECT
            p.poi_id::text AS poi_id,
            p.source,
            p.name,
            p.category,
            p.subcategory,
            ST_Distance(
                p.geom::geography,
                (SELECT geom FROM center)::geography
            )::double precision AS distance_m,
            ST_AsGeoJSON(p.geom)::text AS geometry_json
        FROM map.urban_poi p
        WHERE ST_DWithin(
                p.geom::geography,
                (SELECT geom FROM center)::geography,
                CAST(:radius_m AS double precision)
            )
          AND (
                CAST(:category AS TEXT) IS NULL
                OR lower(COALESCE(p.category, '')) = lower(CAST(:category AS TEXT))
            )
        ORDER BY distance_m ASC, p.poi_id ASC
        LIMIT :limit
    """
    try:
        rows = db.execute(
            text(sql),
            {
                "lon": lon,
                "lat": lat,
                "radius_m": radius_m,
                "category": category,
                "limit": limit,
            },
        ).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Urban nearby search is unavailable. Ensure urban SQL objects are applied "
                "with scripts/init_db.py."
            ),
        ) from exc

    items = [
        UrbanNearbyPoiItem(
            poi_id=str(row["poi_id"]),
            source=str(row["source"]),
            name=row.get("name"),
            category=row.get("category"),
            subcategory=row.get("subcategory"),
            distance_m=float(row.get("distance_m") or 0.0),
            geometry=_parse_geojson(row.get("geometry_json")),
        )
        for row in rows
    ]
    return UrbanNearbyPoisResponse(
        generated_at_utc=datetime.now(tz=UTC),
        center={"lon": lon, "lat": lat},
        radius_m=radius_m,
        count=len(items),
        items=items,
    )


@router.get("/urban/geocode", response_model=UrbanGeocodeResponse)
def geocode_urban(
    q: str = Query(..., min_length=2, max_length=120),
    kind: str = Query(default="all", pattern="^(all|road|poi)$"),
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> UrbanGeocodeResponse:
    query = q.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Query cannot be empty.")
    q_like = f"%{query}%"
    q_prefix = f"{query}%"

    sql = """
        WITH ranked AS (
            SELECT
                'road'::text AS feature_type,
                r.road_id::text AS feature_id,
                r.source,
                r.name,
                r.road_class::text AS category,
                NULL::text AS subcategory,
                CASE
                    WHEN lower(COALESCE(r.name, '')) = lower(CAST(:q AS TEXT)) THEN 3
                    WHEN lower(COALESCE(r.name, '')) LIKE lower(CAST(:q_prefix AS TEXT)) THEN 2
                    ELSE 1
                END AS score,
                ST_AsGeoJSON(ST_LineInterpolatePoint(r.geom, 0.5))::text AS geometry_json
            FROM map.urban_road_segment r
            WHERE lower(COALESCE(r.name, '')) LIKE lower(CAST(:q_like AS TEXT))

            UNION ALL

            SELECT
                'poi'::text AS feature_type,
                p.poi_id::text AS feature_id,
                p.source,
                p.name,
                p.category::text AS category,
                p.subcategory::text AS subcategory,
                CASE
                    WHEN lower(COALESCE(p.name, '')) = lower(CAST(:q AS TEXT)) THEN 3
                    WHEN lower(COALESCE(p.name, '')) LIKE lower(CAST(:q_prefix AS TEXT)) THEN 2
                    ELSE 1
                END AS score,
                ST_AsGeoJSON(p.geom)::text AS geometry_json
            FROM map.urban_poi p
            WHERE lower(COALESCE(p.name, '')) LIKE lower(CAST(:q_like AS TEXT))
        )
        SELECT
            feature_type,
            feature_id,
            source,
            name,
            category,
            subcategory,
            score,
            geometry_json
        FROM ranked
        WHERE (
                CAST(:kind AS TEXT) = 'all'
                OR feature_type = CAST(:kind AS TEXT)
            )
        ORDER BY score DESC, name ASC NULLS LAST
        LIMIT :limit
    """
    try:
        rows = db.execute(
            text(sql),
            {"q": query, "q_like": q_like, "q_prefix": q_prefix, "kind": kind, "limit": limit},
        ).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Urban geocoding is unavailable. Ensure urban SQL objects are applied "
                "with scripts/init_db.py."
            ),
        ) from exc

    items = [
        UrbanGeocodeItem(
            feature_type=str(row["feature_type"]),
            feature_id=str(row["feature_id"]),
            source=str(row["source"]),
            name=row.get("name"),
            category=row.get("category"),
            subcategory=row.get("subcategory"),
            score=int(row.get("score") or 0),
            geometry=_parse_geojson(row.get("geometry_json")),
        )
        for row in rows
    ]
    return UrbanGeocodeResponse(
        generated_at_utc=datetime.now(tz=UTC),
        query=query,
        count=len(items),
        items=items,
    )


_LAYER_TO_LEVEL: dict[str, str] = {
    layer.id: layer.territory_level for layer in _ALL_LAYER_ITEMS
}

_URBAN_TILE_LAYERS: dict[str, dict[str, str]] = {
    "urban_roads": {
        "table": "map.urban_road_segment",
        "alias": "r",
        "id_expr": "r.road_id::text",
        "name_expr": "COALESCE(NULLIF(r.name, ''), 'Via ' || r.road_id::text)",
        "value_expr": "COALESCE(r.length_m, ST_Length(ST_Transform(r.geom, 31983)))::double precision",
        "metric_expr": "'urban_roads'::text",
        "geom_expr": "r.geom",
    },
    "urban_pois": {
        "table": "map.urban_poi",
        "alias": "p",
        "id_expr": "p.poi_id::text",
        "name_expr": "COALESCE(NULLIF(p.name, ''), 'POI ' || p.poi_id::text)",
        "value_expr": "1::double precision",
        "metric_expr": "'urban_pois'::text",
        "geom_expr": "p.geom",
    },
}
# Simplification tolerance in meters on EPSG:3857.
_ZOOM_TOLERANCE_METERS: list[tuple[int, float]] = [
    (5, 20000.0),
    (9, 5000.0),
    (12, 1500.0),
    (15, 400.0),
    (99, 100.0),
]


def _tolerance_for_zoom(z: int) -> float:
    for max_zoom, tol in _ZOOM_TOLERANCE_METERS:
        if z < max_zoom:
            return tol
    return 100.0


_TILE_METRICS: list[dict[str, object]] = []
_TILE_METRICS_MAX = 500


def _tile_to_bbox(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    n = 2.0**z
    lon_min = x / n * 360.0 - 180.0
    lat_max = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    lon_max = (x + 1) / n * 360.0 - 180.0
    lat_min = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    return (lon_min, lat_min, lon_max, lat_max)


@router.get(
    "/tiles/{layer}/{z}/{x}/{y}.mvt",
    responses={
        200: {"content": {"application/vnd.mapbox-vector-tile": {}}},
        204: {"description": "Empty tile"},
        404: {"description": "Unknown layer"},
    },
)
def get_mvt_tile(
    layer: str,
    z: int,
    x: int,
    y: int,
    request: Request,
    metric: str | None = Query(default=None),
    period: str | None = Query(default=None),
    domain: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> Response:
    t0 = time.monotonic()

    level = _LAYER_TO_LEVEL.get(layer)
    urban_layer = _URBAN_TILE_LAYERS.get(layer)
    if level is None and urban_layer is None:
        raise HTTPException(status_code=404, detail={"reason": "Unknown layer", "layer": layer})

    tolerance_meters = _tolerance_for_zoom(z)
    use_indicator_join = metric is not None and period is not None
    layer_filter = _LAYER_EXTRA_WHERE.get(layer, "")
    name_expr = _LAYER_NAME_EXPR.get(layer, "dt.name")

    if urban_layer is not None:
        sql = text(
            f"""
            WITH tile_extent AS (
                SELECT ST_TileEnvelope(:z, :x, :y) AS envelope
            ),
            base AS (
                SELECT
                    {urban_layer["id_expr"]} AS tid,
                    {urban_layer["name_expr"]} AS tname,
                    {urban_layer["value_expr"]} AS val,
                    {urban_layer["metric_expr"]} AS metric,
                    ST_Transform({urban_layer["geom_expr"]}, 3857) AS geom_3857
                FROM {urban_layer["table"]} {urban_layer["alias"]}
                CROSS JOIN tile_extent te
                WHERE {urban_layer["geom_expr"]} IS NOT NULL
                  AND ST_Intersects(ST_Transform({urban_layer["geom_expr"]}, 3857), te.envelope)
            ),
            features AS (
                SELECT
                    base.tid,
                    base.tname,
                    base.val,
                    base.metric,
                    ST_AsMVTGeom(
                        ST_SimplifyPreserveTopology(base.geom_3857, :tolerance_meters),
                        te.envelope,
                        4096,
                        64,
                        true
                    ) AS geom
                FROM base
                CROSS JOIN tile_extent te
            )
            SELECT ST_AsMVT(features.*, :layer_name) AS mvt
            FROM features
            WHERE features.geom IS NOT NULL
            """
        )
    elif use_indicator_join:
        domain_filter = "AND fi.domain = :domain" if domain else ""
        sql = text(
            f"""
            WITH tile_extent AS (
                SELECT ST_TileEnvelope(:z, :x, :y) AS envelope
            ),
            base AS (
                SELECT
                    dt.territory_id::text AS tid,
                    {name_expr} AS tname,
                    fi.value::double precision AS val,
                    fi.indicator_code AS metric,
                    ST_Transform(dt.geometry, 3857) AS geom_3857
                FROM silver.dim_territory dt
                JOIN silver.fact_indicator fi ON fi.territory_id = dt.territory_id
                CROSS JOIN tile_extent te
                WHERE dt.level::text = :level
                  AND dt.geometry IS NOT NULL
                  {layer_filter}
                  AND ST_Intersects(ST_Transform(dt.geometry, 3857), te.envelope)
                  AND fi.indicator_code = :metric
                  AND fi.reference_period = :period
                  {domain_filter}
            ),
            features AS (
                SELECT
                    base.tid,
                    base.tname,
                    base.val,
                    base.metric,
                    ST_AsMVTGeom(
                        ST_SimplifyPreserveTopology(base.geom_3857, :tolerance_meters),
                        te.envelope,
                        4096,
                        64,
                        true
                    ) AS geom
                FROM base
                CROSS JOIN tile_extent te
            )
            SELECT ST_AsMVT(features.*, :layer_name) AS mvt
            FROM features
            WHERE features.geom IS NOT NULL
            """
        )
    else:
        sql = text(
            f"""
            WITH tile_extent AS (
                SELECT ST_TileEnvelope(:z, :x, :y) AS envelope
            ),
            base AS (
                SELECT
                    dt.territory_id::text AS tid,
                    {name_expr} AS tname,
                    ST_Transform(dt.geometry, 3857) AS geom_3857
                FROM silver.dim_territory dt
                CROSS JOIN tile_extent te
                WHERE dt.level::text = :level
                  AND dt.geometry IS NOT NULL
                  {layer_filter}
                  AND ST_Intersects(ST_Transform(dt.geometry, 3857), te.envelope)
            ),
            features AS (
                SELECT
                    base.tid,
                    base.tname,
                    ST_AsMVTGeom(
                        ST_SimplifyPreserveTopology(base.geom_3857, :tolerance_meters),
                        te.envelope,
                        4096,
                        64,
                        true
                    ) AS geom
                FROM base
                CROSS JOIN tile_extent te
            )
            SELECT ST_AsMVT(features.*, :layer_name) AS mvt
            FROM features
            WHERE features.geom IS NOT NULL
            """
        )

    params: dict[str, object] = {
        "z": z,
        "x": x,
        "y": y,
        "level": level,
        "tolerance_meters": tolerance_meters,
        "layer_name": layer,
    }
    if use_indicator_join and urban_layer is None:
        params["metric"] = metric
        params["period"] = period
        if domain:
            params["domain"] = domain

    try:
        execution = db.execute(sql, params)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Map tile backend is unavailable. Ensure map SQL objects are applied "
                "with scripts/init_db.py."
            ),
        ) from exc

    scalar_one_or_none = getattr(execution, "scalar_one_or_none", None)
    if callable(scalar_one_or_none):
        result = scalar_one_or_none()
    else:
        result = execution.scalar()
    mvt_bytes = bytes(result) if result else b""

    elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
    _TILE_METRICS.append(
        {
            "layer": layer,
            "z": z,
            "elapsed_ms": elapsed_ms,
            "bytes": len(mvt_bytes),
            "ts": time.time(),
        }
    )
    if len(_TILE_METRICS) > _TILE_METRICS_MAX:
        del _TILE_METRICS[: len(_TILE_METRICS) - _TILE_METRICS_MAX]

    if not mvt_bytes:
        return Response(status_code=204)

    etag = f"\"{hashlib.sha256(mvt_bytes).hexdigest()}\""
    if request.headers.get("if-none-match") == etag:
        return Response(
            status_code=304,
            headers={
                "Cache-Control": "public, max-age=900",
                "ETag": etag,
                "X-Map-Layer": layer,
                "Access-Control-Allow-Origin": "*",
            },
        )

    return Response(
        content=mvt_bytes,
        media_type="application/vnd.mapbox-vector-tile",
        headers={
            "Cache-Control": "public, max-age=900",
            "ETag": etag,
            "X-Map-Layer": layer,
            "Access-Control-Allow-Origin": "*",
            "X-Tile-Ms": str(elapsed_ms),
        },
    )


@router.get("/tiles/metrics")
def get_tile_metrics() -> dict:
    if not _TILE_METRICS:
        return {"count": 0, "by_layer": {}, "p50_ms": 0, "p95_ms": 0, "p99_ms": 0}

    latencies = sorted(m["elapsed_ms"] for m in _TILE_METRICS)  # type: ignore[type-var]
    n = len(latencies)

    by_layer: dict[str, dict[str, object]] = {}
    for m in _TILE_METRICS:
        lname = str(m["layer"])
        if lname not in by_layer:
            by_layer[lname] = {"count": 0, "total_ms": 0.0, "total_bytes": 0}
        by_layer[lname]["count"] = int(by_layer[lname]["count"]) + 1  # type: ignore[arg-type]
        by_layer[lname]["total_ms"] = float(by_layer[lname]["total_ms"]) + float(m["elapsed_ms"])  # type: ignore[arg-type]
        by_layer[lname]["total_bytes"] = int(by_layer[lname]["total_bytes"]) + int(m["bytes"])  # type: ignore[arg-type]

    for stats in by_layer.values():
        cnt = int(stats["count"])  # type: ignore[arg-type]
        stats["avg_ms"] = round(float(stats["total_ms"]) / cnt, 1) if cnt else 0  # type: ignore[arg-type]
        stats["avg_bytes"] = round(int(stats["total_bytes"]) / cnt) if cnt else 0  # type: ignore[arg-type]

    return {
        "count": n,
        "p50_ms": latencies[n // 2],
        "p95_ms": latencies[min(n - 1, int(n * 0.95))],
        "p99_ms": latencies[min(n - 1, int(n * 0.99))],
        "by_layer": by_layer,
    }
