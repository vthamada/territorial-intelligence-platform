from __future__ import annotations

from collections.abc import Generator
from typing import Any

from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api.main import app


class _FailingSession:
    def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("forced-db-error")


class _TileResult:
    def __init__(self, value: bytes | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> bytes | None:
        return self._value


class _TileSession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _TileResult:
        return _TileResult(b"\x1a\x02")


class _MappingsResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> _MappingsResult:
        return self

    def all(self) -> list[dict[str, Any]]:
        return self._rows


class _UrbanSession:
    def execute(self, statement: Any, *_args: Any, **_kwargs: Any) -> _MappingsResult:
        sql = str(statement)
        if "FROM map.urban_road_segment" in sql and "COALESCE(ST_Length(ST_Transform(geom, 31983))" in sql:
            return _MappingsResult(
                [
                    {
                        "road_id": "1",
                        "source": "OSM",
                        "name": "Rua da Quitanda",
                        "road_class": "residential",
                        "length_m": 123.4,
                        "geometry_json": '{"type":"LineString","coordinates":[[-43.601,-18.244],[-43.600,-18.243]]}',
                    }
                ]
            )
        if "WITH ranked AS" in sql and "FROM map.urban_road_segment r" in sql:
            return _MappingsResult(
                [
                    {
                        "feature_type": "road",
                        "feature_id": "1",
                        "source": "OSM",
                        "name": "Rua da Quitanda",
                        "category": "residential",
                        "subcategory": None,
                        "score": 3,
                        "geometry_json": '{"type":"Point","coordinates":[-43.6005,-18.2438]}',
                    },
                    {
                        "feature_type": "poi",
                        "feature_id": "10",
                        "source": "OSM",
                        "name": "UBS Centro",
                        "category": "health",
                        "subcategory": "primary_care",
                        "score": 2,
                        "geometry_json": '{"type":"Point","coordinates":[-43.6005,-18.2438]}',
                    },
                ]
            )
        if "FROM map.urban_poi p" in sql and "ST_DWithin" in sql:
            return _MappingsResult(
                [
                    {
                        "poi_id": "10",
                        "source": "OSM",
                        "name": "UBS Centro",
                        "category": "health",
                        "subcategory": "primary_care",
                        "distance_m": 84.7,
                        "geometry_json": '{"type":"Point","coordinates":[-43.6005,-18.2438]}',
                    }
                ]
            )
        if "FROM map.urban_poi" in sql and "ORDER BY poi_id" in sql:
            return _MappingsResult(
                [
                    {
                        "poi_id": "10",
                        "source": "OSM",
                        "name": "UBS Centro",
                        "category": "health",
                        "subcategory": "primary_care",
                        "geometry_json": '{"type":"Point","coordinates":[-43.6005,-18.2438]}',
                    }
                ]
            )
        return _MappingsResult([])


def _fake_db() -> Generator[object, None, None]:
    yield object()


def _failing_db() -> Generator[_FailingSession, None, None]:
    yield _FailingSession()


def _tile_db() -> Generator[_TileSession, None, None]:
    yield _TileSession()


def _urban_db() -> Generator[_UrbanSession, None, None]:
    yield _UrbanSession()


def test_v1_health_includes_request_id_header(monkeypatch) -> None:
    monkeypatch.setattr("app.api.main.healthcheck", lambda: "ok")
    client = TestClient(app)

    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}
    assert response.headers.get("x-request-id")


def test_validation_error_contract_shape() -> None:
    app.dependency_overrides[get_db] = _fake_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/geo/choropleth")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"]
    assert isinstance(payload["error"]["details"], dict)
    assert payload["error"]["request_id"]
    assert response.headers.get("x-request-id") == payload["error"]["request_id"]
    app.dependency_overrides.clear()


def test_map_layers_contract_shape() -> None:
    client = TestClient(app)

    response = client.get("/v1/map/layers")

    assert response.status_code == 200
    payload = response.json()
    assert payload["default_layer_id"] == "territory_municipality"
    assert payload["fallback_endpoint"] == "/v1/geo/choropleth"
    assert isinstance(payload["items"], list)
    assert len(payload["items"]) >= 2
    first = payload["items"][0]
    assert first["id"]
    assert first["label"]
    assert first["territory_level"] in {"municipality", "district", "census_sector"}
    assert isinstance(first["default_visibility"], bool)
    assert isinstance(first["zoom_min"], int)
    assert response.headers.get("x-request-id")


def test_map_style_metadata_contract_shape() -> None:
    client = TestClient(app)

    response = client.get("/v1/map/style-metadata")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "v1"
    assert payload["default_mode"] == "choropleth"
    assert isinstance(payload["severity_palette"], list)
    assert isinstance(payload["domain_palette"], list)
    assert isinstance(payload["legend_ranges"], list)
    assert payload["notes"] == "style_metadata_v1_static"
    assert response.headers.get("x-request-id")


