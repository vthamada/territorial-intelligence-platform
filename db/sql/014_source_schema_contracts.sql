CREATE TABLE IF NOT EXISTS ops.source_schema_contracts (
    contract_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    connector_name TEXT NOT NULL,
    source TEXT NOT NULL,
    dataset TEXT NOT NULL,
    target_table TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    effective_from DATE NOT NULL DEFAULT CURRENT_DATE,
    status TEXT NOT NULL DEFAULT 'active',
    required_columns JSONB NOT NULL DEFAULT '[]'::jsonb,
    optional_columns JSONB NOT NULL DEFAULT '[]'::jsonb,
    column_types JSONB NOT NULL DEFAULT '{}'::jsonb,
    constraints_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_uri TEXT NULL,
    notes TEXT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_source_schema_contract_status
        CHECK (status IN ('active', 'deprecated')),
    CONSTRAINT uq_source_schema_contract_version
        UNIQUE (connector_name, target_table, schema_version)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_source_schema_contract_active
    ON ops.source_schema_contracts (connector_name, target_table)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_source_schema_contract_source_dataset
    ON ops.source_schema_contracts (source, dataset, status);

CREATE OR REPLACE VIEW ops.v_source_schema_contracts_active AS
SELECT
    connector_name,
    source,
    dataset,
    target_table,
    schema_version,
    effective_from,
    required_columns,
    optional_columns,
    column_types,
    constraints_json,
    source_uri,
    notes,
    updated_at_utc
FROM ops.source_schema_contracts
WHERE status = 'active';
