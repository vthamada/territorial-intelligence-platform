CREATE OR REPLACE VIEW gold.mart_mobility_access AS
WITH senatran_periods AS (
    SELECT
        fi.reference_period,
        dt.territory_id AS municipality_territory_id,
        dt.municipality_ibge_code,
        MAX(fi.value::double precision) AS fleet_total
    FROM silver.fact_indicator fi
    JOIN silver.dim_territory dt ON dt.territory_id = fi.territory_id
    WHERE fi.source = 'SENATRAN'
      AND fi.indicator_code = 'SENATRAN_FROTA_TOTAL'
      AND dt.level = 'municipality'
    GROUP BY
        fi.reference_period,
        dt.territory_id,
        dt.municipality_ibge_code
),
territories AS (
    SELECT
        dt.territory_id,
        dt.name AS territory_name,
        dt.level::text AS territory_level,
        dt.municipality_ibge_code,
        ST_Transform(dt.geometry::geometry, 4326) AS geom_4326
    FROM silver.dim_territory dt
    WHERE dt.level IN ('municipality', 'district')
      AND dt.geometry IS NOT NULL
),
road_stats AS (
    SELECT
        t.territory_id,
        COUNT(DISTINCT r.road_id)::int AS road_segments_count,
        COALESCE(SUM(ST_Length(ST_Transform(r.geom, 31983))), 0)::double precision AS road_length_m
    FROM territories t
    LEFT JOIN map.urban_road_segment r
        ON ST_Intersects(t.geom_4326, r.geom)
    GROUP BY t.territory_id
),
transport_stats AS (
    SELECT
        t.territory_id,
        COUNT(DISTINCT s.transport_id)::int AS transport_stops_count
    FROM territories t
    LEFT JOIN map.urban_transport_stop s
        ON ST_Intersects(t.geom_4326, s.geom)
    GROUP BY t.territory_id
),
poi_stats AS (
    SELECT
        t.territory_id,
        COUNT(DISTINCT p.poi_id) FILTER (
            WHERE lower(COALESCE(p.category, '')) = 'mobility'
        )::int AS mobility_pois_count
    FROM territories t
    LEFT JOIN map.urban_poi p
        ON ST_Intersects(t.geom_4326, p.geom)
    GROUP BY t.territory_id
),
population_series AS (
    SELECT
        fi.territory_id,
        fi.reference_period,
        fi.value::double precision AS population_estimated
    FROM silver.fact_indicator fi
    WHERE fi.indicator_code = 'POPULACAO_ESTIMADA'
),
population_bound AS (
    SELECT
        sp.reference_period AS target_period,
        sp.municipality_territory_id,
        ps.population_estimated,
        ROW_NUMBER() OVER (
            PARTITION BY sp.reference_period, sp.municipality_territory_id
            ORDER BY ps.reference_period DESC
        ) AS row_num
    FROM senatran_periods sp
    LEFT JOIN population_series ps
        ON ps.territory_id = sp.municipality_territory_id
       AND ps.reference_period <= sp.reference_period
),
municipality_population_bound AS (
    SELECT
        target_period AS reference_period,
        municipality_territory_id,
        population_estimated
    FROM population_bound
    WHERE row_num = 1
),
municipality_population_latest AS (
    SELECT
        ps.territory_id AS municipality_territory_id,
        ps.population_estimated,
        ROW_NUMBER() OVER (
            PARTITION BY ps.territory_id
            ORDER BY ps.reference_period DESC
        ) AS row_num
    FROM population_series ps
),
base AS (
    SELECT
        sp.reference_period,
        t.territory_id,
        t.territory_name,
        t.territory_level,
        t.municipality_ibge_code,
        COALESCE(rs.road_segments_count, 0) AS road_segments_count,
        COALESCE(rs.road_length_m, 0) AS road_length_m,
        COALESCE(ts.transport_stops_count, 0) AS transport_stops_count,
        COALESCE(ps.mobility_pois_count, 0) AS mobility_pois_count,
        sp.fleet_total AS municipality_fleet_total,
        COALESCE(mpb.population_estimated, mpl.population_estimated) AS municipality_population_estimated
    FROM senatran_periods sp
    JOIN territories t
        ON t.municipality_ibge_code = sp.municipality_ibge_code
    LEFT JOIN road_stats rs
        ON rs.territory_id = t.territory_id
    LEFT JOIN transport_stats ts
        ON ts.territory_id = t.territory_id
    LEFT JOIN poi_stats ps
        ON ps.territory_id = t.territory_id
    LEFT JOIN municipality_population_bound mpb
        ON mpb.reference_period = sp.reference_period
       AND mpb.municipality_territory_id = sp.municipality_territory_id
    LEFT JOIN municipality_population_latest mpl
        ON mpl.municipality_territory_id = sp.municipality_territory_id
       AND mpl.row_num = 1
),
allocated AS (
    SELECT
        b.*,
        SUM(
            CASE
                WHEN b.territory_level = 'district' THEN b.road_length_m
                ELSE 0
            END
        ) OVER (
            PARTITION BY b.municipality_ibge_code, b.reference_period
        ) AS district_road_length_total_m
    FROM base b
),
normalized_input AS (
    SELECT
        a.reference_period,
        a.territory_id,
        a.territory_name,
        a.territory_level,
        a.municipality_ibge_code,
        a.road_segments_count,
        a.road_length_m,
        a.transport_stops_count,
        a.mobility_pois_count,
        a.municipality_fleet_total,
        a.municipality_population_estimated,
        CASE
            WHEN a.territory_level = 'municipality' THEN a.municipality_fleet_total
            WHEN a.district_road_length_total_m > 0 THEN
                ROUND((a.municipality_fleet_total * (a.road_length_m / a.district_road_length_total_m))::numeric, 2)::double precision
            ELSE NULL
        END AS fleet_total_effective,
        CASE
            WHEN a.territory_level = 'municipality' THEN a.municipality_population_estimated
            WHEN a.district_road_length_total_m > 0 THEN
                ROUND((a.municipality_population_estimated * (a.road_length_m / a.district_road_length_total_m))::numeric, 2)::double precision
            ELSE NULL
        END AS population_effective,
        CASE
            WHEN a.territory_level = 'district' THEN TRUE
            ELSE FALSE
        END AS uses_proxy_allocation
    FROM allocated a
),
metrics AS (
    SELECT
        n.*,
        (n.road_length_m / 1000.0) AS road_length_km,
        CASE
            WHEN COALESCE(n.population_effective, 0) > 0 THEN
                (n.transport_stops_count * 10000.0) / n.population_effective
            ELSE NULL
        END AS transport_stops_per_10k_pop,
        CASE
            WHEN COALESCE(n.population_effective, 0) > 0 THEN
                ((n.road_length_m / 1000.0) * 10000.0) / n.population_effective
            ELSE NULL
        END AS road_km_per_10k_pop,
        CASE
            WHEN COALESCE(n.population_effective, 0) > 0 THEN
                (n.mobility_pois_count * 10000.0) / n.population_effective
            ELSE NULL
        END AS mobility_pois_per_10k_pop,
        CASE
            WHEN COALESCE(n.population_effective, 0) > 0 THEN
                (n.fleet_total_effective * 1000.0) / n.population_effective
            ELSE NULL
        END AS vehicles_per_1k_pop
    FROM normalized_input n
),
ranked AS (
    SELECT
        m.*,
        CASE
            WHEN COUNT(*) OVER (PARTITION BY m.reference_period, m.territory_level) > 1 THEN
                PERCENT_RANK() OVER (
                    PARTITION BY m.reference_period, m.territory_level
                    ORDER BY COALESCE(m.transport_stops_per_10k_pop, 0)
                )
            ELSE 0.5
        END AS p_transport_stops,
        CASE
            WHEN COUNT(*) OVER (PARTITION BY m.reference_period, m.territory_level) > 1 THEN
                PERCENT_RANK() OVER (
                    PARTITION BY m.reference_period, m.territory_level
                    ORDER BY COALESCE(m.road_km_per_10k_pop, 0)
                )
            ELSE 0.5
        END AS p_road_density,
        CASE
            WHEN COUNT(*) OVER (PARTITION BY m.reference_period, m.territory_level) > 1 THEN
                PERCENT_RANK() OVER (
                    PARTITION BY m.reference_period, m.territory_level
                    ORDER BY COALESCE(m.mobility_pois_per_10k_pop, 0)
                )
            ELSE 0.5
        END AS p_mobility_pois
    FROM metrics m
),
scored AS (
    SELECT
        r.*,
        ROUND((
            (
                (COALESCE(r.p_transport_stops, 0) * 0.45) +
                (COALESCE(r.p_road_density, 0) * 0.35) +
                (COALESCE(r.p_mobility_pois, 0) * 0.20)
            ) * 100.0
        )::numeric, 2)::double precision AS mobility_access_score
    FROM ranked r
)
SELECT
    s.reference_period,
    s.territory_id,
    s.territory_name,
    s.territory_level,
    s.municipality_ibge_code,
    s.road_segments_count,
    s.road_length_km,
    s.transport_stops_count,
    s.mobility_pois_count,
    s.fleet_total_effective,
    s.population_effective,
    s.vehicles_per_1k_pop,
    s.transport_stops_per_10k_pop,
    s.road_km_per_10k_pop,
    s.mobility_pois_per_10k_pop,
    s.mobility_access_score,
    ROUND((100.0 - s.mobility_access_score)::numeric, 2)::double precision AS mobility_access_deficit_score,
    CASE
        WHEN (100.0 - s.mobility_access_score) >= 75 THEN 'critical'
        WHEN (100.0 - s.mobility_access_score) >= 50 THEN 'attention'
        ELSE 'stable'
    END AS priority_status,
    s.uses_proxy_allocation,
    CASE
        WHEN s.uses_proxy_allocation THEN
            'district_allocation_by_road_length_share'
        ELSE
            'direct_measurement'
    END AS allocation_method,
    NOW() AS refreshed_at_utc
FROM scored s;
