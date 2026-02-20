from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api.main import app


class _RowsResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> _RowsResult:
        return self

    def all(self) -> list[dict[str, Any]]:
        return self._rows

    def first(self) -> dict[str, Any] | None:
        if not self._rows:
            return None
        return self._rows[0]


class _ScalarResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one(self) -> Any:
        return self._value


class _QgSession:
    def __init__(self) -> None:
        self.last_params: dict[str, Any] | None = None

    def execute(self, *_args: Any, **_kwargs: Any) -> _RowsResult:
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]
        if isinstance(params, dict):
            self.last_params = params

        sql = str(_args[0]).lower() if _args else ""
        if "avg(fi.value)" in sql:
            return _RowsResult(
                [
                    {
                        "domain": "saude",
                        "indicator_code": "DATASUS_APS_COBERTURA",
                        "indicator_name": "Cobertura APS",
                        "value": 82.5,
                        "unit": "%",
                        "territory_level": "municipality",
                        "updated_at": datetime(2026, 2, 11, 13, 0, tzinfo=UTC),
                    },
                    {
                        "domain": "trabalho",
                        "indicator_code": "MTE_NOVO_CAGED_SALDO_TOTAL",
                        "indicator_name": "Saldo de Empregos",
                        "value": 120.0,
                        "unit": "postos",
                        "territory_level": "municipality",
                        "updated_at": datetime(2026, 2, 11, 12, 0, tzinfo=UTC),
                    },
                ]
            )

        if "with base as" in sql:
            return _RowsResult(
                [
                    {
                        "territory_id": "3121605",
                        "territory_name": "Diamantina",
                        "territory_level": "municipality",
                        "domain": "saude",
                        "indicator_code": "DATASUS_APS_COBERTURA",
                        "indicator_name": "Cobertura APS",
                        "value": 45.0,
                        "unit": "%",
                        "reference_period": "2025",
                        "source": "DATASUS",
                        "dataset": "datasus_health",
                        "updated_at": datetime(2026, 2, 11, 13, 0, tzinfo=UTC),
                        "score": 90.0,
                        "status": "critical",
                    },
                    {
                        "territory_id": "3121605",
                        "territory_name": "Diamantina",
                        "territory_level": "municipality",
                        "domain": "educacao",
                        "indicator_code": "INEP_ABANDONO_ESCOLAR",
                        "indicator_name": "Abandono Escolar",
                        "value": 8.2,
                        "unit": "%",
                        "reference_period": "2025",
                        "source": "INEP",
                        "dataset": "inep_education",
                        "updated_at": datetime(2026, 2, 11, 12, 30, tzinfo=UTC),
                        "score": 63.0,
                        "status": "attention",
                    },
                    {
                        "territory_id": "3121605",
                        "territory_name": "Diamantina",
                        "territory_level": "municipality",
                        "domain": "trabalho",
                        "indicator_code": "MTE_NOVO_CAGED_SALDO_TOTAL",
                        "indicator_name": "Saldo de Empregos",
                        "value": 120.0,
                        "unit": "postos",
                        "reference_period": "2025",
                        "source": "MTE",
                        "dataset": "mte_novo_caged",
                        "updated_at": datetime(2026, 2, 11, 11, 0, tzinfo=UTC),
                        "score": 35.0,
                        "status": "stable",
                    },
                ]
            )

        raise AssertionError(f"Unexpected SQL in QG test: {sql}")


