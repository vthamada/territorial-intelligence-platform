from __future__ import annotations

from pathlib import Path


def test_silver_schema_has_required_tables() -> None:
    schema_sql = Path("db/sql/002_silver_schema.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS silver.dim_territory" in schema_sql
    assert "CREATE TABLE IF NOT EXISTS silver.fact_indicator" in schema_sql
    assert "CREATE TABLE IF NOT EXISTS silver.fact_electorate" in schema_sql
    assert "CREATE TABLE IF NOT EXISTS silver.fact_election_result" in schema_sql
    assert "CREATE TABLE IF NOT EXISTS ops.pipeline_runs" in schema_sql
