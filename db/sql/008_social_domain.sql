CREATE TABLE IF NOT EXISTS silver.fact_social_protection (
    fact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    territory_id UUID NOT NULL REFERENCES silver.dim_territory(territory_id),
    source TEXT NOT NULL,
    dataset TEXT NOT NULL,
    reference_period TEXT NOT NULL,
    households_total NUMERIC NULL,
    people_total NUMERIC NULL,
    avg_income_per_capita NUMERIC NULL,
    poverty_rate NUMERIC NULL,
    extreme_poverty_rate NUMERIC NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fact_social_protection UNIQUE (territory_id, source, dataset, reference_period)
);

CREATE TABLE IF NOT EXISTS silver.fact_social_assistance_network (
    fact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    territory_id UUID NOT NULL REFERENCES silver.dim_territory(territory_id),
    source TEXT NOT NULL,
    dataset TEXT NOT NULL,
    reference_period TEXT NOT NULL,
    cras_units NUMERIC NULL,
    creas_units NUMERIC NULL,
    social_units_total NUMERIC NULL,
    workers_total NUMERIC NULL,
    service_capacity_total NUMERIC NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fact_social_assistance_network UNIQUE (territory_id, source, dataset, reference_period)
);

CREATE INDEX IF NOT EXISTS idx_fact_social_protection_lookup
    ON silver.fact_social_protection (reference_period, territory_id, source);

CREATE INDEX IF NOT EXISTS idx_fact_social_assistance_network_lookup
    ON silver.fact_social_assistance_network (reference_period, territory_id, source);