class _TerritoryProfileSession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _RowsResult:
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]
        sql = str(_args[0]).lower() if _args else ""
        if "from silver.dim_territory" in sql:
            return _RowsResult(
                [
                    {
                        "territory_id": "3121605",
                        "territory_name": "Diamantina",
                        "territory_level": "municipality",
                    }
                ]
            )
        if "with latest as" in sql and "partition by dt.territory_id, fi.indicator_code" in sql:
            period = str((params or {}).get("period"))
            if period == "2025":
                return _RowsResult(
                    [
                        {
                            "territory_id": "3121605",
                            "domain": "saude",
                            "indicator_code": "DATASUS_APS_COBERTURA",
                            "score": 82.0,
                            "status": "critical",
                        },
                        {
                            "territory_id": "3121605",
                            "domain": "trabalho",
                            "indicator_code": "MTE_NOVO_CAGED_SALDO_TOTAL",
                            "score": 67.0,
                            "status": "attention",
                        },
                    ]
                )
            if period == "2024":
                return _RowsResult(
                    [
                        {
                            "territory_id": "3121605",
                            "domain": "saude",
                            "indicator_code": "DATASUS_APS_COBERTURA",
                            "score": 72.0,
                            "status": "attention",
                        },
                        {
                            "territory_id": "3121605",
                            "domain": "trabalho",
                            "indicator_code": "MTE_NOVO_CAGED_SALDO_TOTAL",
                            "score": 58.0,
                            "status": "attention",
                        },
                    ]
                )
            return _RowsResult([])
        if "with ranked as" in sql and "from silver.fact_indicator fi" in sql:
            return _RowsResult(
                [
                    {
                        "domain": "saude",
                        "indicator_code": "DATASUS_APS_COBERTURA",
                        "indicator_name": "Cobertura APS",
                        "value": 75.0,
                        "unit": "%",
                        "reference_period": "2025",
                        "source": "DATASUS",
                        "dataset": "datasus_health",
                        "updated_at": datetime(2026, 2, 11, 13, 0, tzinfo=UTC),
                    },
                    {
                        "domain": "trabalho",
                        "indicator_code": "MTE_NOVO_CAGED_SALDO_TOTAL",
                        "indicator_name": "Saldo CAGED",
                        "value": 120.0,
                        "unit": "postos",
                        "reference_period": "2025",
                        "source": "MTE",
                        "dataset": "mte_novo_caged",
                        "updated_at": datetime(2026, 2, 11, 12, 0, tzinfo=UTC),
                    },
                ]
            )
        raise AssertionError(f"Unexpected SQL in territory profile test: {sql}")


class _TerritoryCompareSession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _RowsResult:
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]
        sql = str(_args[0]).lower() if _args else ""

        if "from silver.dim_territory" in sql:
            territory_id = str(params["territory_id"])
            if territory_id == "3121605":
                return _RowsResult(
                    [
                        {
                            "territory_id": "3121605",
                            "territory_name": "Diamantina",
                            "territory_level": "municipality",
                        }
                    ]
                )
            return _RowsResult(
                [
                    {
                        "territory_id": "3106200",
                        "territory_name": "Belo Horizonte",
                        "territory_level": "municipality",
                    }
                ]
            )

        if "with ranked as" in sql and "from silver.fact_indicator fi" in sql:
            territory_id = str(params["territory_id"])
            if territory_id == "3121605":
                return _RowsResult(
                    [
                        {
                            "domain": "saude",
                            "indicator_code": "DATASUS_APS_COBERTURA",
                            "indicator_name": "Cobertura APS",
                            "value": 70.0,
                            "unit": "%",
                            "reference_period": "2025",
                            "source": "DATASUS",
                            "dataset": "datasus_health",
                            "updated_at": datetime(2026, 2, 11, 12, 0, tzinfo=UTC),
                        },
                        {
                            "domain": "trabalho",
                            "indicator_code": "MTE_NOVO_CAGED_SALDO_TOTAL",
                            "indicator_name": "Saldo CAGED",
                            "value": 110.0,
                            "unit": "postos",
                            "reference_period": "2025",
                            "source": "MTE",
                            "dataset": "mte_novo_caged",
                            "updated_at": datetime(2026, 2, 11, 11, 0, tzinfo=UTC),
                        },
                    ]
                )
            return _RowsResult(
                [
                    {
                        "domain": "saude",
                        "indicator_code": "DATASUS_APS_COBERTURA",
                        "indicator_name": "Cobertura APS",
                        "value": 55.0,
                        "unit": "%",
                        "reference_period": "2025",
                        "source": "DATASUS",
                        "dataset": "datasus_health",
                        "updated_at": datetime(2026, 2, 11, 10, 0, tzinfo=UTC),
                    },
                    {
                        "domain": "trabalho",
                        "indicator_code": "MTE_NOVO_CAGED_SALDO_TOTAL",
                        "indicator_name": "Saldo CAGED",
                        "value": 140.0,
                        "unit": "postos",
                        "reference_period": "2025",
                        "source": "MTE",
                        "dataset": "mte_novo_caged",
                        "updated_at": datetime(2026, 2, 11, 9, 0, tzinfo=UTC),
                    },
                ]
            )

        raise AssertionError(f"Unexpected SQL in territory compare test: {sql}")


