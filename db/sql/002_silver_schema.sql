CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS ops;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'territory_level'
          AND n.nspname = 'silver'
    ) THEN
        CREATE TYPE silver.territory_level AS ENUM (
            'municipality',
            'district',
            'census_sector',
            'electoral_zone',
            'electoral_section'
        );
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'connector_status'
          AND n.nspname = 'ops'
    ) THEN
        CREATE TYPE ops.connector_status AS ENUM (
            'implemented',
            'partial',
            'blocked',
            'planned'
        );
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS silver.dim_territory (
    territory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level silver.territory_level NOT NULL,
    parent_territory_id UUID NULL REFERENCES silver.dim_territory(territory_id),
    canonical_key TEXT NOT NULL UNIQUE,
    source_system TEXT NOT NULL,
    source_entity_id TEXT NOT NULL,
    ibge_geocode TEXT NULL,
    tse_zone TEXT NULL,
    tse_section TEXT NULL,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    uf TEXT NULL,
    municipality_ibge_code TEXT NOT NULL,
    valid_from DATE NULL,
    valid_to DATE NULL,
    geometry GEOMETRY(Geometry, 4674) NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_dim_territory_identity UNIQUE (level, ibge_geocode, tse_zone, tse_section, municipality_ibge_code),
    CONSTRAINT uq_dim_territory_source UNIQUE (source_system, source_entity_id, municipality_ibge_code)
);

CREATE TABLE IF NOT EXISTS silver.dim_time (
    date_id DATE PRIMARY KEY,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    reference_period TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS silver.fact_indicator (
    fact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    territory_id UUID NOT NULL REFERENCES silver.dim_territory(territory_id),
    source TEXT NOT NULL,
    dataset TEXT NOT NULL,
    indicator_code TEXT NOT NULL,
    indicator_name TEXT NOT NULL,
    unit TEXT NULL,
    category TEXT NULL,
    value NUMERIC NOT NULL,
    reference_period TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fact_indicator UNIQUE (territory_id, source, dataset, indicator_code, category, reference_period)
);

CREATE TABLE IF NOT EXISTS silver.fact_electorate (
    fact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    territory_id UUID NOT NULL REFERENCES silver.dim_territory(territory_id),
    reference_year INTEGER NOT NULL,
    sex TEXT NULL,
    age_range TEXT NULL,
    education TEXT NULL,
    voters INTEGER NOT NULL CHECK (voters >= 0),
    CONSTRAINT uq_fact_electorate UNIQUE (territory_id, reference_year, sex, age_range, education)
);

CREATE TABLE IF NOT EXISTS silver.fact_election_result (
    fact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    territory_id UUID NOT NULL REFERENCES silver.dim_territory(territory_id),
    election_year INTEGER NOT NULL,
    election_round INTEGER NULL,
    office TEXT NULL,
    metric TEXT NOT NULL,
    value NUMERIC NOT NULL CHECK (value >= 0),
    CONSTRAINT uq_fact_election_result UNIQUE (territory_id, election_year, election_round, office, metric)
);

CREATE TABLE IF NOT EXISTS ops.pipeline_runs (
    run_id UUID PRIMARY KEY,
    job_name TEXT NOT NULL,
    source TEXT NULL,
    dataset TEXT NULL,
    wave TEXT NULL,
    reference_period TEXT NULL,
    started_at_utc TIMESTAMPTZ NOT NULL,
    finished_at_utc TIMESTAMPTZ NULL,
    duration_seconds NUMERIC NULL,
    status TEXT NOT NULL,
    rows_extracted BIGINT NOT NULL DEFAULT 0,
    rows_loaded BIGINT NOT NULL DEFAULT 0,
    warnings_count INT NOT NULL DEFAULT 0,
    errors_count INT NOT NULL DEFAULT 0,
    bronze_path TEXT NULL,
    manifest_path TEXT NULL,
    checksum_sha256 TEXT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS ops.pipeline_checks (
    check_id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES ops.pipeline_runs(run_id) ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    details TEXT NOT NULL,
    observed_value NUMERIC NULL,
    threshold_value NUMERIC NULL,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ops.connector_registry (
    connector_name TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    wave TEXT NOT NULL,
    status ops.connector_status NOT NULL,
    notes TEXT NULL,
    updated_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'silver'
          AND c.relname = 'dim_territorio'
          AND c.relkind = 'r'
    ) THEN
        ALTER TABLE silver.dim_territorio RENAME TO dim_territorio_legacy;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'silver'
          AND c.relname = 'dim_tempo'
          AND c.relkind = 'r'
    ) THEN
        ALTER TABLE silver.dim_tempo RENAME TO dim_tempo_legacy;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'silver'
          AND c.relname = 'fact_indicador'
          AND c.relkind = 'r'
    ) THEN
        ALTER TABLE silver.fact_indicador RENAME TO fact_indicador_legacy;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'silver'
          AND c.relname = 'fact_eleitorado'
          AND c.relkind = 'r'
    ) THEN
        ALTER TABLE silver.fact_eleitorado RENAME TO fact_eleitorado_legacy;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'silver'
          AND c.relname = 'fact_resultado_eleitoral'
          AND c.relkind = 'r'
    ) THEN
        ALTER TABLE silver.fact_resultado_eleitoral RENAME TO fact_resultado_eleitoral_legacy;
    END IF;
END
$$;

CREATE OR REPLACE VIEW silver.dim_territorio AS
SELECT
    territory_id,
    CASE level
        WHEN 'municipality' THEN 'municipio'
        WHEN 'district' THEN 'distrito'
        WHEN 'census_sector' THEN 'setor_censitario'
        WHEN 'electoral_zone' THEN 'zona_eleitoral'
        WHEN 'electoral_section' THEN 'secao_eleitoral'
    END AS level,
    parent_territory_id,
    ibge_geocode,
    tse_zone,
    tse_section,
    name,
    uf,
    municipality_ibge_code AS municipality_ibge_geocode,
    valid_from,
    valid_to,
    geometry
FROM silver.dim_territory;

CREATE OR REPLACE VIEW silver.dim_tempo AS
SELECT * FROM silver.dim_time;

CREATE OR REPLACE VIEW silver.fact_indicador AS
SELECT * FROM silver.fact_indicator;

CREATE OR REPLACE VIEW silver.fact_eleitorado AS
SELECT * FROM silver.fact_electorate;

CREATE OR REPLACE VIEW silver.fact_resultado_eleitoral AS
SELECT * FROM silver.fact_election_result;
