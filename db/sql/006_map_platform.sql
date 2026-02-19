CREATE SCHEMA IF NOT EXISTS map;

CREATE TABLE IF NOT EXISTS map.layer_catalog (
    layer_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    territory_level TEXT NOT NULL,
    is_official BOOLEAN NOT NULL,
    source TEXT NOT NULL,
    default_visibility BOOLEAN NOT NULL,
    zoom_min INTEGER NOT NULL,
    zoom_max INTEGER NULL,
    updated_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO map.layer_catalog (
    layer_id,
    label,
    territory_level,
    is_official,
    source,
    default_visibility,
    zoom_min,
    zoom_max
)
VALUES
    (
        'territory_municipality',
        'Municipios',
        'municipality',
        TRUE,
        'silver.dim_territory',
        TRUE,
        0,
        8
    ),
    (
        'territory_district',
        'Distritos',
        'district',
        TRUE,
        'silver.dim_territory',
        TRUE,
        9,
        11
    ),
    (
        'territory_census_sector',
        'Setores censitarios',
        'census_sector',
        FALSE,
        'silver.dim_territory',
        FALSE,
        12,
        NULL
    )
ON CONFLICT (layer_id) DO UPDATE
SET
    label = EXCLUDED.label,
    territory_level = EXCLUDED.territory_level,
    is_official = EXCLUDED.is_official,
    source = EXCLUDED.source,
    default_visibility = EXCLUDED.default_visibility,
    zoom_min = EXCLUDED.zoom_min,
    zoom_max = EXCLUDED.zoom_max,
    updated_at_utc = NOW();

DROP VIEW IF EXISTS map.layer_stats;

DROP MATERIALIZED VIEW IF EXISTS map.mv_territory_municipality;
CREATE MATERIALIZED VIEW map.mv_territory_municipality AS
SELECT
    dt.territory_id,
    dt.name,
    dt.level::text AS territory_level,
    dt.municipality_ibge_code,
    dt.uf,
    dt.geometry AS geom,
    ST_SimplifyPreserveTopology(dt.geometry, 0.002) AS geom_simplified
FROM silver.dim_territory dt
WHERE dt.level::text = 'municipality'
  AND dt.geometry IS NOT NULL;

DROP MATERIALIZED VIEW IF EXISTS map.mv_territory_district;
CREATE MATERIALIZED VIEW map.mv_territory_district AS
SELECT
    dt.territory_id,
    dt.name,
    dt.level::text AS territory_level,
    dt.municipality_ibge_code,
    dt.uf,
    dt.geometry AS geom,
    ST_SimplifyPreserveTopology(dt.geometry, 0.0008) AS geom_simplified
FROM silver.dim_territory dt
WHERE dt.level::text = 'district'
  AND dt.geometry IS NOT NULL;

DROP MATERIALIZED VIEW IF EXISTS map.mv_territory_census_sector;
CREATE MATERIALIZED VIEW map.mv_territory_census_sector AS
SELECT
    dt.territory_id,
    dt.name,
    dt.level::text AS territory_level,
    dt.municipality_ibge_code,
    dt.uf,
    dt.geometry AS geom,
    ST_SimplifyPreserveTopology(dt.geometry, 0.0002) AS geom_simplified
FROM silver.dim_territory dt
WHERE dt.level::text = 'census_sector'
  AND dt.geometry IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_territory_municipality_id
    ON map.mv_territory_municipality (territory_id);
CREATE INDEX IF NOT EXISTS idx_mv_territory_municipality_geom_gist
    ON map.mv_territory_municipality USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_mv_territory_municipality_geom_simple_gist
    ON map.mv_territory_municipality USING GIST (geom_simplified);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_territory_district_id
    ON map.mv_territory_district (territory_id);
CREATE INDEX IF NOT EXISTS idx_mv_territory_district_geom_gist
    ON map.mv_territory_district USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_mv_territory_district_geom_simple_gist
    ON map.mv_territory_district USING GIST (geom_simplified);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_territory_census_sector_id
    ON map.mv_territory_census_sector (territory_id);
CREATE INDEX IF NOT EXISTS idx_mv_territory_census_sector_geom_gist
    ON map.mv_territory_census_sector USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_mv_territory_census_sector_geom_simple_gist
    ON map.mv_territory_census_sector USING GIST (geom_simplified);

CREATE INDEX IF NOT EXISTS idx_dim_territory_geometry_gist
    ON silver.dim_territory USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_fact_indicator_map_filters
    ON silver.fact_indicator (indicator_code, reference_period, category, territory_id);

CREATE OR REPLACE VIEW map.layer_stats AS
SELECT
    c.layer_id,
    c.territory_level,
    c.zoom_min,
    c.zoom_max,
    CASE c.layer_id
        WHEN 'territory_municipality' THEN (SELECT COUNT(*) FROM map.mv_territory_municipality)
        WHEN 'territory_district' THEN (SELECT COUNT(*) FROM map.mv_territory_district)
        WHEN 'territory_census_sector' THEN (SELECT COUNT(*) FROM map.mv_territory_census_sector)
        ELSE 0
    END::BIGINT AS row_count,
    c.updated_at_utc
FROM map.layer_catalog c;

CREATE OR REPLACE FUNCTION map.refresh_materialized_layers()
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW map.mv_territory_municipality;
    REFRESH MATERIALIZED VIEW map.mv_territory_district;
    REFRESH MATERIALIZED VIEW map.mv_territory_census_sector;
END;
$$;