class _TerritoryPeersSession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _RowsResult:
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]
        sql = str(_args[0]).lower() if _args else ""

        if "from silver.dim_territory" in sql:
            return _RowsResult(
                [
                    {
                        "territory_id": "3121605",
                        "territory_name": "Diamantina",
                        "territory_level": "municipality",
                    }
                ]
            )

        if "with latest as" in sql and "partition by dt.territory_id, fi.indicator_code" in sql:
            territory_id = (params or {}).get("territory_id")
            if territory_id == "3121605":
                return _RowsResult(
                    [
                        {
                            "territory_id": "3121605",
                            "territory_name": "Diamantina",
                            "territory_level": "municipality",
                            "domain": "saude",
                            "indicator_code": "DATASUS_APS_COBERTURA",
                            "score": 80.0,
                            "updated_at": datetime(2026, 2, 11, 13, 0, tzinfo=UTC),
                            "status": "critical",
                        },
                        {
                            "territory_id": "3121605",
                            "territory_name": "Diamantina",
                            "territory_level": "municipality",
                            "domain": "trabalho",
                            "indicator_code": "MTE_NOVO_CAGED_SALDO_TOTAL",
                            "score": 60.0,
                            "updated_at": datetime(2026, 2, 11, 13, 0, tzinfo=UTC),
                            "status": "attention",
                        },
                    ]
                )

            return _RowsResult(
                [
                    {
                        "territory_id": "3121605",
                        "territory_name": "Diamantina",
                        "territory_level": "municipality",
                        "domain": "saude",
                        "indicator_code": "DATASUS_APS_COBERTURA",
                        "score": 80.0,
                        "updated_at": datetime(2026, 2, 11, 13, 0, tzinfo=UTC),
                        "status": "critical",
                    },
                    {
                        "territory_id": "3121605",
                        "territory_name": "Diamantina",
                        "territory_level": "municipality",
                        "domain": "trabalho",
                        "indicator_code": "MTE_NOVO_CAGED_SALDO_TOTAL",
                        "score": 60.0,
                        "updated_at": datetime(2026, 2, 11, 13, 0, tzinfo=UTC),
                        "status": "attention",
                    },
                    {
                        "territory_id": "3106200",
                        "territory_name": "Belo Horizonte",
                        "territory_level": "municipality",
                        "domain": "saude",
                        "indicator_code": "DATASUS_APS_COBERTURA",
                        "score": 78.0,
                        "updated_at": datetime(2026, 2, 11, 12, 0, tzinfo=UTC),
                        "status": "critical",
                    },
                    {
                        "territory_id": "3106200",
                        "territory_name": "Belo Horizonte",
                        "territory_level": "municipality",
                        "domain": "trabalho",
                        "indicator_code": "MTE_NOVO_CAGED_SALDO_TOTAL",
                        "score": 58.0,
                        "updated_at": datetime(2026, 2, 11, 12, 0, tzinfo=UTC),
                        "status": "attention",
                    },
                    {
                        "territory_id": "3120904",
                        "territory_name": "Curvelo",
                        "territory_level": "municipality",
                        "domain": "saude",
                        "indicator_code": "DATASUS_APS_COBERTURA",
                        "score": 50.0,
                        "updated_at": datetime(2026, 2, 11, 11, 0, tzinfo=UTC),
                        "status": "attention",
                    },
                    {
                        "territory_id": "3120904",
                        "territory_name": "Curvelo",
                        "territory_level": "municipality",
                        "domain": "trabalho",
                        "indicator_code": "MTE_NOVO_CAGED_SALDO_TOTAL",
                        "score": 40.0,
                        "updated_at": datetime(2026, 2, 11, 11, 0, tzinfo=UTC),
                        "status": "stable",
                    },
                ]
            )

        raise AssertionError(f"Unexpected SQL in territory peers test: {sql}")


