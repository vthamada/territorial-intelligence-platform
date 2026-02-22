CREATE TABLE IF NOT EXISTS ops.robustness_window_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    generated_at_utc TIMESTAMPTZ NOT NULL,
    window_days INTEGER NOT NULL CHECK (window_days >= 1),
    health_window_days INTEGER NOT NULL CHECK (health_window_days >= 1),
    slo1_target_pct DOUBLE PRECISION NOT NULL CHECK (slo1_target_pct >= 0 AND slo1_target_pct <= 100),
    include_blocked_as_success BOOLEAN NOT NULL DEFAULT TRUE,
    strict BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL CHECK (status IN ('READY', 'NOT_READY')),
    severity TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'normal')),
    gates_all_pass BOOLEAN NOT NULL,
    payload JSONB NOT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_robustness_snapshots_generated
    ON ops.robustness_window_snapshots (generated_at_utc DESC, snapshot_id DESC);

CREATE INDEX IF NOT EXISTS idx_robustness_snapshots_filters
    ON ops.robustness_window_snapshots (status, severity, window_days, strict);

CREATE OR REPLACE VIEW ops.v_robustness_window_snapshot_latest AS
SELECT
    s.snapshot_id,
    s.generated_at_utc,
    s.window_days,
    s.health_window_days,
    s.slo1_target_pct,
    s.include_blocked_as_success,
    s.strict,
    s.status,
    s.severity,
    s.gates_all_pass,
    s.payload
FROM ops.robustness_window_snapshots s
JOIN (
    SELECT
        window_days,
        strict,
        MAX(generated_at_utc) AS generated_at_utc
    FROM ops.robustness_window_snapshots
    GROUP BY window_days, strict
) latest
  ON latest.window_days = s.window_days
 AND latest.strict = s.strict
 AND latest.generated_at_utc = s.generated_at_utc;
