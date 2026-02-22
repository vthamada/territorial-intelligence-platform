CREATE OR REPLACE VIEW gold.mart_priority_drivers AS
WITH score_cfg AS (
    SELECT
        cfg.score_version,
        cfg.config_version,
        cfg.scoring_method,
        cfg.critical_threshold,
        cfg.attention_threshold,
        cfg.default_domain_weight,
        cfg.default_indicator_weight,
        cfg.domain_weights,
        cfg.indicator_weights
    FROM ops.v_strategic_score_version_active cfg

    UNION ALL

    SELECT
        'v1.0.0'::text AS score_version,
        '1.0.0'::text AS config_version,
        'rank_abs_value_v1'::text AS scoring_method,
        80.0::double precision AS critical_threshold,
        50.0::double precision AS attention_threshold,
        1.0::double precision AS default_domain_weight,
        1.0::double precision AS default_indicator_weight,
        '{}'::jsonb AS domain_weights,
        '{}'::jsonb AS indicator_weights
    WHERE NOT EXISTS (SELECT 1 FROM ops.v_strategic_score_version_active)
),
base AS (
    SELECT
        fi.reference_period,
        dt.territory_id::text AS territory_id,
        dt.name AS territory_name,
        dt.level::text AS territory_level,
        CASE
            WHEN fi.source = 'DATASUS' THEN 'saude'
            WHEN fi.source = 'INEP' THEN 'educacao'
            WHEN fi.source = 'MTE' THEN 'trabalho'
            WHEN fi.source = 'SICONFI' THEN 'financas'
            WHEN fi.source = 'TSE' THEN 'eleitorado'
            WHEN fi.source = 'SIDRA' THEN 'socioeconomico'
            WHEN fi.source = 'SENATRAN' THEN 'mobilidade'
            WHEN fi.source = 'SEJUSP_MG' THEN 'seguranca'
            WHEN fi.source = 'SIOPS' THEN 'saude'
            WHEN fi.source = 'SNIS' THEN 'saneamento'
            WHEN fi.source = 'INMET' THEN 'clima'
            WHEN fi.source = 'INPE_QUEIMADAS' THEN 'meio_ambiente'
            WHEN fi.source = 'ANA' THEN 'recursos_hidricos'
            WHEN fi.source = 'ANATEL' THEN 'conectividade'
            WHEN fi.source = 'ANEEL' THEN 'energia'
            WHEN fi.source = 'CECAD' THEN 'assistencia_social'
            WHEN fi.source = 'CENSO_SUAS' THEN 'assistencia_social'
            WHEN fi.source = 'IBGE' THEN 'socioeconomico'
            ELSE 'geral'
        END AS domain,
        fi.indicator_code,
        fi.indicator_name,
        fi.value::double precision AS value,
        fi.unit,
        fi.source,
        fi.dataset,
        fi.updated_at
    FROM silver.fact_indicator fi
    JOIN silver.dim_territory dt ON dt.territory_id = fi.territory_id
    WHERE fi.value IS NOT NULL
),
latest AS (
    SELECT
        b.*,
        ROW_NUMBER() OVER (
            PARTITION BY b.reference_period, b.territory_id, b.indicator_code
            ORDER BY b.updated_at DESC, ABS(b.value) DESC
        ) AS latest_row
    FROM base b
),
dedup AS (
    SELECT
        l.reference_period,
        l.territory_id,
        l.territory_name,
        l.territory_level,
        l.domain,
        l.indicator_code,
        l.indicator_name,
        l.value,
        l.unit,
        l.source,
        l.dataset,
        l.updated_at
    FROM latest l
    WHERE l.latest_row = 1
),
weighted AS (
    SELECT
        d.reference_period,
        d.territory_id,
        d.territory_name,
        d.territory_level,
        d.domain,
        d.indicator_code,
        d.indicator_name,
        d.value,
        d.unit,
        d.source,
        d.dataset,
        d.updated_at,
        cfg.score_version,
        cfg.config_version,
        cfg.scoring_method,
        cfg.critical_threshold,
        cfg.attention_threshold,
        COALESCE(
            NULLIF((cfg.domain_weights ->> d.domain), '')::double precision,
            cfg.default_domain_weight
        ) AS domain_weight,
        COALESCE(
            NULLIF((cfg.indicator_weights ->> d.indicator_code), '')::double precision,
            cfg.default_indicator_weight
        ) AS indicator_weight
    FROM dedup d
    CROSS JOIN score_cfg cfg
),
ranked AS (
    SELECT
        w.*,
        (ABS(w.value) * w.domain_weight * w.indicator_weight)::double precision AS weighted_magnitude,
        ROW_NUMBER() OVER (
            PARTITION BY w.reference_period, w.territory_level, w.domain
            ORDER BY (ABS(w.value) * w.domain_weight * w.indicator_weight) DESC, w.territory_name ASC, w.indicator_code ASC
        )::int AS driver_rank,
        COUNT(*) OVER (
            PARTITION BY w.reference_period, w.territory_level, w.domain
        )::int AS driver_total
    FROM weighted w
),
scored AS (
    SELECT
        r.*,
        ABS(r.value)::double precision AS driver_magnitude,
        CASE
            WHEN r.driver_total <= 1 THEN 50.0
            ELSE ROUND(
                (
                    1 - ((r.driver_rank - 1)::numeric / (r.driver_total - 1))
                ) * 100,
                2
            )::double precision
        END AS priority_score
    FROM ranked r
)
SELECT
    s.reference_period,
    s.territory_id,
    s.territory_name,
    s.territory_level,
    s.domain,
    s.indicator_code,
    s.indicator_name,
    s.value,
    s.unit,
    s.source,
    s.dataset,
    s.updated_at,
    s.driver_rank,
    s.driver_total,
    s.driver_magnitude,
    s.priority_score,
    CASE
        WHEN s.priority_score >= s.critical_threshold THEN 'critical'
        WHEN s.priority_score >= s.attention_threshold THEN 'attention'
        ELSE 'stable'
    END AS priority_status,
    CASE
        WHEN s.driver_total <= 1 THEN 50.0
        ELSE ROUND(
            (
                1 - ((s.driver_rank - 1)::numeric / (s.driver_total - 1))
            ) * 100,
            2
        )::double precision
    END AS driver_percentile,
    s.scoring_method,
    NOW() AS refreshed_at_utc,
    s.score_version,
    s.config_version,
    s.critical_threshold,
    s.attention_threshold,
    s.domain_weight,
    s.indicator_weight,
    s.weighted_magnitude
FROM scored s;
