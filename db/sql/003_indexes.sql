CREATE INDEX IF NOT EXISTS idx_dim_territory_parent
    ON silver.dim_territory (parent_territory_id);

CREATE INDEX IF NOT EXISTS idx_dim_territory_level_municipality
    ON silver.dim_territory (level, municipality_ibge_code);

CREATE INDEX IF NOT EXISTS idx_dim_territory_canonical_key
    ON silver.dim_territory (canonical_key);

CREATE INDEX IF NOT EXISTS idx_fact_indicator_lookup
    ON silver.fact_indicator (indicator_code, reference_period, territory_id);

CREATE INDEX IF NOT EXISTS idx_fact_electorate_lookup
    ON silver.fact_electorate (reference_year, territory_id);

CREATE INDEX IF NOT EXISTS idx_fact_election_result_lookup
    ON silver.fact_election_result (election_year, territory_id, metric);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_job_status
    ON ops.pipeline_runs (job_name, status, started_at_utc DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_checks_run_id
    ON ops.pipeline_checks (run_id);

CREATE INDEX IF NOT EXISTS idx_connector_registry_status
    ON ops.connector_registry (status, wave);

-- Spatial index on dim_territory geometry for MVT tile queries (MP-2/MP-3)
CREATE INDEX IF NOT EXISTS idx_dim_territory_geometry
    ON silver.dim_territory USING GIST (geometry)
    WHERE geometry IS NOT NULL;
