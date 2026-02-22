from __future__ import annotations

from pathlib import Path

import pytest

from pipelines.common.schema_contracts import (
    SKIPPED_CONNECTORS,
    SUPPORTED_CONNECTOR_STATUSES,
    build_schema_contract_records,
    load_connectors,
    load_schema_contract_config,
)


def _eligible_connectors() -> list[str]:
    connectors = load_connectors(Path("configs/connectors.yml"))
    names: list[str] = []
    for connector in connectors:
        connector_name = str(connector.get("connector_name") or "").strip()
        source = str(connector.get("source") or "").strip()
        status = str(connector.get("status") or "").strip().lower()
        if not connector_name:
            continue
        if connector_name in SKIPPED_CONNECTORS:
            continue
        if source.upper() == "INTERNAL":
            continue
        if status not in SUPPORTED_CONNECTOR_STATUSES:
            continue
        names.append(connector_name)
    return sorted(set(names))


def _contract_records_by_connector() -> dict[str, dict]:
    connectors = load_connectors(Path("configs/connectors.yml"))
    config = load_schema_contract_config(Path("configs/schema_contracts.yml"))
    records = build_schema_contract_records(connectors, config=config)
    return {str(item["connector_name"]): item for item in records}


def test_schema_contract_connector_coverage_is_at_least_90_pct() -> None:
    expected = _eligible_connectors()
    records_by_connector = _contract_records_by_connector()
    covered = sorted(set(expected) & set(records_by_connector))
    if not expected:
        pytest.fail("No eligible connectors found for schema contract coverage validation.")
    coverage_pct = (len(covered) / len(expected)) * 100.0
    assert coverage_pct >= 90.0, (
        f"Schema contract connector coverage below threshold: {coverage_pct:.2f}% "
        f"({len(covered)}/{len(expected)})."
    )


@pytest.mark.parametrize("connector_name", _eligible_connectors())
def test_each_eligible_connector_has_contract_record(connector_name: str) -> None:
    records_by_connector = _contract_records_by_connector()
    assert connector_name in records_by_connector, (
        f"Missing schema contract record for connector '{connector_name}'."
    )


@pytest.mark.parametrize("connector_name", _eligible_connectors())
def test_each_eligible_connector_contract_has_required_structure(connector_name: str) -> None:
    records_by_connector = _contract_records_by_connector()
    contract = records_by_connector[connector_name]
    required_columns = contract.get("required_columns")
    column_types = contract.get("column_types")
    assert isinstance(required_columns, list) and len(required_columns) > 0, (
        f"Connector '{connector_name}' has no required_columns in schema contract."
    )
    assert isinstance(column_types, dict) and len(column_types) > 0, (
        f"Connector '{connector_name}' has no column_types in schema contract."
    )
    assert str(contract.get("schema_version") or "").startswith("v"), (
        f"Connector '{connector_name}' has invalid schema_version."
    )
