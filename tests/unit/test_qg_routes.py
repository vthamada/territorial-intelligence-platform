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

    def one(self) -> dict[str, Any]:
        if not self._rows:
            raise AssertionError("Expected one row, found none")
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
                        "score_version": "v1.0.0",
                        "config_version": "1.0.0",
                        "scoring_method": "rank_abs_value_v1",
                        "critical_threshold": 80.0,
                        "attention_threshold": 50.0,
                        "domain_weight": 1.0,
                        "indicator_weight": 1.0,
                        "weighted_magnitude": 45.0,
                        "driver_rank": 1,
                        "driver_total": 3,
                        "coverage_covered_territories": 1,
                        "coverage_total_territories": 1,
                        "coverage_pct": 100.0,
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
                        "score_version": "v1.0.0",
                        "config_version": "1.0.0",
                        "scoring_method": "rank_abs_value_v1",
                        "critical_threshold": 80.0,
                        "attention_threshold": 50.0,
                        "domain_weight": 1.0,
                        "indicator_weight": 1.0,
                        "weighted_magnitude": 8.2,
                        "driver_rank": 2,
                        "driver_total": 3,
                        "coverage_covered_territories": 1,
                        "coverage_total_territories": 1,
                        "coverage_pct": 100.0,
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
                        "score_version": "v1.0.0",
                        "config_version": "1.0.0",
                        "scoring_method": "rank_abs_value_v1",
                        "critical_threshold": 80.0,
                        "attention_threshold": 50.0,
                        "domain_weight": 1.0,
                        "indicator_weight": 1.0,
                        "weighted_magnitude": 120.0,
                        "driver_rank": 3,
                        "driver_total": 3,
                        "coverage_covered_territories": 1,
                        "coverage_total_territories": 1,
                        "coverage_pct": 100.0,
                        "score": 35.0,
                        "status": "stable",
                    },
                ]
            )

        # _fetch_previous_values: return empty so trend defaults to stable
        if "fi.reference_period = cast(:period as text)" in sql and "fi.indicator_code" in sql and "fi.value" in sql:
            return _RowsResult([])

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
        if "group by fr.office" in sql and "sum(case when fr.metric = 'turnout'" in sql:
            return _RowsResult([{"office": "PREFEITO", "election_round": 1, "turnout": 8200.0}])
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
        if "group by fr.office" in sql and "sum(case when fr.metric = 'turnout'" in sql:
            return _RowsResult([{"office": "PREFEITO", "election_round": 1, "turnout": 8200.0}])
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
        if "group by fr.office" in sql and "sum(case when fr.metric = 'turnout'" in sql:
            return _RowsResult([{"office": "PREFEITO", "election_round": 1, "turnout": 8200.0}])
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


class _ElectorateHistorySession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _RowsResult:
        sql = str(_args[0]).lower() if _args else ""

        if "sum(fe.voters)::bigint as total_voters" in sql and "group by fe.reference_year" in sql:
            return _RowsResult(
                [
                    {"year": 2024, "total_voters": 12500},
                    {"year": 2022, "total_voters": 11900},
                ]
            )
        if "row_number()" in sql and "group by fr.election_year, fr.metric" in sql:
            return _RowsResult(
                [
                    {"year": 2024, "metric": "turnout", "total_value": 8200.0},
                    {"year": 2024, "metric": "abstention", "total_value": 1800.0},
                    {"year": 2024, "metric": "votes_total", "total_value": 8000.0},
                    {"year": 2024, "metric": "votes_blank", "total_value": 200.0},
                    {"year": 2024, "metric": "votes_null", "total_value": 300.0},
                    {"year": 2022, "metric": "turnout", "total_value": 7600.0},
                    {"year": 2022, "metric": "abstention", "total_value": 1700.0},
                    {"year": 2022, "metric": "votes_total", "total_value": 7400.0},
                    {"year": 2022, "metric": "votes_blank", "total_value": 150.0},
                    {"year": 2022, "metric": "votes_null", "total_value": 250.0},
                ]
            )

        raise AssertionError(f"Unexpected SQL in electorate history test: {sql}")


