"""Tests for the MVT tiles endpoint and helpers."""
from __future__ import annotations

import math

import pytest

from app.api.routes_map import _tile_to_bbox, _LAYER_TO_LEVEL, _tolerance_for_zoom, _TILE_METRICS


class TestTileToBbox:
    def test_zoom_zero(self) -> None:
        """Full world at z=0 x=0 y=0."""
        bbox = _tile_to_bbox(0, 0, 0)
        assert len(bbox) == 4
        lon_min, lat_min, lon_max, lat_max = bbox
        assert lon_min == pytest.approx(-180.0)
        assert lon_max == pytest.approx(180.0)
        assert lat_min == pytest.approx(-85.05, abs=0.1)
        assert lat_max == pytest.approx(85.05, abs=0.1)

    def test_zoom_one(self) -> None:
        """z=1 x=0 y=0 is the top-left quadrant."""
        bbox = _tile_to_bbox(1, 0, 0)
        lon_min, lat_min, lon_max, lat_max = bbox
        assert lon_min == pytest.approx(-180.0)
        assert lon_max == pytest.approx(0.0)
        assert lat_max == pytest.approx(85.05, abs=0.1)
        assert lat_min == pytest.approx(0.0, abs=0.1)

    def test_higher_zoom(self) -> None:
        """z=5 tile covers a small area."""
        bbox = _tile_to_bbox(5, 10, 15)
        lon_min, lat_min, lon_max, lat_max = bbox
        assert lon_min < lon_max
        assert lat_min < lat_max
        # Each tile at z=5 covers 360/32 = 11.25 degrees longitude
        assert lon_max - lon_min == pytest.approx(11.25)


class TestLayerMapping:
    def test_known_layers(self) -> None:
        assert _LAYER_TO_LEVEL["territory_municipality"] == "municipality"
        assert _LAYER_TO_LEVEL["territory_district"] == "district"
        assert _LAYER_TO_LEVEL["territory_census_sector"] == "census_sector"
        assert _LAYER_TO_LEVEL["territory_neighborhood_proxy"] == "census_sector"
        assert _LAYER_TO_LEVEL["territory_electoral_zone"] == "electoral_zone"
        assert _LAYER_TO_LEVEL["territory_electoral_section"] == "electoral_section"
        assert _LAYER_TO_LEVEL["territory_polling_place"] == "electoral_section"
        assert _LAYER_TO_LEVEL["urban_roads"] == "urban"
        assert _LAYER_TO_LEVEL["urban_pois"] == "urban"

    def test_unknown_layer(self) -> None:
        assert _LAYER_TO_LEVEL.get("nonexistent") is None


class TestMultiLevelTolerance:
    """Verify zoom-dependent simplification tolerance bands."""

    def test_overview_zoom_coarse(self) -> None:
        """z0-4 should use coarsest tolerance."""
        for z in (0, 2, 4):
            assert _tolerance_for_zoom(z) == 20000.0

    def test_state_zoom_moderate(self) -> None:
        """z5-8 should use moderate tolerance."""
        for z in (5, 7, 8):
            assert _tolerance_for_zoom(z) == 5000.0

    def test_city_zoom_fine(self) -> None:
        """z9-11 should use fine tolerance."""
        for z in (9, 10, 11):
            assert _tolerance_for_zoom(z) == 1500.0

    def test_neighborhood_zoom_very_fine(self) -> None:
        """z12-14 should use very fine tolerance."""
        for z in (12, 13, 14):
            assert _tolerance_for_zoom(z) == 400.0

    def test_block_zoom_near_lossless(self) -> None:
        """z15+ should use near-lossless tolerance."""
        for z in (15, 18):
            assert _tolerance_for_zoom(z) == 100.0

    def test_tolerance_decreases_with_zoom(self) -> None:
        """Higher zoom levels should always produce equal or lower tolerance."""
        prev = _tolerance_for_zoom(0)
        for z in range(1, 19):
            current = _tolerance_for_zoom(z)
            assert current <= prev, f"z={z}: {current} should be <= {prev}"
            prev = current


