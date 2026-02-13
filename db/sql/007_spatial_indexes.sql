-- 007_spatial_indexes.sql
-- Dedicated spatial indexes for geospatial queries.
-- Addresses item A03 of the traceability matrix (GIST indexes and geospatial tuning).

-- GIST index on dim_territory geometry for choropleth and spatial joins.
CREATE INDEX IF NOT EXISTS idx_dim_territory_geom_gist
    ON silver.dim_territory USING GIST (geometry);

-- Filtered index: only territories with geometry (avoids indexing NULLs).
CREATE INDEX IF NOT EXISTS idx_dim_territory_geom_notnull
    ON silver.dim_territory USING GIST (geometry)
    WHERE geometry IS NOT NULL;

-- Composite index for level-filtered spatial queries (zoom-based layer switching).
CREATE INDEX IF NOT EXISTS idx_dim_territory_level_geom
    ON silver.dim_territory (level)
    WHERE geometry IS NOT NULL;

-- Index for territory lookup by level, name and ibge_code (map search).
CREATE INDEX IF NOT EXISTS idx_dim_territory_name_trgm
    ON silver.dim_territory USING GIN (normalized_name gin_trgm_ops);

-- Covering index for fact_indicator queries that join on territory for map rendering.
CREATE INDEX IF NOT EXISTS idx_fact_indicator_map_query
    ON silver.fact_indicator (indicator_code, reference_period, territory_id, value);