class _ElectoratePollingPlacesSession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _ScalarResult | _RowsResult:
        sql = str(_args[0]).lower() if _args else ""

        if "select max(fe.reference_year)" in sql:
            return _ScalarResult(2024)
        if (
            "polling_place_registry as" in sql
            and "municipality_total as" in sql
            and "from silver.fact_electorate fe" in sql
            and "from silver.fact_election_result fr" not in sql
        ):
            return _RowsResult(
                [
                    {
                        "territory_id": "pp-1",
                        "territory_name": "E. E. PROF.ª ISABEL MOTA",
                        "territory_level": "polling_place",
                        "polling_place_name": "E. E. PROF.ª ISABEL MOTA",
                        "polling_place_code": "102",
                        "district_name": "Rio Grande",
                        "zone_codes": ["101"],
                        "section_count": 8,
                        "sections": ["58", "59", "60"],
                        "voters_total": 2453.0,
                        "share_percent": 6.3,
                    },
                    {
                        "territory_id": "pp-2",
                        "territory_name": "UEMG (ANTIGA FEVALE)",
                        "territory_level": "polling_place",
                        "polling_place_name": "UEMG (ANTIGA FEVALE)",
                        "polling_place_code": "101",
                        "district_name": "Centro",
                        "zone_codes": ["101"],
                        "section_count": 13,
                        "sections": ["41", "177", "212"],
                        "voters_total": 2327.0,
                        "share_percent": 6.1,
                    },
                ]
            )
        if "select max(fr.election_year)" in sql:
            return _ScalarResult(2024)
        if "group by fr.office" in sql and "sum(case when fr.metric = 'turnout'" in sql:
            return _RowsResult([{"office": "PREFEITO", "election_round": 1, "turnout": 8200.0}])
        if "polling_place_registry as" in sql and "electorate_base as" in sql and "from silver.fact_election_result fr" in sql:
            return _RowsResult(
                [
                    {
                        "territory_id": "pp-1",
                        "territory_name": "UEMG (ANTIGA FEVALE)",
                        "territory_level": "polling_place",
                        "polling_place_name": "UEMG (ANTIGA FEVALE)",
                        "polling_place_code": "101",
                        "district_name": "Centro",
                        "zone_codes": ["101"],
                        "section_count": 13,
                        "sections": ["41", "177", "212"],
                        "voters_total": 2327.0,
                        "share_percent": 6.1,
                        "turnout": 1800.0,
                        "abstention": 400.0,
                        "votes_blank": 50.0,
                        "votes_null": 30.0,
                        "votes_total": 1880.0,
                    },
                    {
                        "territory_id": "pp-2",
                        "territory_name": "E. E. PROF.ª ISABEL MOTA",
                        "territory_level": "polling_place",
                        "polling_place_name": "E. E. PROF.ª ISABEL MOTA",
                        "polling_place_code": "102",
                        "district_name": "Rio Grande",
                        "zone_codes": ["101"],
                        "section_count": 8,
                        "sections": ["58", "59", "60"],
                        "voters_total": 2453.0,
                        "share_percent": 6.3,
                        "turnout": 1700.0,
                        "abstention": 500.0,
                        "votes_blank": 30.0,
                        "votes_null": 20.0,
                        "votes_total": 1750.0,
                    },
                ]
            )

        raise AssertionError(f"Unexpected SQL in electorate polling places test: {sql}")


class _ElectorateElectionContextSession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _ScalarResult | _RowsResult:
        sql = str(_args[0]).lower() if _args else ""

        if "to_regclass('silver.fact_candidate_vote')" in sql:
            return _RowsResult(
                [{"fact_candidate_vote": True, "dim_candidate": True, "dim_election": True}]
            )
        if "from silver.fact_candidate_vote fcv" in sql and "count(*)" in sql:
            return _ScalarResult(12)
        if "from silver.fact_candidate_vote fcv" in sql and "group by de.office, de.election_round, de.election_type" in sql:
            return _RowsResult(
                [{"office": "PREFEITO", "election_round": 1, "election_type": "municipal", "total_votes": 8200.0}]
            )
        if "with grouped as" in sql and "cross join total t" in sql and "dc.candidate_id::text as candidate_id" in sql:
            return _RowsResult(
                [
                    {
                        "candidate_id": "cand-13",
                        "candidate_number": "13",
                        "candidate_name": "Candidato A",
                        "ballot_name": "Candidato A",
                        "party_abbr": "PT",
                        "party_number": "13",
                        "party_name": "Partido dos Testes",
                        "votes": 4300.0,
                        "total_votes": 8200.0,
                        "share_percent": 52.439024,
                    },
                    {
                        "candidate_id": "cand-45",
                        "candidate_number": "45",
                        "candidate_name": "Candidato B",
                        "ballot_name": "Candidato B",
                        "party_abbr": "PSDB",
                        "party_number": "45",
                        "party_name": "Partido B",
                        "votes": 3900.0,
                        "total_votes": 8200.0,
                        "share_percent": 47.560976,
                    },
                ]
            )

        raise AssertionError(f"Unexpected SQL in electorate election context test: {sql}")


