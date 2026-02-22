-- D8 / BD-081
-- Performance and cost tuning for operational and map hot paths.

-- ----------------------------------------------------------------------------
-- Ops query tuning
-- ----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_pipeline_checks_status_created
    ON ops.pipeline_checks (status, created_at_utc DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_checks_name_created
    ON ops.pipeline_checks (check_name, created_at_utc DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_checks_created_run
    ON ops.pipeline_checks (created_at_utc DESC, run_id);

CREATE INDEX IF NOT EXISTS idx_connector_registry_updated_filters
    ON ops.connector_registry (updated_at_utc DESC, wave, status, source);

CREATE INDEX IF NOT EXISTS idx_frontend_events_name_timestamp
    ON ops.frontend_events (name, event_timestamp_utc DESC);

-- ----------------------------------------------------------------------------
-- Map geocoding tuning (ILIKE / lower(name) hot paths)
-- ----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_urban_road_segment_name_trgm
    ON map.urban_road_segment
    USING GIN (lower(COALESCE(name, '')) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_urban_poi_name_trgm
    ON map.urban_poi
    USING GIN (lower(COALESCE(name, '')) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_urban_transport_stop_name_trgm
    ON map.urban_transport_stop
    USING GIN (lower(COALESCE(name, '')) gin_trgm_ops);