def test_map_tiles_contract_shape() -> None:
    app.dependency_overrides[get_db] = _tile_db
    client = TestClient(app)

    response = client.get("/v1/map/tiles/territory_municipality/8/73/97.mvt")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.mapbox-vector-tile"
    assert response.headers.get("etag")
    assert response.headers.get("cache-control") == "public, max-age=900"
    assert response.headers.get("x-map-layer") == "territory_municipality"
    assert response.content == b"\x1a\x02"
    app.dependency_overrides.clear()


def test_map_tiles_urban_contract_shape() -> None:
    app.dependency_overrides[get_db] = _tile_db
    client = TestClient(app)

    response = client.get("/v1/map/tiles/urban_roads/14/4689/6586.mvt")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.mapbox-vector-tile"
    assert response.headers.get("etag")
    assert response.headers.get("cache-control") == "public, max-age=900"
    assert response.headers.get("x-map-layer") == "urban_roads"
    assert response.content == b"\x1a\x02"
    app.dependency_overrides.clear()


def test_map_tiles_supports_conditional_etag() -> None:
    app.dependency_overrides[get_db] = _tile_db
    client = TestClient(app)

    first = client.get("/v1/map/tiles/territory_municipality/8/73/97.mvt")
    etag = first.headers.get("etag")
    assert etag

    second = client.get(
        "/v1/map/tiles/territory_municipality/8/73/97.mvt",
        headers={"if-none-match": etag},
    )
    assert second.status_code == 304
    assert second.content == b""
    app.dependency_overrides.clear()


def test_map_tiles_unknown_layer_returns_404() -> None:
    app.dependency_overrides[get_db] = _tile_db
    client = TestClient(app)

    response = client.get("/v1/map/tiles/unknown_layer/8/73/97.mvt")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "http_error"
    app.dependency_overrides.clear()


def test_map_urban_roads_contract_shape() -> None:
    app.dependency_overrides[get_db] = _urban_db
    client = TestClient(app)

    response = client.get("/v1/map/urban/roads?bbox=-43.61,-18.25,-43.59,-18.23&limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    first = payload["items"][0]
    assert first["road_id"] == "1"
    assert first["source"] == "OSM"
    assert first["road_class"] == "residential"
    assert first["geometry"]["type"] == "LineString"
    app.dependency_overrides.clear()


def test_map_urban_pois_contract_shape() -> None:
    app.dependency_overrides[get_db] = _urban_db
    client = TestClient(app)

    response = client.get("/v1/map/urban/pois?category=health&limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    first = payload["items"][0]
    assert first["poi_id"] == "10"
    assert first["category"] == "health"
    assert first["geometry"]["type"] == "Point"
    app.dependency_overrides.clear()


def test_map_urban_nearby_pois_contract_shape() -> None:
    app.dependency_overrides[get_db] = _urban_db
    client = TestClient(app)

    response = client.get("/v1/map/urban/nearby-pois?lon=-43.60&lat=-18.24&radius_m=500")

    assert response.status_code == 200
    payload = response.json()
    assert payload["radius_m"] == 500.0
    assert payload["count"] == 1
    first = payload["items"][0]
    assert first["poi_id"] == "10"
    assert first["distance_m"] == 84.7
    app.dependency_overrides.clear()


def test_map_urban_geocode_contract_shape() -> None:
    app.dependency_overrides[get_db] = _urban_db
    client = TestClient(app)

    response = client.get("/v1/map/urban/geocode?q=Rua&kind=all&limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "Rua"
    assert payload["count"] == 2
    assert payload["items"][0]["feature_type"] == "road"
    assert payload["items"][1]["feature_type"] == "poi"
    app.dependency_overrides.clear()


def test_map_urban_roads_invalid_bbox_returns_422() -> None:
    app.dependency_overrides[get_db] = _urban_db
    client = TestClient(app)

    response = client.get("/v1/map/urban/roads?bbox=-43.6,-18.2,-43.7")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "http_error"
    app.dependency_overrides.clear()


def test_http_error_contract_with_custom_request_id() -> None:
    app.dependency_overrides[get_db] = _fake_db
    client = TestClient(app, raise_server_exceptions=False)
    request_id = "req-contract-http-error"

    response = client.get(
        "/v1/territories?level=invalido",
        headers={"x-request-id": request_id},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "http_error"
    assert payload["error"]["request_id"] == request_id
    assert response.headers.get("x-request-id") == request_id
    app.dependency_overrides.clear()


def test_internal_error_contract_shape() -> None:
    app.dependency_overrides[get_db] = _failing_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/territories?level=municipio")

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "internal_error"
    assert payload["error"]["message"]
    assert payload["error"]["details"]["detail"] == "forced-db-error"
    assert payload["error"]["request_id"]
    assert response.headers.get("x-request-id") == payload["error"]["request_id"]
    app.dependency_overrides.clear()