class _ElectorateElectionContextFallbackSession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _ScalarResult | _RowsResult:
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]
        sql = str(_args[0]).lower() if _args else ""

        if "to_regclass('silver.fact_candidate_vote')" in sql:
            return _RowsResult(
                [{"fact_candidate_vote": True, "dim_candidate": True, "dim_election": True}]
            )
        if "from silver.fact_candidate_vote fcv" in sql and "count(*)" in sql:
            level = str((params or {}).get("level"))
            if level == "municipality":
                return _ScalarResult(0)
            if level == "electoral_section":
                return _ScalarResult(0)
            return _ScalarResult(12)
        if "from silver.fact_candidate_vote fcv" in sql and "group by de.office, de.election_round, de.election_type" in sql:
            return _RowsResult(
                [{"office": "PREFEITO", "election_round": 1, "election_type": "municipal", "total_votes": 8200.0}]
            )
        if "with grouped as" in sql and "cross join total t" in sql and "dc.candidate_id::text as candidate_id" in sql:
            return _RowsResult(
                [
                    {
                        "candidate_id": "cand-13",
                        "candidate_number": "13",
                        "candidate_name": "Candidato A",
                        "ballot_name": "Candidato A",
                        "party_abbr": "PT",
                        "party_number": "13",
                        "party_name": "Partido dos Testes",
                        "votes": 4300.0,
                        "total_votes": 8200.0,
                        "share_percent": 52.439024,
                    }
                ]
            )

        raise AssertionError(f"Unexpected SQL in electorate election context fallback test: {sql}")


class _ElectorateElectionContextSectionPreferredSession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _ScalarResult | _RowsResult:
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]
        sql = str(_args[0]).lower() if _args else ""

        if "to_regclass('silver.fact_candidate_vote')" in sql:
            return _RowsResult(
                [{"fact_candidate_vote": True, "dim_candidate": True, "dim_election": True}]
            )
        if "from silver.fact_candidate_vote fcv" in sql and "count(*)" in sql:
            level = str((params or {}).get("level"))
            if level == "municipality":
                return _ScalarResult(0)
            if level == "electoral_section":
                return _ScalarResult(48)
            if level == "electoral_zone":
                return _ScalarResult(24)
        if "from silver.fact_candidate_vote fcv" in sql and "group by de.office, de.election_round, de.election_type" in sql:
            return _RowsResult(
                [{"office": "PREFEITO", "election_round": 1, "election_type": "municipal", "total_votes": 8200.0}]
            )
        if "with grouped as" in sql and "cross join total t" in sql and "dc.candidate_id::text as candidate_id" in sql:
            return _RowsResult(
                [
                    {
                        "candidate_id": "cand-13",
                        "candidate_number": "13",
                        "candidate_name": "Candidato A",
                        "ballot_name": "Candidato A",
                        "party_abbr": "PT",
                        "party_number": "13",
                        "party_name": "Partido dos Testes",
                        "votes": 4300.0,
                        "total_votes": 8200.0,
                        "share_percent": 52.439024,
                    }
                ]
            )

        raise AssertionError(f"Unexpected SQL in electorate election context section preferred test: {sql}")


