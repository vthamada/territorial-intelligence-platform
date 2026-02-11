CREATE TABLE IF NOT EXISTS ops.frontend_events (
    event_id BIGSERIAL PRIMARY KEY,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    severity TEXT NOT NULL,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    event_timestamp_utc TIMESTAMPTZ NOT NULL,
    received_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    request_id TEXT NULL,
    user_agent TEXT NULL,
    CONSTRAINT ck_frontend_events_category
        CHECK (category IN ('frontend_error', 'web_vital', 'performance', 'lifecycle', 'api_request')),
    CONSTRAINT ck_frontend_events_severity
        CHECK (severity IN ('info', 'warn', 'error'))
);

CREATE INDEX IF NOT EXISTS idx_frontend_events_timestamp
    ON ops.frontend_events (event_timestamp_utc DESC);

CREATE INDEX IF NOT EXISTS idx_frontend_events_category_severity
    ON ops.frontend_events (category, severity);