class _ElectorateSummarySession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _ScalarResult | _RowsResult:
        sql = str(_args[0]).lower() if _args else ""

        if "select max(fe.reference_year)" in sql:
            return _ScalarResult(2024)
        if "from silver.fact_election_result fr" in sql and "count(*)" in sql:
            return _ScalarResult(1)
        if "select coalesce(sum(fe.voters), 0)::bigint as total_voters" in sql:
            return _ScalarResult(12500)
        if "group by label" in sql and "fe.sex" in sql:
            return _RowsResult([{"label": "MASCULINO", "voters": 6000}, {"label": "FEMININO", "voters": 6500}])
        if "group by label" in sql and "fe.age_range" in sql:
            return _RowsResult([{"label": "25-34", "voters": 4500}, {"label": "35-44", "voters": 4000}])
        if "group by label" in sql and "fe.education" in sql:
            return _RowsResult([{"label": "ENSINO MEDIO", "voters": 7000}, {"label": "SUPERIOR", "voters": 2000}])
        if "group by fr.metric" in sql:
            return _RowsResult(
                [
                    {"metric": "turnout", "total_value": 8200.0},
                    {"metric": "abstention", "total_value": 1800.0},
                    {"metric": "votes_total", "total_value": 8000.0},
                    {"metric": "votes_blank", "total_value": 200.0},
                    {"metric": "votes_null", "total_value": 300.0},
                ]
            )

        raise AssertionError(f"Unexpected SQL in electorate summary test: {sql}")


class _ElectorateMapSession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _ScalarResult | _RowsResult:
        sql = str(_args[0]).lower() if _args else ""

        if "select max(fe.reference_year)" in sql:
            return _ScalarResult(2024)
        if "sum(fe.voters)::double precision as value" in sql:
            return _RowsResult(
                [
                    {
                        "territory_id": "3121605",
                        "territory_name": "Diamantina",
                        "territory_level": "municipality",
                        "value": 12500.0,
                        "geometry": {"type": "Polygon", "coordinates": []},
                    }
                ]
            )
        if "select max(fr.election_year)" in sql:
            return _ScalarResult(2024)
        if "with grouped as" in sql and "from silver.fact_election_result fr" in sql:
            return _RowsResult(
                [
                    {
                        "territory_id": "3121605",
                        "territory_name": "Diamantina",
                        "territory_level": "municipality",
                        "value": 18.0,
                        "geometry": {"type": "Polygon", "coordinates": []},
                    }
                ]
            )

        raise AssertionError(f"Unexpected SQL in electorate map test: {sql}")


class _ElectorateSummaryOutlierYearSession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _ScalarResult:
        sql = str(_args[0]).lower() if _args else ""
        if "select max(fe.reference_year)" in sql:
            return _ScalarResult(9999)
        raise AssertionError(f"Unexpected SQL in electorate outlier year test: {sql}")