class _ElectorateCandidateTerritoriesSession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _ScalarResult | _RowsResult:
        sql = str(_args[0]).lower() if _args else ""

        if "to_regclass('silver.fact_candidate_vote')" in sql:
            return _RowsResult(
                [{"fact_candidate_vote": True, "dim_candidate": True, "dim_election": True}]
            )
        if "from silver.fact_candidate_vote fcv" in sql and "count(*)" in sql:
            return _ScalarResult(24)
        if "from silver.fact_candidate_vote fcv" in sql and "group by de.office, de.election_round, de.election_type" in sql:
            return _RowsResult(
                [{"office": "PREFEITO", "election_round": 1, "election_type": "municipal", "total_votes": 8200.0}]
            )
        if "polling_place_registry as" in sql and "md5(ppr.pp_key)::text as territory_id" in sql:
            return _RowsResult(
                [
                    {
                        "territory_id": "pp-1",
                        "territory_name": "UEMG (ANTIGA FEVALE)",
                        "territory_level": "polling_place",
                        "polling_place_name": "UEMG (ANTIGA FEVALE)",
                        "polling_place_code": "101",
                        "zone_codes": ["101"],
                        "section_count": 3,
                        "sections": ["41", "177", "212"],
                        "candidate_id": "cand-13",
                        "candidate_number": "13",
                        "candidate_name": "Candidato A",
                        "ballot_name": "Candidato A",
                        "party_abbr": "PT",
                        "party_number": "13",
                        "party_name": "Partido dos Testes",
                        "votes": 1200.0,
                        "district_name": "Centro",
                        "share_percent": 27.906977,
                    }
                ]
            )
        if "polling_place_registry as" in sql and "dt.territory_id::text as territory_id" in sql and "ppr.polling_place_name as polling_place_name" in sql:
            return _RowsResult(
                [
                    {
                        "territory_id": "sec-41",
                        "territory_name": "Seção eleitoral 41 (zona 101) - Diamantina",
                        "territory_level": "electoral_section",
                        "polling_place_name": "UEMG (ANTIGA FEVALE)",
                        "polling_place_code": "101",
                        "zone_codes": ["101"],
                        "section_count": 1,
                        "sections": ["41"],
                        "candidate_id": "cand-13",
                        "candidate_number": "13",
                        "candidate_name": "Candidato A",
                        "ballot_name": "Candidato A",
                        "party_abbr": "PT",
                        "party_number": "13",
                        "party_name": "Partido dos Testes",
                        "votes": 480.0,
                        "district_name": "Centro",
                        "share_percent": 11.707317,
                    }
                ]
            )

        raise AssertionError(f"Unexpected SQL in electorate candidate territories test: {sql}")


class _ElectorateCandidateTerritoriesFallbackSession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _ScalarResult | _RowsResult:
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]
        sql = str(_args[0]).lower() if _args else ""

        if "to_regclass('silver.fact_candidate_vote')" in sql:
            return _RowsResult(
                [{"fact_candidate_vote": True, "dim_candidate": True, "dim_election": True}]
            )
        if "from silver.fact_candidate_vote fcv" in sql and "count(*)" in sql:
            level = str((params or {}).get("level"))
            return _ScalarResult(0 if level == "electoral_section" else 24)

        raise AssertionError(f"Unexpected SQL in electorate candidate territories fallback test: {sql}")


class _MobilityAccessSession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _RowsResult:
        sql = str(_args[0]).lower() if _args else ""

        if "select max(reference_period) as reference_period" in sql and "from gold.mart_mobility_access" in sql:
            return _RowsResult([{"reference_period": "2025"}])

        if "from gold.mart_mobility_access" in sql and "mobility_access_deficit_score" in sql:
            return _RowsResult(
                [
                    {
                        "reference_period": "2025",
                        "territory_id": "d-01",
                        "territory_name": "Sede",
                        "territory_level": "district",
                        "municipality_ibge_code": "3121605",
                        "road_segments_count": 12,
                        "road_length_km": 8.4,
                        "transport_stops_count": 5,
                        "mobility_pois_count": 2,
                        "fleet_total_effective": 610.0,
                        "population_effective": 7800.0,
                        "vehicles_per_1k_pop": 78.2,
                        "transport_stops_per_10k_pop": 6.41,
                        "road_km_per_10k_pop": 10.76,
                        "mobility_pois_per_10k_pop": 2.56,
                        "mobility_access_score": 22.0,
                        "mobility_access_deficit_score": 78.0,
                        "priority_status": "critical",
                        "uses_proxy_allocation": True,
                        "allocation_method": "district_allocation_by_road_length_share",
                        "refreshed_at_utc": datetime(2026, 2, 21, 12, 0, tzinfo=UTC),
                    },
                    {
                        "reference_period": "2025",
                        "territory_id": "d-02",
                        "territory_name": "Guinda",
                        "territory_level": "district",
                        "municipality_ibge_code": "3121605",
                        "road_segments_count": 8,
                        "road_length_km": 4.2,
                        "transport_stops_count": 3,
                        "mobility_pois_count": 1,
                        "fleet_total_effective": 320.0,
                        "population_effective": 4100.0,
                        "vehicles_per_1k_pop": 78.0,
                        "transport_stops_per_10k_pop": 7.31,
                        "road_km_per_10k_pop": 10.24,
                        "mobility_pois_per_10k_pop": 2.43,
                        "mobility_access_score": 40.0,
                        "mobility_access_deficit_score": 60.0,
                        "priority_status": "attention",
                        "uses_proxy_allocation": True,
                        "allocation_method": "district_allocation_by_road_length_share",
                        "refreshed_at_utc": datetime(2026, 2, 21, 12, 0, tzinfo=UTC),
                    },
                ]
            )

        raise AssertionError(f"Unexpected SQL in mobility access test: {sql}")


