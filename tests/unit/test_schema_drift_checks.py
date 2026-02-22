from __future__ import annotations

from typing import Any

from pipelines.common.quality import check_source_schema_drift
from pipelines.common.quality_thresholds import QualityThresholds


class _ScalarResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one(self) -> Any:
        return self._value


class _MappingsResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> "_MappingsResult":
        return self

    def all(self) -> list[dict[str, Any]]:
        return self._rows


class _SchemaDriftSession:
    def __init__(
        self,
        *,
        contracts: list[dict[str, Any]],
        existing_tables: set[str],
        columns_by_table: dict[tuple[str, str], dict[str, str]],
    ) -> None:
        self._contracts = contracts
        self._existing_tables = existing_tables
        self._columns_by_table = columns_by_table

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> Any:
        sql = str(statement).lower()
        params = params or {}
        if "from ops.v_source_schema_contracts_active" in sql:
            return _MappingsResult(self._contracts)
        if "select to_regclass" in sql:
            table_name = str(params["target_table"])
            return _ScalarResult(table_name in self._existing_tables)
        if "from pg_catalog.pg_attribute" in sql:
            schema_name = str(params["schema_name"])
            table_name = str(params["table_name"])
            columns = self._columns_by_table.get((schema_name, table_name), {})
            return _MappingsResult(
                [
                    {"column_name": column_name, "normalized_type": column_type}
                    for column_name, column_type in columns.items()
                ]
            )
        raise AssertionError(f"Unexpected query: {sql}")


def _thresholds() -> QualityThresholds:
    return QualityThresholds(
        defaults={},
        by_table={
            "schema_drift": {
                "max_missing_required_columns": 0,
                "max_type_mismatch_columns": 0,
                "max_connectors_with_drift": 0,
            }
        },
    )


def test_check_source_schema_drift_passes_when_contract_matches_table() -> None:
    session = _SchemaDriftSession(
        contracts=[
            {
                "connector_name": "sidra_indicators_fetch",
                "target_table": "silver.fact_indicator",
                "required_columns": ["territory_id", "value"],
                "column_types": {"territory_id": "uuid", "value": "numeric"},
            }
        ],
        existing_tables={"silver.fact_indicator"},
        columns_by_table={
            ("silver", "fact_indicator"): {
                "territory_id": "uuid",
                "value": "numeric",
                "source": "text",
            }
        },
    )

    results = check_source_schema_drift(session, _thresholds())
    by_name = {result.name: result for result in results}
    assert by_name["schema_drift_table_exists_sidra_indicators_fetch"].status == "pass"
    assert by_name["schema_drift_missing_required_columns_sidra_indicators_fetch"].status == "pass"
    assert by_name["schema_drift_type_mismatch_columns_sidra_indicators_fetch"].status == "pass"
    assert by_name["schema_drift_connectors_with_issues"].status == "pass"
    assert by_name["schema_drift_connectors_with_issues"].observed_value == 0


def test_check_source_schema_drift_fails_when_required_or_types_drift() -> None:
    session = _SchemaDriftSession(
        contracts=[
            {
                "connector_name": "urban_pois_fetch",
                "target_table": "map.urban_poi",
                "required_columns": ["source", "geom", "name"],
                "column_types": {
                    "source": "text",
                    "geom": "geometry(point,4326)",
                    "name": "text",
                },
            }
        ],
        existing_tables={"map.urban_poi"},
        columns_by_table={
            ("map", "urban_poi"): {
                "source": "integer",
                "geom": "geometry(linestring,4326)",
            }
        },
    )

    results = check_source_schema_drift(session, _thresholds())
    by_name = {result.name: result for result in results}
    assert by_name["schema_drift_table_exists_urban_pois_fetch"].status == "pass"
    assert by_name["schema_drift_missing_required_columns_urban_pois_fetch"].status == "fail"
    assert by_name["schema_drift_missing_required_columns_urban_pois_fetch"].observed_value == 1
    assert by_name["schema_drift_type_mismatch_columns_urban_pois_fetch"].status == "fail"
    assert by_name["schema_drift_type_mismatch_columns_urban_pois_fetch"].observed_value == 2
    assert by_name["schema_drift_connectors_with_issues"].status == "fail"
    assert by_name["schema_drift_connectors_with_issues"].observed_value == 1