class _ElectorateOutlierFallbackSession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _ScalarResult | _RowsResult:
        sql = str(_args[0]).lower() if _args else ""

        if "from silver.fact_electorate fe" in sql and "count(*)" in sql and "fe.reference_year = :year" in sql:
            return _ScalarResult(0)
        if "select max(fe.reference_year)" in sql and "fe.reference_year > :max_allowed_year" in sql:
            return _ScalarResult(9999)
        if "from silver.fact_electorate fe" in sql and "count(*)" in sql and "fe.reference_year = :storage_year" in sql:
            return _ScalarResult(5)
        if "select coalesce(sum(fe.voters), 0)::bigint as total_voters" in sql:
            return _ScalarResult(12500)
        if "group by label" in sql and "fe.sex" in sql:
            return _RowsResult([{"label": "MASCULINO", "voters": 6000}, {"label": "FEMININO", "voters": 6500}])
        if "group by label" in sql and "fe.age_range" in sql:
            return _RowsResult([{"label": "25-34", "voters": 4500}, {"label": "35-44", "voters": 4000}])
        if "group by label" in sql and "fe.education" in sql:
            return _RowsResult([{"label": "ENSINO MEDIO", "voters": 7000}, {"label": "SUPERIOR", "voters": 2000}])
        if "from silver.fact_election_result fr" in sql and "count(*)" in sql:
            return _ScalarResult(1)
        if "group by fr.metric" in sql:
            return _RowsResult(
                [
                    {"metric": "turnout", "total_value": 8200.0},
                    {"metric": "abstention", "total_value": 1800.0},
                    {"metric": "votes_total", "total_value": 8000.0},
                    {"metric": "votes_blank", "total_value": 200.0},
                    {"metric": "votes_null", "total_value": 300.0},
                ]
            )
        if "sum(fe.voters)::double precision as value" in sql:
            return _RowsResult(
                [
                    {
                        "territory_id": "3121605",
                        "territory_name": "Diamantina",
                        "territory_level": "municipality",
                        "value": 12500.0,
                        "geometry": None,
                    }
                ]
            )

        raise AssertionError(f"Unexpected SQL in electorate outlier fallback test: {sql}")


def _qg_db() -> Generator[_QgSession, None, None]:
    yield _QgSession()


def test_kpis_overview_returns_items_and_metadata() -> None:
    app.dependency_overrides[get_db] = _qg_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/kpis/overview?period=2025&level=municipio&limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "2025"
    assert payload["metadata"]["source_name"] == "silver.fact_indicator"
    assert len(payload["items"]) == 2
    assert payload["items"][0]["territory_level"] == "municipio"
    assert payload["items"][0]["domain"] == "saude"
    app.dependency_overrides.clear()


def test_priority_list_accepts_level_alias_and_builds_rationale() -> None:
    session = _QgSession()

    def _db() -> Generator[_QgSession, None, None]:
        yield session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/priority/list?period=2025&level=municipio&limit=2")

    assert response.status_code == 200
    assert session.last_params is not None
    assert session.last_params["level"] == "municipality"
    payload = response.json()
    assert payload["level"] == "municipio"
    assert payload["items"][0]["status"] == "critical"
    assert payload["items"][0]["territory_level"] == "municipio"
    assert len(payload["items"][0]["rationale"]) >= 3
    app.dependency_overrides.clear()


def test_priority_summary_returns_status_and_domain_counts() -> None:
    app.dependency_overrides[get_db] = _qg_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/priority/summary?period=2025&level=municipality")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_items"] == 3
    assert payload["by_status"]["critical"] == 1
    assert payload["by_status"]["attention"] == 1
    assert payload["by_status"]["stable"] == 1
    assert payload["by_domain"]["saude"] == 1
    assert payload["top_territories"] == ["Diamantina"]
    app.dependency_overrides.clear()