class _MobilityAccessEmptySession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _RowsResult:
        sql = str(_args[0]).lower() if _args else ""
        if "select max(reference_period) as reference_period" in sql and "from gold.mart_mobility_access" in sql:
            return _RowsResult([{"reference_period": None}])
        if "from gold.mart_mobility_access" in sql and "mobility_access_deficit_score" in sql:
            return _RowsResult([])
        raise AssertionError(f"Unexpected SQL in mobility access empty test: {sql}")


class _EnvironmentRiskSession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _RowsResult:
        sql = str(_args[0]).lower() if _args else ""

        if "select max(reference_period) as reference_period" in sql and "from gold.mart_environment_risk" in sql:
            return _RowsResult([{"reference_period": "2025"}])

        if "from gold.mart_environment_risk" in sql and "environment_risk_score" in sql:
            return _RowsResult(
                [
                    {
                        "reference_period": "2025",
                        "territory_id": "m-01",
                        "territory_name": "Diamantina",
                        "territory_level": "municipality",
                        "municipality_ibge_code": "3121605",
                        "hazard_score": 78.5,
                        "exposure_score": 66.2,
                        "environment_risk_score": 74.2,
                        "risk_percentile": 100.0,
                        "risk_priority_rank": 1,
                        "priority_status": "critical",
                        "area_km2": 892.0,
                        "road_km": 84.2,
                        "pois_count": 312,
                        "transport_stops_count": 42,
                        "road_density_km_per_km2": 0.09,
                        "pois_per_km2": 0.35,
                        "transport_stops_per_km2": 0.05,
                        "population_effective": 49493.0,
                        "exposed_population_per_km2": 55.49,
                        "uses_proxy_allocation": True,
                        "allocation_method": "municipality_rollup_from_districts",
                        "refreshed_at_utc": datetime(2026, 2, 21, 13, 0, tzinfo=UTC),
                    },
                    {
                        "reference_period": "2025",
                        "territory_id": "d-01",
                        "territory_name": "Sede",
                        "territory_level": "district",
                        "municipality_ibge_code": "3121605",
                        "hazard_score": 78.5,
                        "exposure_score": 58.0,
                        "environment_risk_score": 71.3,
                        "risk_percentile": 87.5,
                        "risk_priority_rank": 2,
                        "priority_status": "attention",
                        "area_km2": 32.1,
                        "road_km": 8.4,
                        "pois_count": 48,
                        "transport_stops_count": 5,
                        "road_density_km_per_km2": 0.26,
                        "pois_per_km2": 1.49,
                        "transport_stops_per_km2": 0.16,
                        "population_effective": 7800.0,
                        "exposed_population_per_km2": 242.99,
                        "uses_proxy_allocation": True,
                        "allocation_method": "spatial_exposure_proxy",
                        "refreshed_at_utc": datetime(2026, 2, 21, 13, 0, tzinfo=UTC),
                    },
                ]
            )

        raise AssertionError(f"Unexpected SQL in environment risk test: {sql}")


class _EnvironmentRiskEmptySession:
    def execute(self, *_args: Any, **_kwargs: Any) -> _RowsResult:
        sql = str(_args[0]).lower() if _args else ""
        if "select max(reference_period) as reference_period" in sql and "from gold.mart_environment_risk" in sql:
            return _RowsResult([{"reference_period": None}])
        if "from gold.mart_environment_risk" in sql and "environment_risk_score" in sql:
            return _RowsResult([])
        raise AssertionError(f"Unexpected SQL in environment risk empty test: {sql}")


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


