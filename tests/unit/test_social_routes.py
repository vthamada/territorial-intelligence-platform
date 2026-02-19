from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api.main import app


class _CountResult:
    def __init__(self, value: int) -> None:
        self._value = value

    def scalar_one(self) -> int:
        return self._value


class _RowsResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> _RowsResult:
        return self

    def all(self) -> list[dict[str, Any]]:
        return self._rows


class _SocialSession:
    def __init__(self) -> None:
        self.last_params: dict[str, Any] | None = None

    def execute(self, *_args: Any, **_kwargs: Any) -> _CountResult | _RowsResult:
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]
        if isinstance(params, dict):
            self.last_params = params

        sql = str(_args[0]).lower() if _args else ""
        if "from silver.fact_social_protection" in sql and "count(*)" in sql:
            return _CountResult(1)
        if "from silver.fact_social_assistance_network" in sql and "count(*)" in sql:
            return _CountResult(1)
        if "from silver.fact_social_protection" in sql:
            return _RowsResult(
                [
                    {
                        "fact_id": "11111111-1111-1111-1111-111111111111",
                        "territory_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                        "source": "CECAD",
                        "dataset": "cecad_social_protection_municipal",
                        "reference_period": "2025",
                        "households_total": 1200,
                        "people_total": 3500,
                        "avg_income_per_capita": 210.5,
                        "poverty_rate": 28.1,
                        "extreme_poverty_rate": 9.3,
                        "metadata_json": {"source_type": "manual"},
                        "updated_at": datetime(2026, 2, 19, 1, 0, tzinfo=UTC),
                    }
                ]
            )
        if "from silver.fact_social_assistance_network" in sql:
            return _RowsResult(
                [
                    {
                        "fact_id": "22222222-2222-2222-2222-222222222222",
                        "territory_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                        "source": "CENSO_SUAS",
                        "dataset": "censo_suas_assistance_network_municipal",
                        "reference_period": "2025",
                        "cras_units": 4,
                        "creas_units": 1,
                        "social_units_total": 8,
                        "workers_total": 95,
                        "service_capacity_total": 4100,
                        "metadata_json": {"source_type": "manual"},
                        "updated_at": datetime(2026, 2, 19, 1, 0, tzinfo=UTC),
                    }
                ]
            )
        raise AssertionError(f"Unexpected SQL in social routes test: {sql}")


def _social_db() -> Generator[_SocialSession, None, None]:
    yield _SocialSession()


def test_social_protection_endpoint_returns_paginated_payload() -> None:
    app.dependency_overrides[get_db] = _social_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/social/protection?page=1&page_size=10&period=2025")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["page_size"] == 10
    assert payload["total"] == 1
    assert payload["items"][0]["source"] == "CECAD"
    assert payload["items"][0]["households_total"] == 1200
    app.dependency_overrides.clear()


def test_social_assistance_network_endpoint_returns_paginated_payload() -> None:
    app.dependency_overrides[get_db] = _social_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/social/assistance-network?page=1&page_size=10&period=2025")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["page_size"] == 10
    assert payload["total"] == 1
    assert payload["items"][0]["source"] == "CENSO_SUAS"
    assert payload["items"][0]["cras_units"] == 4
    app.dependency_overrides.clear()


def test_social_routes_accept_period_filter_params() -> None:
    session = _SocialSession()

    def _db() -> Generator[_SocialSession, None, None]:
        yield session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/v1/social/protection"
        "?period=2025"
        "&source=CECAD"
        "&dataset=cecad_social_protection_municipal"
    )

    assert response.status_code == 200
    assert session.last_params is not None
    assert session.last_params["period"] == "2025"
    assert session.last_params["source"] == "CECAD"
    assert session.last_params["dataset"] == "cecad_social_protection_municipal"
    app.dependency_overrides.clear()