def test_insights_highlights_filters_by_severity() -> None:
    app.dependency_overrides[get_db] = _qg_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/insights/highlights?severity=critical&limit=10")

    assert response.status_code == 200
    payload = response.json()
    assert payload["severity"] == "critical"
    assert len(payload["items"]) == 1
    assert payload["items"][0]["severity"] == "critical"
    assert payload["items"][0]["robustness"] == "high"
    app.dependency_overrides.clear()


def test_insights_highlights_rejects_invalid_severity() -> None:
    app.dependency_overrides[get_db] = _qg_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/insights/highlights?severity=urgent")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    app.dependency_overrides.clear()


def test_scenarios_simulate_returns_estimated_impact() -> None:
    app.dependency_overrides[get_db] = _qg_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/v1/scenarios/simulate",
        json={
            "territory_id": "3121605",
            "period": "2025",
            "level": "municipio",
            "indicator_code": "DATASUS_APS_COBERTURA",
            "adjustment_percent": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["territory_name"] == "Diamantina"
    assert payload["status_before"] in {"critical", "attention", "stable"}
    assert payload["status_after"] in {"critical", "attention", "stable"}
    assert payload["peer_count"] >= 1
    assert payload["base_rank"] >= 1
    assert payload["simulated_rank"] >= 1
    assert isinstance(payload["rank_delta"], int)
    assert payload["simulated_value"] > payload["base_value"]
    assert payload["impact"] in {"worsened", "improved", "unchanged"}
    assert len(payload["explanation"]) >= 2
    app.dependency_overrides.clear()


def test_scenarios_simulate_returns_not_found_for_unknown_indicator() -> None:
    app.dependency_overrides[get_db] = _qg_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/v1/scenarios/simulate",
        json={
            "territory_id": "3121605",
            "period": "2025",
            "level": "municipio",
            "indicator_code": "INDICADOR_INEXISTENTE",
            "adjustment_percent": 15,
        },
    )

    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_briefs_generate_returns_summary_and_evidences() -> None:
    app.dependency_overrides[get_db] = _qg_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/v1/briefs",
        json={
            "period": "2025",
            "level": "municipio",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"].startswith("Brief Executivo")
    assert payload["level"] == "municipio"
    assert len(payload["summary_lines"]) >= 2
    assert len(payload["recommended_actions"]) >= 1
    assert len(payload["evidences"]) >= 1
    assert payload["evidences"][0]["territory_name"] == "Diamantina"
    app.dependency_overrides.clear()


def test_briefs_generate_returns_not_found_for_unknown_territory() -> None:
    app.dependency_overrides[get_db] = _qg_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/v1/briefs",
        json={
            "period": "2025",
            "level": "municipio",
            "territory_id": "9999999",
            "limit": 5,
        },
    )

    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_territory_profile_returns_grouped_domains() -> None:
    def _db() -> Generator[_TerritoryProfileSession, None, None]:
        yield _TerritoryProfileSession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/territory/3121605/profile?period=2025")

    assert response.status_code == 200
    payload = response.json()
    assert payload["territory_name"] == "Diamantina"
    assert payload["territory_level"] == "municipio"
    assert payload["overall_score"] == 74.5
    assert payload["overall_status"] == "attention"
    assert payload["overall_trend"] == "up"
    assert len(payload["domains"]) == 2
    assert payload["domains"][0]["status"] in {"critical", "attention", "stable"}
    assert len(payload["highlights"]) >= 1
    app.dependency_overrides.clear()


def test_territory_compare_returns_delta_items() -> None:
    def _db() -> Generator[_TerritoryCompareSession, None, None]:
        yield _TerritoryCompareSession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/territory/3121605/compare?with_id=3106200&period=2025")

    assert response.status_code == 200
    payload = response.json()
    assert payload["territory_name"] == "Diamantina"
    assert payload["compare_with_name"] == "Belo Horizonte"
    assert len(payload["items"]) == 2
    assert payload["items"][0]["indicator_code"] in {
        "DATASUS_APS_COBERTURA",
        "MTE_NOVO_CAGED_SALDO_TOTAL",
    }
    app.dependency_overrides.clear()


