from __future__ import annotations

from pathlib import Path


def test_silver_schema_has_required_tables() -> None:
    schema_sql = Path("db/sql/002_silver_schema.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS silver.dim_territory" in schema_sql
    assert "CREATE TABLE IF NOT EXISTS silver.fact_indicator" in schema_sql
    assert "CREATE TABLE IF NOT EXISTS silver.fact_electorate" in schema_sql
    assert "CREATE TABLE IF NOT EXISTS silver.fact_election_result" in schema_sql
    assert "CREATE TABLE IF NOT EXISTS ops.pipeline_runs" in schema_sql


def test_map_platform_sql_has_required_objects() -> None:
    map_sql = Path("db/sql/006_map_platform.sql").read_text(encoding="utf-8")
    assert "CREATE SCHEMA IF NOT EXISTS map;" in map_sql
    assert "CREATE TABLE IF NOT EXISTS map.layer_catalog" in map_sql
    assert "CREATE MATERIALIZED VIEW map.mv_territory_municipality" in map_sql
    assert "CREATE MATERIALIZED VIEW map.mv_territory_district" in map_sql
    assert "CREATE MATERIALIZED VIEW map.mv_territory_census_sector" in map_sql
    assert "CREATE OR REPLACE FUNCTION map.refresh_materialized_layers()" in map_sql


def test_data_coverage_scorecard_sql_has_required_objects() -> None:
    scorecard_sql = Path("db/sql/007_data_coverage_scorecard.sql").read_text(encoding="utf-8")
    assert "CREATE OR REPLACE VIEW ops.v_data_coverage_scorecard AS" in scorecard_sql
    assert "'implemented_connectors_pct'" in scorecard_sql
    assert "'electorate_distinct_years'" in scorecard_sql
    assert "'election_result_distinct_years'" in scorecard_sql
    assert "'indicator_district_coverage_pct'" in scorecard_sql
    assert "'inmet_distinct_periods'" in scorecard_sql
    assert "'inpe_queimadas_distinct_periods'" in scorecard_sql
    assert "'ana_distinct_periods'" in scorecard_sql
    assert "'environment_risk_district_rows'" in scorecard_sql
    assert "'environment_risk_census_sector_rows'" in scorecard_sql
    assert "'environment_risk_distinct_periods'" in scorecard_sql
    assert "'environment_risk_mart_municipality_rows'" in scorecard_sql
    assert "'environment_risk_mart_district_rows'" in scorecard_sql
    assert "'environment_risk_mart_census_sector_rows'" in scorecard_sql
    assert "'environment_risk_mart_distinct_periods'" in scorecard_sql
    assert "'priority_drivers_rows'" in scorecard_sql
    assert "'priority_drivers_distinct_periods'" in scorecard_sql
    assert "'priority_drivers_missing_score_version_rows'" in scorecard_sql
    assert "'strategic_score_total_versions'" in scorecard_sql
    assert "'strategic_score_active_versions_min'" in scorecard_sql
    assert "'strategic_score_active_versions_max'" in scorecard_sql
    assert "'schema_contracts_active_coverage_pct'" in scorecard_sql
    assert "'schema_drift_fail_checks_last_7d'" in scorecard_sql
    assert "'tse_catalog_discovery'" in scorecard_sql
    assert "'urban_road_rows'" in scorecard_sql
    assert "'urban_poi_rows'" in scorecard_sql
    assert "'urban_transport_stop_rows'" in scorecard_sql


def test_social_domain_sql_has_required_objects() -> None:
    social_sql = Path("db/sql/008_social_domain.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS silver.fact_social_protection" in social_sql
    assert "CREATE TABLE IF NOT EXISTS silver.fact_social_assistance_network" in social_sql
    assert "idx_fact_social_protection_lookup" in social_sql
    assert "idx_fact_social_assistance_network_lookup" in social_sql


def test_urban_domain_sql_has_required_objects() -> None:
    urban_sql = Path("db/sql/009_urban_domain.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS map.urban_road_segment" in urban_sql
    assert "CREATE TABLE IF NOT EXISTS map.urban_poi" in urban_sql
    assert "idx_urban_road_segment_geom_gist" in urban_sql
    assert "idx_urban_poi_geom_gist" in urban_sql
    assert "CREATE OR REPLACE VIEW map.v_urban_data_coverage AS" in urban_sql


def test_urban_transport_sql_has_required_objects() -> None:
    transport_sql = Path("db/sql/010_urban_transport_domain.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS map.urban_transport_stop" in transport_sql
    assert "idx_urban_transport_stop_geom_gist" in transport_sql
    assert "'urban_transport_stops'" in transport_sql
    assert "'urban_transport_stop'" in transport_sql


def test_mobility_access_mart_sql_has_required_objects() -> None:
    mobility_sql = Path("db/sql/011_mobility_access_mart.sql").read_text(encoding="utf-8")
    assert "CREATE OR REPLACE VIEW gold.mart_mobility_access AS" in mobility_sql
    assert "JOIN map.urban_transport_stop" in mobility_sql
    assert "JOIN map.urban_road_segment" in mobility_sql
    assert "JOIN map.urban_poi" in mobility_sql
    assert "mobility_access_score" in mobility_sql
    assert "mobility_access_deficit_score" in mobility_sql


def test_environment_risk_aggregation_sql_has_required_objects() -> None:
    environment_sql = Path("db/sql/012_environment_risk_aggregation.sql").read_text(encoding="utf-8")
    assert "CREATE OR REPLACE VIEW map.v_environment_risk_aggregation AS" in environment_sql
    assert "dt.level::text IN ('district', 'census_sector')" in environment_sql
    assert "hazard_score" in environment_sql
    assert "exposure_score" in environment_sql
    assert "environment_risk_score" in environment_sql


def test_environment_risk_mart_sql_has_required_objects() -> None:
    mart_sql = Path("db/sql/013_environment_risk_mart.sql").read_text(encoding="utf-8")
    assert "CREATE OR REPLACE VIEW gold.mart_environment_risk AS" in mart_sql
    assert "FROM map.v_environment_risk_aggregation" in mart_sql
    assert "'municipality'::text AS territory_level" in mart_sql
    assert "risk_percentile" in mart_sql
    assert "risk_priority_rank" in mart_sql
    assert "environment_risk_score" in mart_sql


def test_source_schema_contracts_sql_has_required_objects() -> None:
    contracts_sql = Path("db/sql/014_source_schema_contracts.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS ops.source_schema_contracts" in contracts_sql
    assert "uq_source_schema_contract_active" in contracts_sql
    assert "CREATE OR REPLACE VIEW ops.v_source_schema_contracts_active AS" in contracts_sql


def test_priority_drivers_mart_sql_has_required_objects() -> None:
    priority_sql = Path("db/sql/015_priority_drivers_mart.sql").read_text(encoding="utf-8")
    assert "CREATE OR REPLACE VIEW gold.mart_priority_drivers AS" in priority_sql
    assert "FROM silver.fact_indicator fi" in priority_sql
    assert "JOIN silver.dim_territory dt" in priority_sql
    assert "FROM ops.v_strategic_score_version_active" in priority_sql
    assert "score_version" in priority_sql
    assert "config_version" in priority_sql
    assert "priority_score" in priority_sql
    assert "priority_status" in priority_sql
    assert "driver_rank" in priority_sql
    assert "scoring_method" in priority_sql
    assert "domain_weight" in priority_sql
    assert "indicator_weight" in priority_sql
    assert "weighted_magnitude" in priority_sql


def test_strategic_score_versions_sql_has_required_objects() -> None:
    strategic_sql = Path("db/sql/016_strategic_score_versions.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS ops.strategic_score_versions" in strategic_sql
    assert "uq_strategic_score_versions_active" in strategic_sql
    assert "CREATE OR REPLACE VIEW ops.v_strategic_score_version_active AS" in strategic_sql
    assert "default_domain_weight" in strategic_sql
    assert "default_indicator_weight" in strategic_sql
    assert "domain_weights JSONB" in strategic_sql
    assert "indicator_weights JSONB" in strategic_sql
