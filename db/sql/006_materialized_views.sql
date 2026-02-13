-- 006_materialized_views.sql
-- Materialized views for map platform and priority ranking.
-- Addresses items A04 (materialized views) and A05 (simplified geometries)
-- from the traceability matrix.

-- ============================================================================
-- 1) Materialized view: territory ranking by indicator (priority/overview)
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.mv_territory_ranking AS
SELECT
    fi.territory_id,
    dt.name                AS territory_name,
    dt.level::text         AS territory_level,
    dt.municipality_ibge_code,
    fi.source,
    fi.dataset,
    fi.indicator_code,
    fi.indicator_name,
    fi.unit,
    fi.reference_period,
    fi.value,
    fi.updated_at,
    RANK() OVER (
        PARTITION BY fi.indicator_code, fi.reference_period
        ORDER BY fi.value DESC
    ) AS rank_desc,
    RANK() OVER (
        PARTITION BY fi.indicator_code, fi.reference_period
        ORDER BY fi.value ASC
    ) AS rank_asc,
    PERCENT_RANK() OVER (
        PARTITION BY fi.indicator_code, fi.reference_period
        ORDER BY fi.value ASC
    ) AS percentile_asc
FROM silver.fact_indicator fi
JOIN silver.dim_territory dt ON dt.territory_id = fi.territory_id
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uidx_mv_territory_ranking
    ON gold.mv_territory_ranking (territory_id, indicator_code, reference_period);

CREATE INDEX IF NOT EXISTS idx_mv_territory_ranking_lookup
    ON gold.mv_territory_ranking (indicator_code, reference_period, rank_desc);


-- ============================================================================
-- 2) Materialized view: map choropleth data (pre-joined for fast render)
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.mv_map_choropleth AS
SELECT
    dt.territory_id,
    dt.name                AS territory_name,
    dt.level::text         AS territory_level,
    dt.municipality_ibge_code,
    fi.indicator_code      AS metric,
    fi.reference_period,
    fi.value,
    fi.source,
    fi.updated_at,
    dt.geometry
FROM silver.fact_indicator fi
JOIN silver.dim_territory dt ON dt.territory_id = fi.territory_id
WHERE dt.geometry IS NOT NULL
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uidx_mv_map_choropleth
    ON gold.mv_map_choropleth (territory_id, metric, reference_period);

CREATE INDEX IF NOT EXISTS idx_mv_map_choropleth_lookup
    ON gold.mv_map_choropleth (metric, reference_period, territory_level);

CREATE INDEX IF NOT EXISTS idx_mv_map_choropleth_geom
    ON gold.mv_map_choropleth USING GIST (geometry);


-- ============================================================================
-- 3) Materialized view: territory summary for map layers
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.mv_territory_map_summary AS
SELECT
    dt.territory_id,
    dt.name                 AS territory_name,
    dt.level::text          AS territory_level,
    dt.municipality_ibge_code,
    dt.parent_territory_id,
    dt.uf,
    ST_SimplifyPreserveTopology(dt.geometry, 0.001) AS geometry_simplified,
    dt.geometry             AS geometry_full,
    COUNT(DISTINCT fi.indicator_code) AS indicator_count,
    MAX(fi.updated_at)      AS last_indicator_updated_at
FROM silver.dim_territory dt
LEFT JOIN silver.fact_indicator fi ON fi.territory_id = dt.territory_id
GROUP BY
    dt.territory_id,
    dt.name,
    dt.level,
    dt.municipality_ibge_code,
    dt.parent_territory_id,
    dt.uf,
    dt.geometry
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uidx_mv_territory_map_summary
    ON gold.mv_territory_map_summary (territory_id);

CREATE INDEX IF NOT EXISTS idx_mv_territory_map_summary_level
    ON gold.mv_territory_map_summary (territory_level);

CREATE INDEX IF NOT EXISTS idx_mv_territory_map_summary_geom_simplified
    ON gold.mv_territory_map_summary USING GIST (geometry_simplified);

CREATE INDEX IF NOT EXISTS idx_mv_territory_map_summary_geom_full
    ON gold.mv_territory_map_summary USING GIST (geometry_full);


-- ============================================================================
-- 4) Refresh function (call after pipeline runs or on schedule)
-- ============================================================================
CREATE OR REPLACE FUNCTION gold.refresh_materialized_views()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_matviews
        WHERE schemaname = 'gold'
          AND matviewname = 'mv_territory_ranking'
          AND ispopulated
    ) THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY gold.mv_territory_ranking;
    ELSE
        REFRESH MATERIALIZED VIEW gold.mv_territory_ranking;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_matviews
        WHERE schemaname = 'gold'
          AND matviewname = 'mv_map_choropleth'
          AND ispopulated
    ) THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY gold.mv_map_choropleth;
    ELSE
        REFRESH MATERIALIZED VIEW gold.mv_map_choropleth;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_matviews
        WHERE schemaname = 'gold'
          AND matviewname = 'mv_territory_map_summary'
          AND ispopulated
    ) THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY gold.mv_territory_map_summary;
    ELSE
        REFRESH MATERIALIZED VIEW gold.mv_territory_map_summary;
    END IF;
END;
$$;

-- Note: Initial population requires:
--   REFRESH MATERIALIZED VIEW gold.mv_territory_ranking;
--   REFRESH MATERIALIZED VIEW gold.mv_map_choropleth;
--   REFRESH MATERIALIZED VIEW gold.mv_territory_map_summary;
