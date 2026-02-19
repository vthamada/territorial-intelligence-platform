from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.map import (
    MapLayerItem,
    MapLayersResponse,
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

_LAYER_CONFIG: dict[str, dict[str, object]] = {
    "territory_municipality": {
        "label": "Municipios",
        "territory_level": "municipality",
        "is_official": True,
        "source": "silver.dim_territory",
        "default_visibility": True,
        "zoom_min": 0,
        "zoom_max": 8,
        "relation": "map.mv_territory_municipality",
        "simplify_until_zoom": 8,
    },
    "territory_district": {
        "label": "Distritos",
        "territory_level": "district",
        "is_official": True,
        "source": "silver.dim_territory",
        "default_visibility": True,
        "zoom_min": 9,
        "zoom_max": 11,
        "relation": "map.mv_territory_district",
        "simplify_until_zoom": 11,
    },
    "territory_census_sector": {
        "label": "Setores censitarios",
        "territory_level": "census_sector",
        "is_official": False,
        "source": "silver.dim_territory",
        "default_visibility": False,
        "zoom_min": 12,
        "zoom_max": None,
        "relation": "map.mv_territory_census_sector",
        "simplify_until_zoom": 12,
    },
}


def _parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    if bbox is None:
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
def get_map_layers() -> MapLayersResponse:
    items = [
        MapLayerItem(
            id=layer_id,
            label=str(item["label"]),
            territory_level=str(item["territory_level"]),
            is_official=bool(item["is_official"]),
            source=str(item["source"]),
            default_visibility=bool(item["default_visibility"]),
            zoom_min=int(item["zoom_min"]),
            zoom_max=int(item["zoom_max"]) if item["zoom_max"] is not None else None,
        )
        for layer_id, item in _LAYER_CONFIG.items()
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
        WHERE CAST(:kind AS TEXT) = 'all' OR feature_type = CAST(:kind AS TEXT)
        ORDER BY score DESC, name ASC NULLS LAST, feature_type ASC, feature_id ASC
        LIMIT :limit
    """
    try:
        rows = db.execute(
            text(sql),
            {
                "q": query,
                "q_like": q_like,
                "q_prefix": q_prefix,
                "kind": kind,
                "limit": limit,
            },
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


@router.get("/tiles/{layer}/{z}/{x}/{y}.mvt")
def get_map_tiles(
    request: Request,
    layer: str = Path(..., description="Layer id from /v1/map/layers."),
    z: int = Path(..., ge=0, le=22),
    x: int = Path(..., ge=0),
    y: int = Path(..., ge=0),
    metric: str | None = Query(default=None),
    period: str | None = Query(default=None),
    domain: str | None = Query(default=None),
    only_critical: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> Response:
    config = _LAYER_CONFIG.get(layer)
    if config is None:
        raise HTTPException(status_code=404, detail=f"Unknown layer: {layer}")

    relation = str(config["relation"])
    simplify_until_zoom = int(config["simplify_until_zoom"])
    if z <= simplify_until_zoom:
        geom_expr_3857 = "ST_Transform(mv.geom_simplified, 3857)"
    else:
        geom_expr_3857 = "ST_Transform(mv.geom, 3857)"

    tile_sql = f"""
        WITH bounds AS (
            SELECT ST_TileEnvelope(:z, :x, :y) AS geom
        ),
        features AS (
            SELECT
                mv.territory_id::text AS territory_id,
                mv.name,
                mv.territory_level AS level,
                mv.municipality_ibge_code,
                fi.indicator_code,
                fi.reference_period,
                fi.value::double precision AS value,
                fi.source,
                fi.dataset,
                CASE
                    WHEN fi.value IS NULL THEN 'info'
                    WHEN fi.value >= 80 THEN 'critical'
                    WHEN fi.value >= 60 THEN 'attention'
                    ELSE 'stable'
                END AS severity,
                {geom_expr_3857} AS geom_3857
            FROM {relation} mv
            CROSS JOIN bounds b
            LEFT JOIN LATERAL (
                SELECT
                    indicator_code,
                    reference_period,
                    value,
                    source,
                    dataset,
                    category,
                    updated_at
                FROM silver.fact_indicator fi
                WHERE fi.territory_id = mv.territory_id
                  AND (
                        CAST(:metric AS TEXT) IS NULL
                        OR fi.indicator_code = CAST(:metric AS TEXT)
                    )
                  AND (
                        CAST(:period AS TEXT) IS NULL
                        OR fi.reference_period = CAST(:period AS TEXT)
                    )
                  AND (
                        CAST(:domain AS TEXT) IS NULL
                        OR lower(COALESCE(fi.category, '')) = lower(CAST(:domain AS TEXT))
                    )
                ORDER BY fi.updated_at DESC
                LIMIT 1
            ) fi ON TRUE
            WHERE ST_Intersects({geom_expr_3857}, b.geom)
        ),
        filtered AS (
            SELECT *
            FROM features
            WHERE (CAST(:only_critical AS BOOLEAN) IS FALSE OR severity = 'critical')
        ),
        mvtgeom AS (
            SELECT
                territory_id,
                name,
                level,
                municipality_ibge_code,
                indicator_code,
                reference_period,
                value,
                source,
                dataset,
                severity,
                ST_AsMVTGeom(
                    geom_3857,
                    (SELECT geom FROM bounds),
                    4096,
                    64,
                    TRUE
                ) AS geom
            FROM filtered
        )
        SELECT ST_AsMVT(mvtgeom, :layer, 4096, 'geom') AS tile
        FROM mvtgeom
    """
    params = {
        "z": z,
        "x": x,
        "y": y,
        "metric": metric,
        "period": period,
        "domain": domain,
        "only_critical": only_critical,
        "layer": layer,
    }
    try:
        tile = db.execute(text(tile_sql), params).scalar_one_or_none()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Map tile backend is unavailable. Ensure map SQL objects are applied "
                "with scripts/init_db.py."
            ),
        ) from exc

    tile_bytes = bytes(tile) if tile else b""
    etag = f"\"{sha256(tile_bytes).hexdigest()}\""
    cache_headers = {
        "Cache-Control": "public, max-age=900",
        "ETag": etag,
        "X-Map-Layer": layer,
    }
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=cache_headers)
    return Response(
        content=tile_bytes,
        media_type="application/vnd.mapbox-vector-tile",
        headers=cache_headers,
    )
