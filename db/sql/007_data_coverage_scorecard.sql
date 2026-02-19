CREATE OR REPLACE VIEW ops.v_data_coverage_scorecard AS
WITH
connector_totals AS (
    SELECT
        COUNT(*)::numeric AS total_connectors,
        COUNT(*) FILTER (WHERE status::text = 'implemented')::numeric AS implemented_connectors
    FROM ops.connector_registry
),
connector_runs_7d AS (
    SELECT
        COUNT(*)::numeric AS total_runs,
        COUNT(*) FILTER (WHERE pr.status = 'success')::numeric AS successful_runs
    FROM ops.pipeline_runs pr
    JOIN ops.connector_registry cr ON cr.connector_name = pr.job_name
    WHERE cr.status::text = 'implemented'
      AND pr.started_at_utc >= NOW() - INTERVAL '7 days'
),
electorate_years AS (
    SELECT COUNT(DISTINCT reference_year)::numeric AS distinct_years
    FROM silver.fact_electorate
),
election_years AS (
    SELECT COUNT(DISTINCT election_year)::numeric AS distinct_years
    FROM silver.fact_election_result
),
indicator_periods AS (
    SELECT COUNT(DISTINCT reference_period)::numeric AS distinct_periods
    FROM silver.fact_indicator
),
zones AS (
    SELECT COUNT(*)::numeric AS total_zones
    FROM silver.dim_territory
    WHERE level::text = 'electoral_zone'
),
electorate_zone_coverage AS (
    SELECT COUNT(DISTINCT fe.territory_id)::numeric AS covered_zones
    FROM silver.fact_electorate fe
    JOIN silver.dim_territory dt ON dt.territory_id = fe.territory_id
    WHERE dt.level::text = 'electoral_zone'
),
election_zone_coverage AS (
    SELECT COUNT(DISTINCT fr.territory_id)::numeric AS covered_zones
    FROM silver.fact_election_result fr
    JOIN silver.dim_territory dt ON dt.territory_id = fr.territory_id
    WHERE dt.level::text = 'electoral_zone'
),
territory_totals AS (
    SELECT
        COUNT(*) FILTER (WHERE level::text = 'municipality')::numeric AS municipality_total,
        COUNT(*) FILTER (WHERE level::text = 'district')::numeric AS district_total,
        COUNT(*) FILTER (WHERE level::text = 'census_sector')::numeric AS census_sector_total
    FROM silver.dim_territory
),
indicator_territory_coverage AS (
    SELECT
        COUNT(DISTINCT fi.territory_id) FILTER (WHERE dt.level::text = 'municipality')::numeric AS municipality_covered,
        COUNT(DISTINCT fi.territory_id) FILTER (WHERE dt.level::text = 'district')::numeric AS district_covered,
        COUNT(DISTINCT fi.territory_id) FILTER (WHERE dt.level::text = 'census_sector')::numeric AS census_sector_covered
    FROM silver.fact_indicator fi
    JOIN silver.dim_territory dt ON dt.territory_id = fi.territory_id
),
quality_fails_7d AS (
    SELECT COUNT(*)::numeric AS fail_checks
    FROM ops.pipeline_checks
    WHERE status = 'fail'
      AND created_at_utc >= NOW() - INTERVAL '7 days'
),
urban_coverage AS (
    SELECT
        (SELECT COUNT(*)::numeric FROM map.urban_road_segment) AS road_rows,
        (SELECT COUNT(*)::numeric FROM map.urban_poi) AS poi_rows
),
metrics AS (
    SELECT
        'connectors'::text AS metric_group,
        'implemented_connectors_pct'::text AS metric_name,
        CASE
            WHEN ct.total_connectors = 0 THEN 0::numeric
            ELSE ROUND((ct.implemented_connectors / ct.total_connectors) * 100, 2)
        END AS observed_value,
        100::numeric AS target_value,
        'gte'::text AS comparator,
        'pct'::text AS unit
    FROM connector_totals ct

    UNION ALL

    SELECT
        'operations'::text,
        'implemented_runs_success_pct_7d'::text,
        CASE
            WHEN cr.total_runs = 0 THEN 0::numeric
            ELSE ROUND((cr.successful_runs / cr.total_runs) * 100, 2)
        END AS observed_value,
        95::numeric AS target_value,
        'gte'::text AS comparator,
        'pct'::text AS unit
    FROM connector_runs_7d cr

    UNION ALL

    SELECT
        'temporal_coverage'::text,
        'electorate_distinct_years'::text,
        ey.distinct_years,
        5::numeric,
        'gte'::text,
        'years'::text
    FROM electorate_years ey

    UNION ALL

    SELECT
        'temporal_coverage'::text,
        'election_result_distinct_years'::text,
        ey.distinct_years,
        5::numeric,
        'gte'::text,
        'years'::text
    FROM election_years ey

    UNION ALL

    SELECT
        'temporal_coverage'::text,
        'indicator_distinct_periods'::text,
        ip.distinct_periods,
        5::numeric,
        'gte'::text,
        'periods'::text
    FROM indicator_periods ip

    UNION ALL

    SELECT
        'territorial_coverage'::text,
        'electorate_zone_coverage_pct'::text,
        CASE
            WHEN z.total_zones = 0 THEN 0::numeric
            ELSE ROUND((ezc.covered_zones / z.total_zones) * 100, 2)
        END AS observed_value,
        100::numeric AS target_value,
        'gte'::text AS comparator,
        'pct'::text AS unit
    FROM zones z
    CROSS JOIN electorate_zone_coverage ezc

    UNION ALL

    SELECT
        'territorial_coverage'::text,
        'election_result_zone_coverage_pct'::text,
        CASE
            WHEN z.total_zones = 0 THEN 0::numeric
            ELSE ROUND((ezc.covered_zones / z.total_zones) * 100, 2)
        END AS observed_value,
        100::numeric AS target_value,
        'gte'::text AS comparator,
        'pct'::text AS unit
    FROM zones z
    CROSS JOIN election_zone_coverage ezc

    UNION ALL

    SELECT
        'territorial_coverage'::text,
        'indicator_municipality_coverage_pct'::text,
        CASE
            WHEN tt.municipality_total = 0 THEN 0::numeric
            ELSE ROUND((itc.municipality_covered / tt.municipality_total) * 100, 2)
        END AS observed_value,
        100::numeric AS target_value,
        'gte'::text AS comparator,
        'pct'::text AS unit
    FROM territory_totals tt
    CROSS JOIN indicator_territory_coverage itc

    UNION ALL

    SELECT
        'territorial_coverage'::text,
        'indicator_district_coverage_pct'::text,
        CASE
            WHEN tt.district_total = 0 THEN 0::numeric
            ELSE ROUND((itc.district_covered / tt.district_total) * 100, 2)
        END AS observed_value,
        80::numeric AS target_value,
        'gte'::text AS comparator,
        'pct'::text AS unit
    FROM territory_totals tt
    CROSS JOIN indicator_territory_coverage itc

    UNION ALL

    SELECT
        'territorial_coverage'::text,
        'indicator_census_sector_coverage_pct'::text,
        CASE
            WHEN tt.census_sector_total = 0 THEN 0::numeric
            ELSE ROUND((itc.census_sector_covered / tt.census_sector_total) * 100, 2)
        END AS observed_value,
        60::numeric AS target_value,
        'gte'::text AS comparator,
        'pct'::text AS unit
    FROM territory_totals tt
    CROSS JOIN indicator_territory_coverage itc

    UNION ALL

    SELECT
        'quality'::text,
        'fail_checks_last_7d'::text,
        qf.fail_checks AS observed_value,
        0::numeric AS target_value,
        'lte'::text AS comparator,
        'count'::text AS unit
    FROM quality_fails_7d qf

    UNION ALL

    SELECT
        'urban_coverage'::text,
        'urban_road_rows'::text,
        uc.road_rows AS observed_value,
        1::numeric AS target_value,
        'gte'::text AS comparator,
        'count'::text AS unit
    FROM urban_coverage uc

    UNION ALL

    SELECT
        'urban_coverage'::text,
        'urban_poi_rows'::text,
        uc.poi_rows AS observed_value,
        1::numeric AS target_value,
        'gte'::text AS comparator,
        'count'::text AS unit
    FROM urban_coverage uc
)
SELECT
    NOW() AS generated_at_utc,
    metric_group,
    metric_name,
    observed_value,
    target_value,
    comparator,
    unit,
    CASE
        WHEN comparator = 'gte' AND observed_value >= target_value THEN 'pass'
        WHEN comparator = 'lte' AND observed_value <= target_value THEN 'pass'
        ELSE 'warn'
    END AS status
FROM metrics;