def test_mobility_access_returns_ranked_items_and_metadata() -> None:
    def _db() -> Generator[_MobilityAccessSession, None, None]:
        yield _MobilityAccessSession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/mobility/access?level=distrito&limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "2025"
    assert payload["level"] == "distrito"
    assert payload["metadata"]["source_name"] == "gold.mart_mobility_access"
    assert payload["metadata"]["notes"] == "mobility_access_mart_v1"
    assert len(payload["items"]) == 2
    assert payload["items"][0]["priority_status"] == "critical"
    assert payload["items"][0]["territory_level"] == "distrito"
    assert payload["items"][0]["uses_proxy_allocation"] is True
    app.dependency_overrides.clear()


def test_mobility_access_returns_empty_shape_when_period_not_found() -> None:
    def _db() -> Generator[_MobilityAccessEmptySession, None, None]:
        yield _MobilityAccessEmptySession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/mobility/access?period=2021")

    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "2021"
    assert payload["metadata"]["notes"] == "no_data_for_selected_filters"
    assert payload["items"] == []
    app.dependency_overrides.clear()


def test_environment_risk_returns_ranked_items_and_metadata() -> None:
    def _db() -> Generator[_EnvironmentRiskSession, None, None]:
        yield _EnvironmentRiskSession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/environment/risk?level=municipio&limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "2025"
    assert payload["level"] == "municipio"
    assert payload["metadata"]["source_name"] == "gold.mart_environment_risk"
    assert payload["metadata"]["notes"] == "environment_risk_mart_v1"
    assert len(payload["items"]) == 2
    assert payload["items"][0]["priority_status"] == "critical"
    assert payload["items"][0]["territory_level"] == "municipio"
    assert payload["items"][0]["risk_priority_rank"] == 1
    app.dependency_overrides.clear()


def test_environment_risk_returns_empty_shape_when_period_not_found() -> None:
    def _db() -> Generator[_EnvironmentRiskEmptySession, None, None]:
        yield _EnvironmentRiskEmptySession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/environment/risk?period=2021")

    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "2021"
    assert payload["metadata"]["notes"] == "no_data_for_selected_filters"
    assert payload["items"] == []
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
    assert len(payload["items"][0]["rationale"]) >= 4
    assert payload["items"][0]["evidence"]["updated_at"] is not None
    assert payload["items"][0]["explainability"]["trail_id"]
    assert payload["items"][0]["explainability"]["coverage"]["coverage_pct"] == 100.0
    app.dependency_overrides.clear()


def test_priority_explainability_alias_returns_auditable_payload() -> None:
    session = _QgSession()

    def _db() -> Generator[_QgSession, None, None]:
        yield session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/priority/explainability?period=2025&level=municipio&limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["level"] == "municipio"
    assert len(payload["items"]) >= 1
    first = payload["items"][0]
    assert isinstance(first["rationale"], list)
    assert len(first["rationale"]) >= 1
    assert first["evidence"]["score_version"] == "v1.0.0"
    assert first["explainability"]["trail_id"]
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
    assert payload["items"][0]["evidence"]["updated_at"] is not None
    assert payload["items"][0]["explainability"]["trail_id"]
    assert payload["items"][0]["deep_link"].startswith("/insights?")
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


def test_electorate_history_returns_historical_series() -> None:
    def _db() -> Generator[_ElectorateHistorySession, None, None]:
        yield _ElectorateHistorySession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/electorate/history?level=municipio&limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["level"] == "municipio"
    assert len(payload["items"]) == 2
    assert payload["items"][0]["year"] == 2024
    assert payload["items"][0]["total_voters"] == 12500
    assert payload["items"][0]["turnout_rate"] == 82.0
    assert payload["items"][1]["abstention_rate"] == 18.27957
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


def test_electorate_polling_places_returns_ranked_voters() -> None:
    def _db() -> Generator[_ElectoratePollingPlacesSession, None, None]:
        yield _ElectoratePollingPlacesSession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/electorate/polling-places?metric=voters&limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["metric"] == "voters"
    assert payload["year"] == 2024
    assert len(payload["items"]) == 2
    assert payload["items"][0]["territory_name"] == "E. E. PROF.\u00aa ISABEL MOTA"
    assert payload["items"][0]["section_count"] == 8
    assert payload["items"][0]["share_percent"] == 6.3
    app.dependency_overrides.clear()