class TestMvtEndpointValidation:
    """Test that invalid layer returns 404 (no DB needed)."""

    def test_unknown_layer_returns_404(self) -> None:
        from collections.abc import Generator
        from fastapi.testclient import TestClient
        from app.api.deps import get_db
        from app.api.main import app

        # Override DB with a dummy that shouldn't be called
        def _fake_db() -> Generator[object, None, None]:
            yield object()

        app.dependency_overrides[get_db] = _fake_db
        try:
            client = TestClient(app)
            response = client.get("/v1/map/tiles/nonexistent_layer/0/0/0.mvt")
            assert response.status_code == 404
            body = response.json()
            assert body["error"]["code"] == "http_error"
            assert body["error"]["details"]["reason"] == "Unknown layer"
            assert body["error"]["details"]["layer"] == "nonexistent_layer"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_tile_metrics_endpoint_returns_structure(self) -> None:
        from fastapi.testclient import TestClient
        from app.api.main import app

        client = TestClient(app)
        response = client.get("/v1/map/tiles/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "p50_ms" in data
        assert "p95_ms" in data
        assert "p99_ms" in data
        assert "by_layer" in data

    def test_layer_metadata_endpoint_known_layer(self) -> None:
        from fastapi.testclient import TestClient
        from app.api.main import app

        client = TestClient(app)
        response = client.get("/v1/map/layers/territory_municipality/metadata")
        assert response.status_code == 200
        payload = response.json()
        assert payload["layer"]["id"] == "territory_municipality"
        assert payload["layer"]["official_status"] == "official"
        assert "methodology" in payload
        assert "limitations" in payload

    def test_layer_metadata_endpoint_unknown_layer(self) -> None:
        from fastapi.testclient import TestClient
        from app.api.main import app

        client = TestClient(app)
        response = client.get("/v1/map/layers/nonexistent/metadata")
        assert response.status_code == 404

    def test_territory_layers_catalog_alias_endpoint(self) -> None:
        from fastapi.testclient import TestClient
        from app.api.main import app

        client = TestClient(app)
        response = client.get("/v1/territory/layers/catalog")
        assert response.status_code == 200
        payload = response.json()
        assert payload["default_layer_id"] == "territory_municipality"
        assert len(payload["items"]) >= 6

    def test_territory_layers_metadata_alias_endpoint(self) -> None:
        from fastapi.testclient import TestClient
        from app.api.main import app

        client = TestClient(app)
        response = client.get("/v1/territory/layers/territory_district/metadata")
        assert response.status_code == 200
        payload = response.json()
        assert payload["layer"]["id"] == "territory_district"

    def test_polling_place_metadata_endpoint(self) -> None:
        from fastapi.testclient import TestClient
        from app.api.main import app

        client = TestClient(app)
        response = client.get("/v1/map/layers/territory_polling_place/metadata")
        assert response.status_code == 200
        payload = response.json()
        assert payload["layer"]["id"] == "territory_polling_place"
        assert payload["layer"]["layer_kind"] == "point"

    def test_territory_layers_readiness_endpoint(self) -> None:
        from collections.abc import Generator
        from fastapi.testclient import TestClient
        from app.api.deps import get_db
        from app.api.main import app

        class _FakeResult:
            def __init__(self, rows: list[dict[str, object]]) -> None:
                self._rows = rows

            def mappings(self) -> "_FakeResult":
                return self

            def all(self) -> list[dict[str, object]]:
                return self._rows

            def first(self) -> dict[str, object] | None:
                return self._rows[0] if self._rows else None

        class _FakeSession:
            def execute(self, statement, _params=None) -> _FakeResult:
                sql = str(statement)
                if "FROM silver.dim_territory" in sql and "GROUP BY level::text" in sql:
                    return _FakeResult(
                        [
                            {
                                "territory_level": "municipality",
                                "territories_total": 1,
                                "territories_with_geometry": 1,
                            },
                            {
                                "territory_level": "district",
                                "territories_total": 2,
                                "territories_with_geometry": 2,
                            },
                        ]
                    )
                if "JOIN silver.fact_indicator fi" in sql:
                    return _FakeResult(
                        [
                            {"territory_level": "municipality", "territories_with_indicator": 1},
                            {"territory_level": "district", "territories_with_indicator": 1},
                        ]
                    )
                if "FROM ops.pipeline_runs" in sql and "quality_suite" in sql:
                    return _FakeResult(
                        [{"run_id": "11111111-1111-1111-1111-111111111111", "started_at_utc": "2026-02-13T15:00:00Z"}]
                    )
                if "FROM ops.pipeline_checks" in sql and "map_layer_rows_" in sql:
                    return _FakeResult(
                        [
                            {
                                "check_name": "map_layer_rows_municipality",
                                "status": "pass",
                                "details": "ok",
                                "observed_value": 1,
                                "threshold_value": 1,
                            },
                            {
                                "check_name": "map_layer_geometry_ratio_municipality",
                                "status": "pass",
                                "details": "ok",
                                "observed_value": 1,
                                "threshold_value": 1,
                            },
                        ]
                    )
                return _FakeResult([])

        def _fake_db() -> Generator[object, None, None]:
            yield _FakeSession()

        app.dependency_overrides[get_db] = _fake_db
        try:
            client = TestClient(app)
            response = client.get("/v1/territory/layers/readiness")
            assert response.status_code == 200
            payload = response.json()
            assert payload["quality_run_id"] == "11111111-1111-1111-1111-111111111111"
            assert len(payload["items"]) >= 5
            assert payload["items"][0]["layer"]["id"] == "territory_municipality"
            assert payload["items"][0]["readiness_status"] in {"pass", "warn", "fail", "pending"}
        finally:
            app.dependency_overrides.pop(get_db, None)
