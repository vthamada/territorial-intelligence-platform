CREATE TABLE IF NOT EXISTS ops.strategic_score_versions (
    score_version TEXT PRIMARY KEY,
    config_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'deprecated', 'draft')),
    effective_from DATE NOT NULL DEFAULT CURRENT_DATE,
    scoring_method TEXT NOT NULL DEFAULT 'rank_abs_value_v1',
    critical_threshold DOUBLE PRECISION NOT NULL,
    attention_threshold DOUBLE PRECISION NOT NULL,
    default_domain_weight DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    default_indicator_weight DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    domain_weights JSONB NOT NULL DEFAULT '{}'::jsonb,
    indicator_weights JSONB NOT NULL DEFAULT '{}'::jsonb,
    notes TEXT,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_strategic_score_versions_active
    ON ops.strategic_score_versions (status)
    WHERE status = 'active';

CREATE OR REPLACE VIEW ops.v_strategic_score_version_active AS
SELECT
    ssv.score_version,
    ssv.config_version,
    ssv.status,
    ssv.effective_from,
    ssv.scoring_method,
    ssv.critical_threshold,
    ssv.attention_threshold,
    ssv.default_domain_weight,
    ssv.default_indicator_weight,
    ssv.domain_weights,
    ssv.indicator_weights,
    ssv.notes,
    ssv.created_at_utc,
    ssv.updated_at_utc
FROM ops.strategic_score_versions ssv
WHERE ssv.status = 'active'
ORDER BY ssv.effective_from DESC, ssv.updated_at_utc DESC
LIMIT 1;

INSERT INTO ops.strategic_score_versions (
    score_version,
    config_version,
    status,
    effective_from,
    scoring_method,
    critical_threshold,
    attention_threshold,
    default_domain_weight,
    default_indicator_weight,
    domain_weights,
    indicator_weights,
    notes
) VALUES (
    'v1.0.0',
    '1.0.0',
    'active',
    CURRENT_DATE,
    'rank_abs_value_v1',
    80.0,
    50.0,
    1.0,
    1.0,
    '{}'::jsonb,
    '{}'::jsonb,
    'Initial strategic score version seed.'
)
ON CONFLICT (score_version) DO UPDATE SET
    config_version = EXCLUDED.config_version,
    status = EXCLUDED.status,
    effective_from = EXCLUDED.effective_from,
    scoring_method = EXCLUDED.scoring_method,
    critical_threshold = EXCLUDED.critical_threshold,
    attention_threshold = EXCLUDED.attention_threshold,
    default_domain_weight = EXCLUDED.default_domain_weight,
    default_indicator_weight = EXCLUDED.default_indicator_weight,
    domain_weights = EXCLUDED.domain_weights,
    indicator_weights = EXCLUDED.indicator_weights,
    notes = EXCLUDED.notes,
    updated_at_utc = NOW();