def test_electorate_polling_places_returns_ranked_behavior_metric() -> None:
    def _db() -> Generator[_ElectoratePollingPlacesSession, None, None]:
        yield _ElectoratePollingPlacesSession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/electorate/polling-places?metric=abstention_rate&limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["metric"] == "abstention_rate"
    assert payload["year"] == 2024
    assert len(payload["items"]) == 2
    assert payload["items"][0]["territory_name"] == "E. E. PROF.\u00aa ISABEL MOTA"
    assert payload["items"][0]["value"] == 22.727273
    assert payload["items"][1]["value"] == 18.181818
    app.dependency_overrides.clear()


def test_electorate_election_context_returns_primary_office_and_candidates() -> None:
    def _db() -> Generator[_ElectorateElectionContextSession, None, None]:
        yield _ElectorateElectionContextSession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/electorate/election-context?level=municipio&year=2024&limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["office"] == "PREFEITO"
    assert payload["election_type"] == "municipal"
    assert payload["total_votes"] == 8200
    assert payload["items"][0]["candidate_id"] == "cand-13"
    assert payload["items"][0]["votes"] == 4300
    app.dependency_overrides.clear()


def test_electorate_election_context_falls_back_to_zone_level_for_municipality_view() -> None:
    def _db() -> Generator[_ElectorateElectionContextFallbackSession, None, None]:
        yield _ElectorateElectionContextFallbackSession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/electorate/election-context?level=municipio&year=2024&limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["year"] == 2024
    assert payload["office"] == "PREFEITO"
    assert payload["total_votes"] == 8200
    assert payload["metadata"]["notes"] == "electorate_election_context_v1|source_level=electoral_zone"
    assert payload["items"][0]["candidate_id"] == "cand-13"
    app.dependency_overrides.clear()


def test_electorate_election_context_prefers_section_level_over_zone_for_municipality_view() -> None:
    def _db() -> Generator[_ElectorateElectionContextSectionPreferredSession, None, None]:
        yield _ElectorateElectionContextSectionPreferredSession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/electorate/election-context?level=municipio&year=2024&limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["year"] == 2024
    assert payload["office"] == "PREFEITO"
    assert payload["total_votes"] == 8200
    assert payload["metadata"]["notes"] == "electorate_election_context_v1|source_level=electoral_section"
    assert payload["items"][0]["candidate_id"] == "cand-13"
    app.dependency_overrides.clear()


def test_electorate_candidate_territories_returns_polling_place_ranking() -> None:
    def _db() -> Generator[_ElectorateCandidateTerritoriesSession, None, None]:
        yield _ElectorateCandidateTerritoriesSession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/electorate/candidate-territories?candidate_id=cand-13&year=2024&limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["aggregate_by"] == "polling_place"
    assert payload["office"] == "PREFEITO"
    assert payload["items"][0]["territory_id"] == "pp-1"
    assert payload["items"][0]["votes"] == 1200
    assert payload["items"][0]["sections"] == ["41", "177", "212"]
    app.dependency_overrides.clear()


def test_electorate_candidate_territories_returns_explicit_note_when_only_zone_level_exists() -> None:
    def _db() -> Generator[_ElectorateCandidateTerritoriesFallbackSession, None, None]:
        yield _ElectorateCandidateTerritoriesFallbackSession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/electorate/candidate-territories?candidate_id=cand-13&year=2024&limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["metadata"]["notes"] == "candidate_territories_unavailable|source_level=electoral_zone|requested_aggregate=polling_place"
    app.dependency_overrides.clear()


def test_electorate_candidate_territories_returns_section_breakdown() -> None:
    def _db() -> Generator[_ElectorateCandidateTerritoriesSession, None, None]:
        yield _ElectorateCandidateTerritoriesSession()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/v1/electorate/candidate-territories?candidate_id=cand-13&year=2024&aggregate_by=electoral_section&limit=5"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["aggregate_by"] == "electoral_section"
    assert payload["items"][0]["territory_id"] == "sec-41"
    assert payload["items"][0]["section_count"] == 1
    assert payload["items"][0]["votes"] == 480
    app.dependency_overrides.clear()
