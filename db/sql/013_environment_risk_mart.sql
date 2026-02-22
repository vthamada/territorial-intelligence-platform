CREATE OR REPLACE VIEW gold.mart_environment_risk AS
WITH base AS (
    SELECT
        v.reference_period,
        v.territory_id,
        v.territory_name,
        v.territory_level,
        v.municipality_ibge_code,
        v.hazard_score,
        v.exposure_score,
        v.environment_risk_score,
        v.priority_status,
        v.area_km2,
        v.road_km,
        v.pois_count,
        v.transport_stops_count,
        v.road_density_km_per_km2,
        v.pois_per_km2,
        v.transport_stops_per_km2,
        v.uses_proxy_allocation,
        v.allocation_method,
        v.geometry
    FROM map.v_environment_risk_aggregation v
),
municipality_dim AS (
    SELECT
        dt.territory_id,
        dt.name AS territory_name,
        dt.municipality_ibge_code,
        CASE
            WHEN ST_SRID(dt.geometry) = 4326 THEN
                CASE WHEN ST_IsValid(dt.geometry) THEN dt.geometry ELSE ST_MakeValid(dt.geometry) END
            ELSE
                ST_Transform(
                    CASE WHEN ST_IsValid(dt.geometry) THEN dt.geometry ELSE ST_MakeValid(dt.geometry) END,
                    4326
                )
        END AS geometry
    FROM silver.dim_territory dt
    WHERE dt.level::text = 'municipality'
      AND dt.geometry IS NOT NULL
),
municipality_rollup AS (
    SELECT
        b.reference_period,
        md.territory_id,
        md.territory_name,
        'municipality'::text AS territory_level,
        b.municipality_ibge_code,
        ROUND(AVG(b.hazard_score)::numeric, 2)::double precision AS hazard_score,
        ROUND(
            (
                SUM(COALESCE(b.exposure_score, 0) * GREATEST(COALESCE(b.area_km2, 0), 0))
                / NULLIF(SUM(GREATEST(COALESCE(b.area_km2, 0), 0)), 0)
            )::numeric,
            2
        )::double precision AS exposure_score,
        ROUND(
            (
                (
                    AVG(b.hazard_score) * 0.65
                )
                +
                (
                    (
                        SUM(COALESCE(b.exposure_score, 0) * GREATEST(COALESCE(b.area_km2, 0), 0))
                        / NULLIF(SUM(GREATEST(COALESCE(b.area_km2, 0), 0)), 0)
                    ) * 0.35
                )
            )::numeric,
            2
        )::double precision AS environment_risk_score,
        CASE
            WHEN (
                (
                    AVG(b.hazard_score) * 0.65
                )
                +
                (
                    (
                        SUM(COALESCE(b.exposure_score, 0) * GREATEST(COALESCE(b.area_km2, 0), 0))
                        / NULLIF(SUM(GREATEST(COALESCE(b.area_km2, 0), 0)), 0)
                    ) * 0.35
                )
            ) >= 75 THEN 'critical'
            WHEN (
                (
                    AVG(b.hazard_score) * 0.65
                )
                +
                (
                    (
                        SUM(COALESCE(b.exposure_score, 0) * GREATEST(COALESCE(b.area_km2, 0), 0))
                        / NULLIF(SUM(GREATEST(COALESCE(b.area_km2, 0), 0)), 0)
                    ) * 0.35
                )
            ) >= 55 THEN 'attention'
            ELSE 'stable'
        END AS priority_status,
        SUM(COALESCE(b.area_km2, 0))::double precision AS area_km2,
        SUM(COALESCE(b.road_km, 0))::double precision AS road_km,
        SUM(COALESCE(b.pois_count, 0))::int AS pois_count,
        SUM(COALESCE(b.transport_stops_count, 0))::int AS transport_stops_count,
        (
            SUM(COALESCE(b.road_km, 0))
            / NULLIF(SUM(COALESCE(b.area_km2, 0)), 0)
        )::double precision AS road_density_km_per_km2,
        (
            SUM(COALESCE(b.pois_count, 0))::double precision
            / NULLIF(SUM(COALESCE(b.area_km2, 0)), 0)
        )::double precision AS pois_per_km2,
        (
            SUM(COALESCE(b.transport_stops_count, 0))::double precision
            / NULLIF(SUM(COALESCE(b.area_km2, 0)), 0)
        )::double precision AS transport_stops_per_km2,
        COALESCE(BOOL_OR(b.uses_proxy_allocation), FALSE) AS uses_proxy_allocation,
        'municipality_rollup_from_districts'::text AS allocation_method,
        md.geometry
    FROM base b
    JOIN municipality_dim md
      ON md.municipality_ibge_code = b.municipality_ibge_code
    WHERE b.territory_level = 'district'
    GROUP BY
        b.reference_period,
        md.territory_id,
        md.territory_name,
        b.municipality_ibge_code,
        md.geometry
),
all_levels AS (
    SELECT
        b.reference_period,
        b.territory_id,
        b.territory_name,
        b.territory_level,
        b.municipality_ibge_code,
        b.hazard_score,
        b.exposure_score,
        b.environment_risk_score,
        b.priority_status,
        b.area_km2,
        b.road_km,
        b.pois_count,
        b.transport_stops_count,
        b.road_density_km_per_km2,
        b.pois_per_km2,
        b.transport_stops_per_km2,
        b.uses_proxy_allocation,
        b.allocation_method,
        b.geometry
    FROM base b

    UNION ALL

    SELECT
        mr.reference_period,
        mr.territory_id,
        mr.territory_name,
        mr.territory_level,
        mr.municipality_ibge_code,
        mr.hazard_score,
        mr.exposure_score,
        mr.environment_risk_score,
        mr.priority_status,
        mr.area_km2,
        mr.road_km,
        mr.pois_count,
        mr.transport_stops_count,
        mr.road_density_km_per_km2,
        mr.pois_per_km2,
        mr.transport_stops_per_km2,
        mr.uses_proxy_allocation,
        mr.allocation_method,
        mr.geometry
    FROM municipality_rollup mr
),
municipality_population AS (
    SELECT
        fi.reference_period,
        dt.municipality_ibge_code,
        MAX(fi.value::double precision) AS population_estimated
    FROM silver.fact_indicator fi
    JOIN silver.dim_territory dt ON dt.territory_id = fi.territory_id
    WHERE fi.indicator_code = 'POPULACAO_ESTIMADA'
      AND dt.level::text = 'municipality'
    GROUP BY fi.reference_period, dt.municipality_ibge_code
),
population_bound AS (
    SELECT
        a.reference_period,
        a.territory_id,
        mp.population_estimated,
        ROW_NUMBER() OVER (
            PARTITION BY a.reference_period, a.territory_id
            ORDER BY mp.reference_period DESC
        ) AS row_num
    FROM all_levels a
    LEFT JOIN municipality_population mp
      ON mp.municipality_ibge_code = a.municipality_ibge_code
     AND mp.reference_period <= a.reference_period
),
population_latest AS (
    SELECT
        mp.municipality_ibge_code,
        mp.population_estimated,
        ROW_NUMBER() OVER (
            PARTITION BY mp.municipality_ibge_code
            ORDER BY mp.reference_period DESC
        ) AS row_num
    FROM municipality_population mp
),
with_population AS (
    SELECT
        a.reference_period,
        a.territory_id,
        a.territory_name,
        a.territory_level,
        a.municipality_ibge_code,
        a.hazard_score,
        a.exposure_score,
        a.environment_risk_score,
        a.priority_status,
        a.area_km2,
        a.road_km,
        a.pois_count,
        a.transport_stops_count,
        a.road_density_km_per_km2,
        a.pois_per_km2,
        a.transport_stops_per_km2,
        a.uses_proxy_allocation,
        a.allocation_method,
        a.geometry,
        CASE
            WHEN a.territory_level = 'municipality' THEN
                COALESCE(pb.population_estimated, pl.population_estimated)
            WHEN SUM(COALESCE(a.area_km2, 0)) OVER (
                PARTITION BY a.reference_period, a.municipality_ibge_code, a.territory_level
            ) > 0 THEN
                (
                    COALESCE(pb.population_estimated, pl.population_estimated)
                    *
                    (
                        COALESCE(a.area_km2, 0)
                        / NULLIF(
                            SUM(COALESCE(a.area_km2, 0)) OVER (
                                PARTITION BY a.reference_period, a.municipality_ibge_code, a.territory_level
                            ),
                            0
                        )
                    )
                )
            ELSE NULL
        END::double precision AS population_effective
    FROM all_levels a
    LEFT JOIN population_bound pb
      ON pb.reference_period = a.reference_period
     AND pb.territory_id = a.territory_id
     AND pb.row_num = 1
    LEFT JOIN population_latest pl
      ON pl.municipality_ibge_code = a.municipality_ibge_code
     AND pl.row_num = 1
),
scored AS (
    SELECT
        wp.*,
        CASE
            WHEN COUNT(*) OVER (
                PARTITION BY wp.reference_period, wp.territory_level
            ) > 1 THEN
                ROUND(
                    (
                        PERCENT_RANK() OVER (
                            PARTITION BY wp.reference_period, wp.territory_level
                            ORDER BY COALESCE(wp.environment_risk_score, 0)
                        ) * 100
                    )::numeric,
                    2
                )::double precision
            ELSE 50.0
        END AS risk_percentile,
        DENSE_RANK() OVER (
            PARTITION BY wp.reference_period, wp.territory_level
            ORDER BY COALESCE(wp.environment_risk_score, 0) DESC, wp.territory_name ASC
        )::int AS risk_priority_rank
    FROM with_population wp
)
SELECT
    s.reference_period,
    s.territory_id::text AS territory_id,
    s.territory_name,
    s.territory_level,
    s.municipality_ibge_code,
    s.hazard_score,
    s.exposure_score,
    s.environment_risk_score,
    s.risk_percentile,
    s.risk_priority_rank,
    s.priority_status,
    s.area_km2,
    s.road_km,
    s.pois_count,
    s.transport_stops_count,
    s.road_density_km_per_km2,
    s.pois_per_km2,
    s.transport_stops_per_km2,
    ROUND(s.population_effective::numeric, 2)::double precision AS population_effective,
    CASE
        WHEN COALESCE(s.population_effective, 0) > 0 AND COALESCE(s.area_km2, 0) > 0 THEN
            ROUND((s.population_effective / s.area_km2)::numeric, 2)::double precision
        ELSE NULL
    END AS exposed_population_per_km2,
    s.uses_proxy_allocation,
    s.allocation_method,
    s.geometry,
    NOW() AS refreshed_at_utc
FROM scored s;
