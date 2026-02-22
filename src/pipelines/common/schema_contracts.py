from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

SUPPORTED_CONNECTOR_STATUSES = {"implemented", "partial"}
SKIPPED_CONNECTORS = {"quality_suite", "dbt_build", "tse_catalog_discovery"}

TARGET_TABLE_BY_CONNECTOR: dict[str, str] = {
    "ibge_admin_fetch": "silver.dim_territory",
    "ibge_geometries_fetch": "silver.dim_territory",
    "tse_electorate_fetch": "silver.fact_electorate",
    "tse_results_fetch": "silver.fact_election_result",
    "cecad_social_protection_fetch": "silver.fact_social_protection",
    "censo_suas_fetch": "silver.fact_social_assistance_network",
    "urban_roads_fetch": "map.urban_road_segment",
    "urban_pois_fetch": "map.urban_poi",
    "urban_transport_fetch": "map.urban_transport_stop",
}

DATASET_BY_CONNECTOR: dict[str, str] = {
    "ibge_admin_fetch": "ibge_admin",
    "ibge_geometries_fetch": "ibge_geometries",
    "ibge_indicators_fetch": "ibge_indicators",
    "tse_electorate_fetch": "tse_electorate",
    "tse_results_fetch": "tse_results",
    "education_inep_fetch": "inep_education",
    "health_datasus_fetch": "datasus_health",
    "finance_siconfi_fetch": "siconfi_finance",
    "labor_mte_fetch": "mte_novo_caged",
    "sidra_indicators_fetch": "sidra_indicators",
    "senatran_fleet_fetch": "senatran_fleet",
    "sejusp_public_safety_fetch": "sejusp_public_safety",
    "siops_health_finance_fetch": "siops_health_finance",
    "snis_sanitation_fetch": "snis_sanitation",
    "inmet_climate_fetch": "inmet_climate",
    "inpe_queimadas_fetch": "inpe_queimadas",
    "ana_hydrology_fetch": "ana_hydrology",
    "anatel_connectivity_fetch": "anatel_connectivity",
    "aneel_energy_fetch": "aneel_energy",
    "cecad_social_protection_fetch": "cecad_social_protection",
    "censo_suas_fetch": "censo_suas",
    "urban_roads_fetch": "urban_road_segment",
    "urban_pois_fetch": "urban_poi",
    "urban_transport_fetch": "urban_transport_stop",
}

REQUIRED_COLUMNS_BY_TABLE: dict[str, list[str]] = {
    "silver.fact_indicator": [
        "territory_id",
        "source",
        "dataset",
        "indicator_code",
        "indicator_name",
        "value",
        "reference_period",
    ],
    "silver.fact_electorate": ["territory_id", "reference_year", "voters"],
    "silver.fact_election_result": ["territory_id", "election_year", "metric", "value"],
    "silver.dim_territory": [
        "territory_id",
        "level",
        "canonical_key",
        "source_system",
        "source_entity_id",
        "name",
        "normalized_name",
        "municipality_ibge_code",
    ],
    "silver.fact_social_protection": [
        "territory_id",
        "source",
        "dataset",
        "reference_period",
    ],
    "silver.fact_social_assistance_network": [
        "territory_id",
        "source",
        "dataset",
        "reference_period",
    ],
    "map.urban_road_segment": ["source", "geom"],
    "map.urban_poi": ["source", "geom"],
    "map.urban_transport_stop": ["source", "geom"],
}

OPTIONAL_COLUMNS_BY_TABLE: dict[str, list[str]] = {
    "silver.fact_indicator": ["unit", "category", "updated_at"],
    "silver.fact_electorate": ["sex", "age_range", "education"],
    "silver.fact_election_result": ["election_round", "office"],
    "silver.dim_territory": [
        "parent_territory_id",
        "ibge_geocode",
        "tse_zone",
        "tse_section",
        "uf",
        "valid_from",
        "valid_to",
        "geometry",
        "metadata",
    ],
    "silver.fact_social_protection": [
        "households_total",
        "people_total",
        "avg_income_per_capita",
        "poverty_rate",
        "extreme_poverty_rate",
        "metadata_json",
        "updated_at",
    ],
    "silver.fact_social_assistance_network": [
        "cras_units",
        "creas_units",
        "social_units_total",
        "workers_total",
        "service_capacity_total",
        "metadata_json",
        "updated_at",
    ],
    "map.urban_road_segment": [
        "external_id",
        "name",
        "road_class",
        "is_oneway",
        "metadata_json",
    ],
    "map.urban_poi": [
        "external_id",
        "name",
        "category",
        "subcategory",
        "metadata_json",
    ],
    "map.urban_transport_stop": [
        "external_id",
        "name",
        "mode",
        "operator",
        "is_accessible",
        "metadata_json",
    ],
}

