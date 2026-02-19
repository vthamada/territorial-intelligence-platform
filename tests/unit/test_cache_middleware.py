"""Tests for the cache header middleware."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import app
from app.api.cache_middleware import _match_cache_rule


def test_map_layers_has_cache_control_header() -> None:
    client = TestClient(app)
    response = client.get("/v1/map/layers")

    assert response.status_code == 200
    assert "cache-control" in response.headers
    assert "max-age=3600" in response.headers["cache-control"]


def test_match_cache_rule_prefers_operational_layers_paths() -> None:
    assert _match_cache_rule("/v1/map/layers/readiness") == 60
    assert _match_cache_rule("/v1/map/layers/coverage") == 60
    assert _match_cache_rule("/v1/map/layers") == 3600


def test_map_style_metadata_has_cache_control_header() -> None:
    client = TestClient(app)
    response = client.get("/v1/map/style-metadata")

    assert response.status_code == 200
    assert "cache-control" in response.headers
    assert "max-age=3600" in response.headers["cache-control"]


def test_map_layers_returns_etag_header() -> None:
    client = TestClient(app)
    response = client.get("/v1/map/layers")

    assert response.status_code == 200
    assert "etag" in response.headers
    etag = response.headers["etag"]
    assert etag.startswith('W/"')


def test_conditional_request_returns_304_when_body_matches() -> None:
    """304 must be returned when ETag matches response body."""
    client = TestClient(app)
    first = client.get("/v1/map/layers")
    etag = first.headers.get("etag")
    assert etag

    second = client.get("/v1/map/layers", headers={"If-None-Match": etag})
    assert second.status_code == 304
    assert second.headers.get("etag") == etag


def test_non_cacheable_endpoint_has_no_cache_header() -> None:
    client = TestClient(app)
    response = client.get("/v1/health")

    assert response.status_code == 200
    assert "cache-control" not in response.headers


def test_post_request_not_cached() -> None:
    """POST requests should never receive cache headers."""
    client = TestClient(app)
    # Use a path that would match cache rules if it were GET
    response = client.post(
        "/v1/map/layers",
        headers={"Content-Type": "application/json"},
    )
    # It will likely return 405, but should not have cache headers
    assert "cache-control" not in response.headers
