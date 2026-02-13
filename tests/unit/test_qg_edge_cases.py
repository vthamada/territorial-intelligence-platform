"""Edge-case contract tests for QG executive endpoints (Sprint 5.2 item 2).

Covers boundary conditions, invalid inputs, empty results, and error shapes
that are not exercised by the happy-path contract tests.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api.main import app


# ── shared fixtures ──────────────────────────


class _EmptySession:
    """Returns empty result sets for any query."""

    class _EmptyResult:
        def mappings(self):
            return self

        def all(self):
            return []

        def first(self):
            return None

    def execute(self, *_args: Any, **_kwargs: Any):
        return self._EmptyResult()


def _empty_db() -> Generator[_EmptySession, None, None]:
    yield _EmptySession()


@pytest.fixture(autouse=True)
def _override_db():
    app.dependency_overrides[get_db] = _empty_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def client():
    return TestClient(app, raise_server_exceptions=False)


# ── normalize_level validation ───────────────


class TestLevelValidation:

    def test_invalid_level_returns_422(self, client: TestClient):
        response = client.get("/v1/kpis/overview?level=invalido")

        assert response.status_code == 422
        payload = response.json()
        assert payload["error"]["code"] == "http_error"
        assert "Invalid level" in str(payload["error"]["details"])

    def test_portuguese_level_accepted(self, client: TestClient):
        response = client.get("/v1/kpis/overview?level=municipio")

        assert response.status_code == 200

    def test_english_level_accepted(self, client: TestClient):
        response = client.get("/v1/kpis/overview?level=municipality")

        assert response.status_code == 200

    def test_level_case_insensitive(self, client: TestClient):
        response = client.get("/v1/kpis/overview?level=MUNICIPALITY")

        assert response.status_code == 200

    def test_invalid_level_on_priority_list(self, client: TestClient):
        response = client.get("/v1/priority/list?level=foo")

        assert response.status_code == 422

    def test_invalid_level_on_electorate_summary(self, client: TestClient):
        response = client.get("/v1/electorate/summary?level=xyz")

        assert response.status_code == 422


# ── limit boundary tests ────────────────────


class TestLimitBoundaries:

    def test_kpis_overview_limit_zero_rejected(self, client: TestClient):
        response = client.get("/v1/kpis/overview?limit=0")

        assert response.status_code == 422

    def test_kpis_overview_limit_above_max_rejected(self, client: TestClient):
        response = client.get("/v1/kpis/overview?limit=21")

        assert response.status_code == 422

    def test_kpis_overview_limit_max_accepted(self, client: TestClient):
        response = client.get("/v1/kpis/overview?limit=20")

        assert response.status_code == 200

    def test_priority_list_limit_above_max_rejected(self, client: TestClient):
        response = client.get("/v1/priority/list?limit=201")

        assert response.status_code == 422

    def test_priority_summary_limit_above_max_rejected(self, client: TestClient):
        response = client.get("/v1/priority/summary?limit=501")

        assert response.status_code == 422

    def test_insights_limit_above_max_rejected(self, client: TestClient):
        response = client.get("/v1/insights/highlights?limit=51")

        assert response.status_code == 422

    def test_negative_limit_rejected(self, client: TestClient):
        response = client.get("/v1/kpis/overview?limit=-1")

        assert response.status_code == 422

    def test_electorate_map_limit_above_max_rejected(self, client: TestClient):
        response = client.get("/v1/electorate/map?limit=5001")

        assert response.status_code == 422


# ── empty data edge cases ───────────────────


class TestEmptyDataResponses:

    def test_kpis_overview_empty_returns_valid_shape(self, client: TestClient):
        response = client.get("/v1/kpis/overview")

        assert response.status_code == 200
        payload = response.json()
        assert payload["items"] == []
        assert payload["metadata"]["source_name"] == "silver.fact_indicator"

    def test_priority_list_empty_returns_valid_shape(self, client: TestClient):
        response = client.get("/v1/priority/list")

        assert response.status_code == 200
        payload = response.json()
        assert payload["items"] == []
        assert payload["period"] is None

    def test_priority_summary_empty_returns_zero_counts(self, client: TestClient):
        response = client.get("/v1/priority/summary")

        assert response.status_code == 200
        payload = response.json()
        assert payload["total_items"] == 0
        assert payload["by_status"] == {}
        assert payload["by_domain"] == {}
        assert payload["top_territories"] == []

    def test_insights_empty_returns_valid_shape(self, client: TestClient):
        response = client.get("/v1/insights/highlights")

        assert response.status_code == 200
        payload = response.json()
        assert payload["items"] == []

    def test_electorate_summary_empty_returns_500_with_mock_db(self, client: TestClient):
        """Electorate endpoints use scalar_one() which fails with stub DB.
        This verifies the error response shape is consistent."""
        response = client.get("/v1/electorate/summary")

        assert response.status_code == 500
        payload = response.json()
        assert payload["error"]["code"] == "internal_error"
        assert payload["error"]["request_id"]

    def test_electorate_map_empty_returns_500_with_mock_db(self, client: TestClient):
        """Electorate map also uses scalar_one() which fails with stub DB."""
        response = client.get("/v1/electorate/map")

        assert response.status_code == 500
        payload = response.json()
        assert payload["error"]["code"] == "internal_error"


# ── territory endpoint edge cases ────────────


class TestTerritoryEdgeCases:

    def test_territory_profile_not_found(self, client: TestClient):
        response = client.get("/v1/territory/9999999/profile")

        assert response.status_code == 404
        payload = response.json()
        assert payload["error"]["code"] == "http_error"
        assert "not found" in str(payload["error"]["details"]).lower()

    def test_territory_compare_missing_with_id(self, client: TestClient):
        """with_id is a required query param — omitting it should return 422."""
        response = client.get("/v1/territory/3121605/compare")

        assert response.status_code == 422

    def test_territory_compare_base_not_found(self, client: TestClient):
        response = client.get("/v1/territory/9999999/compare?with_id=3106200")

        assert response.status_code == 404
        payload = response.json()
        assert "not found" in str(payload["error"]["details"]).lower()

    def test_territory_peers_not_found(self, client: TestClient):
        response = client.get("/v1/territory/9999999/peers")

        assert response.status_code == 404

    def test_territory_profile_limit_boundary(self, client: TestClient):
        response = client.get("/v1/territory/3121605/profile?limit=301")

        assert response.status_code == 422

    def test_territory_peers_limit_boundary(self, client: TestClient):
        response = client.get("/v1/territory/3121605/peers?limit=21")

        assert response.status_code == 422


# ── scenarios/briefs edge cases ──────────────


class TestScenariosEdgeCases:

    def test_scenario_simulate_empty_body_rejected(self, client: TestClient):
        response = client.post("/v1/scenarios/simulate", json={})

        assert response.status_code == 422

    def test_scenario_simulate_no_data_returns_404(self, client: TestClient):
        response = client.post(
            "/v1/scenarios/simulate",
            json={
                "territory_id": "9999999",
                "adjustment_percent": 10,
                "limit": 50,
            },
        )

        assert response.status_code == 404
        payload = response.json()
        details_str = str(payload["error"]["details"]).lower()
        assert "not found" in details_str or "no indicators" in details_str

    def test_brief_generate_no_data_returns_valid_shape(self, client: TestClient):
        """With no territory_id filter, brief returns empty-but-valid response."""
        response = client.post(
            "/v1/briefs",
            json={"level": "municipality", "limit": 20},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["brief_id"]
        assert payload["title"]
        assert isinstance(payload["summary_lines"], list)
        assert isinstance(payload["recommended_actions"], list)
        assert isinstance(payload["evidences"], list)

    def test_brief_generate_with_missing_territory_returns_404(self, client: TestClient):
        response = client.post(
            "/v1/briefs",
            json={"territory_id": "9999999", "level": "municipality", "limit": 20},
        )

        assert response.status_code == 404


# ── severity regex validation ────────────────


class TestInsightsSeverityValidation:

    def test_valid_severity_critical(self, client: TestClient):
        response = client.get("/v1/insights/highlights?severity=critical")

        assert response.status_code == 200

    def test_valid_severity_attention(self, client: TestClient):
        response = client.get("/v1/insights/highlights?severity=attention")

        assert response.status_code == 200

    def test_valid_severity_info(self, client: TestClient):
        response = client.get("/v1/insights/highlights?severity=info")

        assert response.status_code == 200

    def test_invalid_severity_rejected(self, client: TestClient):
        response = client.get("/v1/insights/highlights?severity=unknown")

        assert response.status_code == 422


# ── electorate year validation ───────────────


class TestElectorateYearValidation:

    def test_year_below_minimum_rejected(self, client: TestClient):
        response = client.get("/v1/electorate/summary?year=1899")

        assert response.status_code == 422

    def test_year_above_maximum_rejected(self, client: TestClient):
        response = client.get("/v1/electorate/summary?year=2200")

        assert response.status_code == 422

    def test_year_non_numeric_rejected(self, client: TestClient):
        response = client.get("/v1/electorate/summary?year=abc")

        assert response.status_code == 422


# ── electorate map metric validation ─────────


class TestElectorateMapMetricValidation:

    def test_valid_metric_accepted(self, client: TestClient):
        """Valid metrics pass regex validation (may 500 due to mock DB scalar_one)."""
        for metric in ["voters", "turnout", "abstention_rate", "blank_rate", "null_rate"]:
            response = client.get(f"/v1/electorate/map?metric={metric}")
            # Regex validation passes (not 422); 500 is expected with stub DB
            assert response.status_code in (200, 500), f"metric={metric} returned {response.status_code}"

    def test_invalid_metric_rejected(self, client: TestClient):
        response = client.get("/v1/electorate/map?metric=invalid_metric")

        assert response.status_code == 422


# ── request-id propagation ──────────────────


class TestRequestIdPropagation:

    def test_custom_request_id_propagated_on_success(self, client: TestClient):
        rid = "req-edge-case-001"
        response = client.get("/v1/kpis/overview", headers={"x-request-id": rid})

        assert response.status_code == 200
        assert response.headers.get("x-request-id") == rid

    def test_custom_request_id_propagated_on_422(self, client: TestClient):
        rid = "req-edge-case-002"
        response = client.get(
            "/v1/kpis/overview?level=invalido",
            headers={"x-request-id": rid},
        )

        assert response.status_code == 422
        assert response.headers.get("x-request-id") == rid

    def test_auto_generated_request_id_present(self, client: TestClient):
        response = client.get("/v1/kpis/overview")

        assert response.status_code == 200
        assert response.headers.get("x-request-id")


# ── content-type on errors ──────────────────


class TestErrorContentType:

    def test_422_returns_json(self, client: TestClient):
        response = client.get("/v1/kpis/overview?limit=0")

        assert response.status_code == 422
        assert "application/json" in response.headers.get("content-type", "")

    def test_404_returns_json(self, client: TestClient):
        response = client.get("/v1/territory/0000000/profile")

        assert response.status_code == 404
        assert "application/json" in response.headers.get("content-type", "")
