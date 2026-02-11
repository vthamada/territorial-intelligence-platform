CREATE INDEX IF NOT EXISTS idx_fact_indicator_period_territory
    ON silver.fact_indicator (reference_period, territory_id);

CREATE INDEX IF NOT EXISTS idx_fact_indicator_source_period
    ON silver.fact_indicator (source, reference_period);

CREATE INDEX IF NOT EXISTS idx_fact_indicator_territory_period_updated
    ON silver.fact_indicator (territory_id, reference_period, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_dim_territory_level_name
    ON silver.dim_territory (level, name);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_ops_filters
    ON ops.pipeline_runs (
        reference_period,
        wave,
        source,
        dataset,
        status,
        started_at_utc DESC
    );
