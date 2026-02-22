CREATE TABLE IF NOT EXISTS map.urban_transport_stop (
    transport_id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NULL,
    name TEXT NULL,
    mode TEXT NULL,
    operator TEXT NULL,
    is_accessible BOOLEAN NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(Point, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_urban_transport_stop_source_external
    ON map.urban_transport_stop (source, external_id)
    WHERE external_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_urban_transport_stop_mode
    ON map.urban_transport_stop (mode);
CREATE INDEX IF NOT EXISTS idx_urban_transport_stop_geom_gist
    ON map.urban_transport_stop USING GIST (geom);

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
VALUES (
    'urban_transport_stops',
    'Paradas e estacoes de transporte',
    'urban',
    FALSE,
    'map.urban_transport_stop',
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

CREATE OR REPLACE VIEW map.v_urban_data_coverage AS
SELECT
    'urban_road_segment'::text AS dataset,
    COUNT(*)::bigint AS rows,
    MIN(created_at) AS first_seen_at_utc,
    MAX(updated_at) AS last_seen_at_utc
FROM map.urban_road_segment
UNION ALL
SELECT
    'urban_poi'::text AS dataset,
    COUNT(*)::bigint AS rows,
    MIN(created_at) AS first_seen_at_utc,
    MAX(updated_at) AS last_seen_at_utc
FROM map.urban_poi
UNION ALL
SELECT
    'urban_transport_stop'::text AS dataset,
    COUNT(*)::bigint AS rows,
    MIN(created_at) AS first_seen_at_utc,
    MAX(updated_at) AS last_seen_at_utc
FROM map.urban_transport_stop;
