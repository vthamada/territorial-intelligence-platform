CREATE TABLE IF NOT EXISTS ops.strategic_score_version_audit (
    audit_id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL CHECK (event_type IN ('insert', 'update', 'delete')),
    score_version TEXT NOT NULL,
    changed_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    changed_by TEXT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.user', true), ''), CURRENT_USER),
    old_row JSONB,
    new_row JSONB,
    changed_fields TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    weights_changed BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_strategic_score_version_audit_score_version
    ON ops.strategic_score_version_audit (score_version, changed_at_utc DESC);

CREATE INDEX IF NOT EXISTS idx_strategic_score_version_audit_weights_changed
    ON ops.strategic_score_version_audit (weights_changed, changed_at_utc DESC);

CREATE OR REPLACE FUNCTION ops.fn_audit_strategic_score_versions()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    old_payload JSONB := to_jsonb(OLD);
    new_payload JSONB := to_jsonb(NEW);
    changed_cols TEXT[] := ARRAY[]::TEXT[];
BEGIN
    IF TG_OP = 'INSERT' THEN
        changed_cols := ARRAY(SELECT jsonb_object_keys(new_payload));
    ELSIF TG_OP = 'UPDATE' THEN
        changed_cols := ARRAY(
            SELECT COALESCE(n.key, o.key)
            FROM jsonb_each(new_payload) n
            FULL OUTER JOIN jsonb_each(old_payload) o ON n.key = o.key
            WHERE n.value IS DISTINCT FROM o.value
            ORDER BY COALESCE(n.key, o.key)
        );
    ELSE
        changed_cols := ARRAY(SELECT jsonb_object_keys(old_payload));
    END IF;

    INSERT INTO ops.strategic_score_version_audit (
        event_type,
        score_version,
        changed_by,
        old_row,
        new_row,
        changed_fields,
        weights_changed
    )
    VALUES (
        LOWER(TG_OP),
        COALESCE(NEW.score_version, OLD.score_version),
        COALESCE(NULLIF(current_setting('app.user', true), ''), CURRENT_USER),
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN old_payload ELSE NULL END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN new_payload ELSE NULL END,
        changed_cols,
        CASE
            WHEN TG_OP IN ('INSERT', 'DELETE') THEN TRUE
            ELSE (
                NEW.default_domain_weight IS DISTINCT FROM OLD.default_domain_weight
                OR NEW.default_indicator_weight IS DISTINCT FROM OLD.default_indicator_weight
                OR NEW.domain_weights IS DISTINCT FROM OLD.domain_weights
                OR NEW.indicator_weights IS DISTINCT FROM OLD.indicator_weights
                OR NEW.scoring_method IS DISTINCT FROM OLD.scoring_method
                OR NEW.critical_threshold IS DISTINCT FROM OLD.critical_threshold
                OR NEW.attention_threshold IS DISTINCT FROM OLD.attention_threshold
            )
        END
    );

    RETURN COALESCE(NEW, OLD);
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_strategic_score_versions ON ops.strategic_score_versions;
CREATE TRIGGER trg_audit_strategic_score_versions
AFTER INSERT OR UPDATE OR DELETE ON ops.strategic_score_versions
FOR EACH ROW
EXECUTE FUNCTION ops.fn_audit_strategic_score_versions();
