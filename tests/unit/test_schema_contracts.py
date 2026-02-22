from __future__ import annotations

from datetime import UTC, datetime

from pipelines.common.schema_contracts import build_schema_contract_records


def test_build_schema_contract_records_filters_and_builds_defaults() -> None:
    connectors = [
        {
            "connector_name": "sidra_indicators_fetch",
            "source": "SIDRA",
            "status": "implemented",
        },
        {
            "connector_name": "quality_suite",
            "source": "INTERNAL",
            "status": "implemented",
        },
        {
            "connector_name": "cecad_social_protection_fetch",
            "source": "CECAD",
            "status": "planned",
        },
    ]
    config = {
        "defaults": {
            "schema_version": "v1",
            "status": "active",
            "effective_from": "2026-02-21",
            "notes": "baseline",
        },
        "overrides": {},
    }

    records = build_schema_contract_records(
        connectors,
        config=config,
        now_utc=datetime(2026, 2, 21, 12, 0, tzinfo=UTC),
    )

    assert len(records) == 1
    record = records[0]
    assert record["connector_name"] == "sidra_indicators_fetch"
    assert record["source"] == "SIDRA"
    assert record["dataset"] == "sidra_indicators"
    assert record["target_table"] == "silver.fact_indicator"
    assert record["schema_version"] == "v1"
    assert record["status"] == "active"
    assert record["effective_from"] == "2026-02-21"
    assert "indicator_code" in record["required_columns"]
    assert record["notes"] == "baseline"


def test_build_schema_contract_records_applies_override_fields() -> None:
    connectors = [
        {
            "connector_name": "urban_transport_fetch",
            "source": "OSM",
            "status": "implemented",
            "notes": "connector notes",
        }
    ]
    config = {
        "defaults": {
            "schema_version": "v1",
            "status": "active",
            "effective_from": "2026-02-21",
        },
        "overrides": {
            "urban_transport_fetch": {
                "schema_version": "v2",
                "target_table": "map.urban_transport_stop",
                "dataset": "custom_transport",
                "required_columns": ["source", "geom", "external_id"],
                "optional_columns": ["name"],
                "column_types": {"source": "text", "geom": "geometry(point,4326)"},
                "constraints_json": {"checks": ["source <> ''"]},
                "source_uri": "https://example.com/transport",
                "notes": "override notes",
            }
        },
    }

    records = build_schema_contract_records(connectors, config=config)

    assert len(records) == 1
    record = records[0]
    assert record["schema_version"] == "v2"
    assert record["dataset"] == "custom_transport"
    assert record["required_columns"] == ["external_id", "geom", "source"]
    assert record["optional_columns"] == ["name"]
    assert record["constraints_json"] == {"checks": ["source <> ''"]}
    assert record["source_uri"] == "https://example.com/transport"
    assert record["notes"] == "override notes"
