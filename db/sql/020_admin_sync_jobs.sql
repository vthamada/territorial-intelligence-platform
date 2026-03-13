CREATE TABLE IF NOT EXISTS ops.admin_sync_jobs (
    job_id UUID PRIMARY KEY,
    mode TEXT NOT NULL CHECK (mode IN ('validate', 'sync')),
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'success', 'failed')),
    started_at_utc TIMESTAMPTZ NOT NULL,
    finished_at_utc TIMESTAMPTZ NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    current_step TEXT NULL,
    last_message TEXT NULL,
    recent_logs JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ops.admin_sync_job_steps (
    job_id UUID NOT NULL REFERENCES ops.admin_sync_jobs(job_id) ON DELETE CASCADE,
    step_name TEXT NOT NULL,
    step_order INTEGER NOT NULL CHECK (step_order >= 1),
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'success', 'failed')),
    started_at_utc TIMESTAMPTZ NULL,
    finished_at_utc TIMESTAMPTZ NULL,
    exit_code INTEGER NULL,
    summary TEXT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (job_id, step_name)
);

CREATE INDEX IF NOT EXISTS idx_admin_sync_jobs_started
    ON ops.admin_sync_jobs (started_at_utc DESC, job_id DESC);

CREATE INDEX IF NOT EXISTS idx_admin_sync_jobs_status
    ON ops.admin_sync_jobs (status, mode, is_active);

CREATE INDEX IF NOT EXISTS idx_admin_sync_job_steps_job_order
    ON ops.admin_sync_job_steps (job_id, step_order);
