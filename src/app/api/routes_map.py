from __future__ import annotations

import hashlib
import math
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.map import (
    MapLayerCoverageItem,
    MapLayerItem,
    MapLayerMetadataResponse,
    MapLayersResponse,
    MapLayersCoverageResponse,
    MapStyleDomainItem,
    MapStyleLegendRangeItem,
    MapStyleMetadataResponse,
    MapStyleSeverityItem,
)

router = APIRouter(prefix="/map", tags=["map"])
_STATIC_METADATA_GENERATED_AT = datetime.now(tz=UTC)
_LAYER_ITEMS: list[MapLayerItem] = [
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
_LAYER_INDEX: dict[str, MapLayerItem] = {item.id: item for item in _LAYER_ITEMS}

_LAYER_EXTRA_WHERE: dict[str, str] = {
    "territory_polling_place": "AND dt.metadata ? 'polling_place_name'",
}

_LAYER_NAME_EXPR: dict[str, str] = {
    "territory_polling_place": "COALESCE(NULLIF(dt.metadata->>'polling_place_name', ''), dt.name)",
}


@router.get("/layers", response_model=MapLayersResponse)
def get_map_layers() -> MapLayersResponse:
    return MapLayersResponse(
        generated_at_utc=_STATIC_METADATA_GENERATED_AT,
        default_layer_id="territory_municipality",
        fallback_endpoint="/v1/geo/choropleth",
        items=_LAYER_ITEMS,
    )


@router.get("/layers/coverage", response_model=MapLayersCoverageResponse)
def get_map_layers_coverage(
    metric: str | None = Query(default=None),
    period: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> MapLayersCoverageResponse:
    items: list[MapLayerCoverageItem] = []
    filters_applied = metric is not None or period is not None
    for layer in _LAYER_ITEMS:
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


_LAYER_TO_LEVEL: dict[str, str] = {
    layer.id: layer.territory_level for layer in _LAYER_ITEMS
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
        422: {"description": "Unknown layer"},
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
    if level is None:
        raise HTTPException(status_code=422, detail={"reason": "Unknown layer", "layer": layer})

    tolerance_meters = _tolerance_for_zoom(z)
    use_indicator_join = metric is not None and period is not None
    layer_filter = _LAYER_EXTRA_WHERE.get(layer, "")
    name_expr = _LAYER_NAME_EXPR.get(layer, "dt.name")

    if use_indicator_join:
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
            """
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
    if use_indicator_join:
        params["metric"] = metric
        params["period"] = period
        if domain:
            params["domain"] = domain

    result = db.execute(sql, params).scalar()
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

    etag = f'W/"{hashlib.md5(mvt_bytes, usedforsecurity=False).hexdigest()[:16]}"'
    if request.headers.get("if-none-match") == etag:
        return Response(
            status_code=304,
            headers={
                "Cache-Control": "public, max-age=3600",
                "ETag": etag,
                "Access-Control-Allow-Origin": "*",
            },
        )

    return Response(
        content=mvt_bytes,
        media_type="application/vnd.mapbox-vector-tile",
        headers={
            "Cache-Control": "public, max-age=3600",
            "ETag": etag,
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