def test_territory_peers_returns_ranked_similarity() -> None:
    def _db() -> Generator[_TerritoryPeersSession, None, None]:
        yield _TerritoryPeersSession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/territory/3121605/peers?period=2025&limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["territory_name"] == "Diamantina"
    assert len(payload["items"]) == 2
    assert payload["items"][0]["territory_name"] == "Belo Horizonte"
    assert payload["items"][0]["shared_indicators"] == 2
    assert payload["items"][0]["similarity_score"] == 98.0
    assert payload["items"][0]["status"] == "attention"
    app.dependency_overrides.clear()


def test_electorate_summary_returns_breakdowns_and_rates() -> None:
    def _db() -> Generator[_ElectorateSummarySession, None, None]:
        yield _ElectorateSummarySession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/electorate/summary?level=municipio")

    assert response.status_code == 200
    payload = response.json()
    assert payload["level"] == "municipio"
    assert payload["year"] == 2024
    assert payload["total_voters"] == 12500
    assert payload["turnout_rate"] == 82.0
    assert payload["abstention_rate"] == 18.0
    assert len(payload["by_sex"]) == 2
    app.dependency_overrides.clear()


def test_electorate_summary_ignores_outlier_year_and_returns_empty() -> None:
    def _db() -> Generator[_ElectorateSummaryOutlierYearSession, None, None]:
        yield _ElectorateSummaryOutlierYearSession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/electorate/summary?level=municipio")

    assert response.status_code == 200
    payload = response.json()
    assert payload["year"] is None
    assert payload["total_voters"] == 0
    assert payload["by_sex"] == []
    app.dependency_overrides.clear()


def test_electorate_map_returns_values_for_voters_metric() -> None:
    def _db() -> Generator[_ElectorateMapSession, None, None]:
        yield _ElectorateMapSession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/electorate/map?metric=voters&level=municipio")

    assert response.status_code == 200
    payload = response.json()
    assert payload["metric"] == "voters"
    assert payload["year"] == 2024
    assert len(payload["items"]) == 1
    assert payload["items"][0]["territory_name"] == "Diamantina"
    app.dependency_overrides.clear()


def test_electorate_map_returns_values_for_rate_metric() -> None:
    def _db() -> Generator[_ElectorateMapSession, None, None]:
        yield _ElectorateMapSession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/electorate/map?metric=abstention_rate&level=municipio")

    assert response.status_code == 200
    payload = response.json()
    assert payload["metric"] == "abstention_rate"
    assert payload["year"] == 2024
    assert payload["metadata"]["unit"] == "%"
    assert len(payload["items"]) == 1
    app.dependency_overrides.clear()


def test_electorate_summary_uses_outlier_storage_year_when_requested_year_is_valid() -> None:
    def _db() -> Generator[_ElectorateOutlierFallbackSession, None, None]:
        yield _ElectorateOutlierFallbackSession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/electorate/summary?level=municipio&year=2024")

    assert response.status_code == 200
    payload = response.json()
    assert payload["year"] == 2024
    assert payload["total_voters"] == 12500
    assert payload["metadata"]["notes"].startswith("electorate_outlier_year_fallback")
    assert len(payload["by_sex"]) == 2
    app.dependency_overrides.clear()


def test_electorate_map_uses_outlier_storage_year_when_requested_year_is_valid() -> None:
    def _db() -> Generator[_ElectorateOutlierFallbackSession, None, None]:
        yield _ElectorateOutlierFallbackSession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/electorate/map?metric=voters&level=municipio&year=2024")

    assert response.status_code == 200
    payload = response.json()
    assert payload["year"] == 2024
    assert payload["metric"] == "voters"
    assert len(payload["items"]) == 1
    assert payload["metadata"]["notes"].startswith("electorate_outlier_year_fallback")
    app.dependency_overrides.clear()
