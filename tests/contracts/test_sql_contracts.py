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
    assert "'urban_road_rows'" in scorecard_sql
    assert "'urban_poi_rows'" in scorecard_sql


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
