CREATE OR REPLACE VIEW map.v_environment_risk_aggregation AS
WITH municipality_environment AS (
    SELECT
        fi.reference_period,
        MAX(CASE WHEN fi.indicator_code = 'INMET_PRECIPITACAO_TOTAL_MM' THEN fi.value::double precision END) AS inmet_precip_total_mm,
        MAX(CASE WHEN fi.indicator_code = 'INMET_TEMPERATURA_MEDIA_C' THEN fi.value::double precision END) AS inmet_temp_avg_c,
        MAX(CASE WHEN fi.indicator_code = 'INPE_FOCOS_QUEIMADAS_TOTAL' THEN fi.value::double precision END) AS inpe_fire_hotspots_total,
        MAX(CASE WHEN fi.indicator_code = 'INPE_AREA_QUEIMADA_HA' THEN fi.value::double precision END) AS inpe_burned_area_ha,
        MAX(CASE WHEN fi.indicator_code = 'INPE_RISCO_FOGO_INDICE' THEN fi.value::double precision END) AS inpe_fire_risk_index,
        MAX(CASE WHEN fi.indicator_code = 'ANA_VAZAO_MEDIA_M3S' THEN fi.value::double precision END) AS ana_avg_flow_m3s,
        MAX(CASE WHEN fi.indicator_code = 'ANA_NIVEL_MEDIO_M' THEN fi.value::double precision END) AS ana_avg_level_m
    FROM silver.fact_indicator fi
    JOIN silver.dim_territory dt ON dt.territory_id = fi.territory_id
    WHERE dt.level::text = 'municipality'
      AND fi.source IN ('INMET', 'INPE_QUEIMADAS', 'ANA')
    GROUP BY fi.reference_period
),
hazard_norm AS (
    SELECT
        me.reference_period,
        me.inmet_precip_total_mm,
        me.inmet_temp_avg_c,
        me.inpe_fire_hotspots_total,
        me.inpe_burned_area_ha,
        me.inpe_fire_risk_index,
        me.ana_avg_flow_m3s,
        me.ana_avg_level_m,
        COALESCE(
            CASE
                WHEN MAX(me.inmet_precip_total_mm) OVER () > MIN(me.inmet_precip_total_mm) OVER () THEN
                    (me.inmet_precip_total_mm - MIN(me.inmet_precip_total_mm) OVER ())
                    / NULLIF(MAX(me.inmet_precip_total_mm) OVER () - MIN(me.inmet_precip_total_mm) OVER (), 0)
            END,
            0.5
        ) AS inmet_precip_norm,
        COALESCE(
            CASE
                WHEN MAX(me.inmet_temp_avg_c) OVER () > MIN(me.inmet_temp_avg_c) OVER () THEN
                    (me.inmet_temp_avg_c - MIN(me.inmet_temp_avg_c) OVER ())
                    / NULLIF(MAX(me.inmet_temp_avg_c) OVER () - MIN(me.inmet_temp_avg_c) OVER (), 0)
            END,
            0.5
        ) AS inmet_temp_norm,
        COALESCE(
            CASE
                WHEN MAX(me.inpe_fire_hotspots_total) OVER () > MIN(me.inpe_fire_hotspots_total) OVER () THEN
                    (me.inpe_fire_hotspots_total - MIN(me.inpe_fire_hotspots_total) OVER ())
                    / NULLIF(MAX(me.inpe_fire_hotspots_total) OVER () - MIN(me.inpe_fire_hotspots_total) OVER (), 0)
            END,
            0.5
        ) AS inpe_hotspots_norm,
        COALESCE(
            CASE
                WHEN MAX(me.inpe_burned_area_ha) OVER () > MIN(me.inpe_burned_area_ha) OVER () THEN
                    (me.inpe_burned_area_ha - MIN(me.inpe_burned_area_ha) OVER ())
                    / NULLIF(MAX(me.inpe_burned_area_ha) OVER () - MIN(me.inpe_burned_area_ha) OVER (), 0)
            END,
            0.5
        ) AS inpe_burned_area_norm,
        COALESCE(
            CASE
                WHEN MAX(me.inpe_fire_risk_index) OVER () > MIN(me.inpe_fire_risk_index) OVER () THEN
                    (me.inpe_fire_risk_index - MIN(me.inpe_fire_risk_index) OVER ())
                    / NULLIF(MAX(me.inpe_fire_risk_index) OVER () - MIN(me.inpe_fire_risk_index) OVER (), 0)
            END,
            0.5
        ) AS inpe_fire_risk_norm,
        COALESCE(
            CASE
                WHEN MAX(me.ana_avg_flow_m3s) OVER () > MIN(me.ana_avg_flow_m3s) OVER () THEN
                    (me.ana_avg_flow_m3s - MIN(me.ana_avg_flow_m3s) OVER ())
                    / NULLIF(MAX(me.ana_avg_flow_m3s) OVER () - MIN(me.ana_avg_flow_m3s) OVER (), 0)
            END,
            0.5
        ) AS ana_flow_norm,
        COALESCE(
            CASE
                WHEN MAX(me.ana_avg_level_m) OVER () > MIN(me.ana_avg_level_m) OVER () THEN
                    (me.ana_avg_level_m - MIN(me.ana_avg_level_m) OVER ())
                    / NULLIF(MAX(me.ana_avg_level_m) OVER () - MIN(me.ana_avg_level_m) OVER (), 0)
            END,
            0.5
        ) AS ana_level_norm
    FROM municipality_environment me
),
hazard_score AS (
    SELECT
        reference_period,
        ROUND(
            ((
                (inmet_precip_norm * 0.17)
                + (inmet_temp_norm * 0.14)
                + (inpe_hotspots_norm * 0.20)
                + (inpe_burned_area_norm * 0.12)
                + (inpe_fire_risk_norm * 0.17)
                + (ana_flow_norm * 0.10)
                + (ana_level_norm * 0.10)
            ) * 100)::numeric,
            2
        )::double precision AS hazard_score
    FROM hazard_norm
),
territory_base AS (
    SELECT
        dt.territory_id,
        dt.name AS territory_name,
        dt.level::text AS territory_level,
        dt.municipality_ibge_code,
        (ST_Area(dt.geometry::geography) / 1000000.0)::double precision AS area_km2,
        CASE
            WHEN ST_SRID(dt.geometry) = 4326 THEN
                CASE WHEN ST_IsValid(dt.geometry) THEN dt.geometry ELSE ST_MakeValid(dt.geometry) END
            ELSE
                ST_Transform(
                    CASE WHEN ST_IsValid(dt.geometry) THEN dt.geometry ELSE ST_MakeValid(dt.geometry) END,
                    4326
                )
        END AS geom,
        COALESCE(ST_SRID(dt.geometry), 4326) AS source_srid
    FROM silver.dim_territory dt
    WHERE dt.level::text IN ('district', 'census_sector')
      AND dt.geometry IS NOT NULL
),
territory_roads AS (
    SELECT
        tb.territory_id,
        COALESCE(
            SUM(ST_Length(ST_Transform(r.geom, 31983))) / 1000.0,
            0
        )::double precision AS road_km
    FROM territory_base tb
    LEFT JOIN map.urban_road_segment r
        ON r.geom IS NOT NULL
       AND ST_Contains(
            tb.geom,
            ST_LineInterpolatePoint(
                CASE
                    WHEN ST_SRID(r.geom) = 4326 THEN r.geom
                    ELSE ST_Transform(r.geom, 4326)
                END,
                0.5
            )
        )
    GROUP BY tb.territory_id
),
territory_pois AS (
    SELECT
        tb.territory_id,
        COUNT(p.poi_id)::int AS pois_count
    FROM territory_base tb
    LEFT JOIN map.urban_poi p
        ON p.geom IS NOT NULL
       AND ST_Contains(
            tb.geom,
            CASE
                WHEN ST_SRID(p.geom) = 4326 THEN p.geom
                ELSE ST_Transform(p.geom, 4326)
            END
        )
    GROUP BY tb.territory_id
),
territory_transport AS (
    SELECT
        tb.territory_id,
        COUNT(t.transport_id)::int AS transport_stops_count
    FROM territory_base tb
    LEFT JOIN map.urban_transport_stop t
        ON t.geom IS NOT NULL
       AND ST_Contains(
            tb.geom,
            CASE
                WHEN ST_SRID(t.geom) = 4326 THEN t.geom
                ELSE ST_Transform(t.geom, 4326)
            END
        )
    GROUP BY tb.territory_id
),
exposure_raw AS (
    SELECT
        tb.territory_id,
        tb.territory_name,
        tb.territory_level,
        tb.municipality_ibge_code,
        tb.geom,
        tb.area_km2,
        COALESCE(tr.road_km, 0)::double precision AS road_km,
        COALESCE(tp.pois_count, 0)::int AS pois_count,
        COALESCE(tt.transport_stops_count, 0)::int AS transport_stops_count,
        (COALESCE(tr.road_km, 0) / NULLIF(tb.area_km2, 0))::double precision AS road_density_km_per_km2,
        (COALESCE(tp.pois_count, 0)::double precision / NULLIF(tb.area_km2, 0))::double precision AS pois_per_km2,
        (COALESCE(tt.transport_stops_count, 0)::double precision / NULLIF(tb.area_km2, 0))::double precision AS transport_stops_per_km2
    FROM territory_base tb
    LEFT JOIN territory_roads tr ON tr.territory_id = tb.territory_id
    LEFT JOIN territory_pois tp ON tp.territory_id = tb.territory_id
    LEFT JOIN territory_transport tt ON tt.territory_id = tb.territory_id
),
exposure_norm AS (
    SELECT
        er.*,
        COALESCE(
            CASE
                WHEN MAX(er.road_density_km_per_km2) OVER (PARTITION BY er.territory_level)
                    > MIN(er.road_density_km_per_km2) OVER (PARTITION BY er.territory_level)
                THEN
                    (er.road_density_km_per_km2 - MIN(er.road_density_km_per_km2) OVER (PARTITION BY er.territory_level))
                    / NULLIF(
                        MAX(er.road_density_km_per_km2) OVER (PARTITION BY er.territory_level)
                        - MIN(er.road_density_km_per_km2) OVER (PARTITION BY er.territory_level),
                        0
                    )
            END,
            0.5
        ) AS road_norm,
        COALESCE(
            CASE
                WHEN MAX(er.pois_per_km2) OVER (PARTITION BY er.territory_level)
                    > MIN(er.pois_per_km2) OVER (PARTITION BY er.territory_level)
                THEN
                    (er.pois_per_km2 - MIN(er.pois_per_km2) OVER (PARTITION BY er.territory_level))
                    / NULLIF(
                        MAX(er.pois_per_km2) OVER (PARTITION BY er.territory_level)
                        - MIN(er.pois_per_km2) OVER (PARTITION BY er.territory_level),
                        0
                    )
            END,
            0.5
        ) AS pois_norm,
        COALESCE(
            CASE
                WHEN MAX(er.transport_stops_per_km2) OVER (PARTITION BY er.territory_level)
                    > MIN(er.transport_stops_per_km2) OVER (PARTITION BY er.territory_level)
                THEN
                    (er.transport_stops_per_km2 - MIN(er.transport_stops_per_km2) OVER (PARTITION BY er.territory_level))
                    / NULLIF(
                        MAX(er.transport_stops_per_km2) OVER (PARTITION BY er.territory_level)
                        - MIN(er.transport_stops_per_km2) OVER (PARTITION BY er.territory_level),
                        0
                    )
            END,
            0.5
        ) AS transport_norm
    FROM exposure_raw er
),
exposure_score AS (
    SELECT
        territory_id,
        territory_name,
        territory_level,
        municipality_ibge_code,
        geom,
        area_km2,
        road_km,
        pois_count,
        transport_stops_count,
        road_density_km_per_km2,
        pois_per_km2,
        transport_stops_per_km2,
        ROUND(
            (((road_norm * 0.45) + (pois_norm * 0.30) + (transport_norm * 0.25)) * 100)::numeric,
            2
        )::double precision AS exposure_score,
        CASE
            WHEN COALESCE(road_km, 0) = 0
             AND COALESCE(pois_count, 0) = 0
             AND COALESCE(transport_stops_count, 0) = 0
            THEN true
            ELSE false
        END AS uses_proxy_allocation
    FROM exposure_norm
)
SELECT
    hs.reference_period,
    es.territory_id,
    es.territory_name,
    es.territory_level,
    es.municipality_ibge_code,
    hs.hazard_score,
    es.exposure_score,
    ROUND(
        ((hs.hazard_score * 0.65) + (es.exposure_score * 0.35))::numeric,
        2
    )::double precision AS environment_risk_score,
    CASE
        WHEN ((hs.hazard_score * 0.65) + (es.exposure_score * 0.35)) >= 75 THEN 'critical'
        WHEN ((hs.hazard_score * 0.65) + (es.exposure_score * 0.35)) >= 55 THEN 'attention'
        ELSE 'stable'
    END AS priority_status,
    es.area_km2,
    es.road_km,
    es.pois_count,
    es.transport_stops_count,
    es.road_density_km_per_km2,
    es.pois_per_km2,
    es.transport_stops_per_km2,
    es.uses_proxy_allocation,
    CASE
        WHEN es.uses_proxy_allocation THEN 'fallback_equal_exposure'
        ELSE 'spatial_exposure_proxy'
    END AS allocation_method,
    es.geom AS geometry
FROM hazard_score hs
CROSS JOIN exposure_score es;