COLUMN_TYPES_BY_TABLE: dict[str, dict[str, str]] = {
    "silver.fact_indicator": {
        "territory_id": "uuid",
        "source": "text",
        "dataset": "text",
        "indicator_code": "text",
        "indicator_name": "text",
        "value": "numeric",
        "reference_period": "text",
    },
    "silver.fact_electorate": {
        "territory_id": "uuid",
        "reference_year": "integer",
        "voters": "integer",
    },
    "silver.fact_election_result": {
        "territory_id": "uuid",
        "election_year": "integer",
        "metric": "text",
        "value": "numeric",
    },
    "silver.dim_territory": {
        "territory_id": "uuid",
        "level": "silver.territory_level",
        "canonical_key": "text",
        "source_system": "text",
        "source_entity_id": "text",
        "name": "text",
        "normalized_name": "text",
        "municipality_ibge_code": "text",
    },
    "silver.fact_social_protection": {
        "territory_id": "uuid",
        "source": "text",
        "dataset": "text",
        "reference_period": "text",
    },
    "silver.fact_social_assistance_network": {
        "territory_id": "uuid",
        "source": "text",
        "dataset": "text",
        "reference_period": "text",
    },
    "map.urban_road_segment": {"source": "text", "geom": "geometry(linestring,4326)"},
    "map.urban_poi": {"source": "text", "geom": "geometry(point,4326)"},
    "map.urban_transport_stop": {"source": "text", "geom": "geometry(point,4326)"},
}

CONSTRAINTS_BY_TABLE: dict[str, dict[str, Any]] = {
    "silver.fact_indicator": {
        "unique_key": [
            "territory_id",
            "source",
            "dataset",
            "indicator_code",
            "category",
            "reference_period",
        ]
    },
    "silver.fact_electorate": {
        "checks": ["voters >= 0"],
        "unique_key": [
            "territory_id",
            "reference_year",
            "sex",
            "age_range",
            "education",
        ],
    },
    "silver.fact_election_result": {
        "checks": ["value >= 0"],
        "unique_key": [
            "territory_id",
            "election_year",
            "election_round",
            "office",
            "metric",
        ],
    },
}


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if isinstance(payload, dict):
        return payload
    return {}


def load_connectors(path: Path) -> list[dict[str, Any]]:
    payload = load_yaml(path)
    connectors = payload.get("connectors", [])
    if not isinstance(connectors, list):
        return []
    return [item for item in connectors if isinstance(item, dict)]


def load_schema_contract_config(path: Path) -> dict[str, Any]:
    payload = load_yaml(path)
    defaults = payload.get("defaults", {})
    overrides = payload.get("overrides", {})
    return {
        "defaults": defaults if isinstance(defaults, dict) else {},
        "overrides": overrides if isinstance(overrides, dict) else {},
    }


def _infer_target_table(connector_name: str) -> str:
    return TARGET_TABLE_BY_CONNECTOR.get(connector_name, "silver.fact_indicator")


def _infer_dataset(connector_name: str) -> str:
    return DATASET_BY_CONNECTOR.get(connector_name, connector_name)


def build_schema_contract_records(
    connectors: list[dict[str, Any]],
    *,
    config: dict[str, Any],
    now_utc: datetime | None = None,
) -> list[dict[str, Any]]:
    now_utc = now_utc or datetime.now(UTC)
    defaults = config.get("defaults", {})
    overrides = config.get("overrides", {})

    default_version = str(defaults.get("schema_version", "v1"))
    default_status = str(defaults.get("status", "active"))
    default_notes = str(defaults.get("notes", ""))
    default_effective_from = str(defaults.get("effective_from", date.today().isoformat()))

    records: list[dict[str, Any]] = []
    for connector in connectors:
        connector_name = str(connector.get("connector_name") or "").strip()
        if not connector_name or connector_name in SKIPPED_CONNECTORS:
            continue
        connector_status = str(connector.get("status") or "").strip().lower()
        if connector_status not in SUPPORTED_CONNECTOR_STATUSES:
            continue

        source = str(connector.get("source") or "").strip()
        if not source or source.upper() == "INTERNAL":
            continue

        override = overrides.get(connector_name, {})
        if not isinstance(override, dict):
            override = {}

        target_table = str(override.get("target_table") or _infer_target_table(connector_name))
        dataset = str(override.get("dataset") or _infer_dataset(connector_name))
        schema_version = str(override.get("schema_version") or default_version)
        contract_status = str(override.get("status") or default_status)
        effective_from = str(override.get("effective_from") or default_effective_from)
        notes = str(override.get("notes") or default_notes or connector.get("notes") or "")
        source_uri = str(override.get("source_uri") or "")

        required_columns = override.get("required_columns")
        if not isinstance(required_columns, list):
            required_columns = REQUIRED_COLUMNS_BY_TABLE.get(target_table, [])

        optional_columns = override.get("optional_columns")
        if not isinstance(optional_columns, list):
            optional_columns = OPTIONAL_COLUMNS_BY_TABLE.get(target_table, [])

        column_types = override.get("column_types")
        if not isinstance(column_types, dict):
            column_types = COLUMN_TYPES_BY_TABLE.get(target_table, {})

        constraints_json = override.get("constraints_json")
        if not isinstance(constraints_json, dict):
            constraints_json = CONSTRAINTS_BY_TABLE.get(target_table, {})

        records.append(
            {
                "connector_name": connector_name,
                "source": source,
                "dataset": dataset,
                "target_table": target_table,
                "schema_version": schema_version,
                "effective_from": effective_from,
                "status": contract_status,
                "required_columns": sorted({str(item) for item in required_columns if str(item).strip()}),
                "optional_columns": sorted({str(item) for item in optional_columns if str(item).strip()}),
                "column_types": {str(k): str(v) for k, v in column_types.items()},
                "constraints_json": constraints_json,
                "source_uri": source_uri or None,
                "notes": notes or None,
                "updated_at_utc": now_utc.isoformat(),
            }
        )

    records.sort(key=lambda item: (item["connector_name"], item["target_table"]))
    return records
