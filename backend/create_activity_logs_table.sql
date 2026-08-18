-- ================================================
-- PharmaCast: activity_logs table for Supabase
-- Run this SQL in Supabase Dashboard > SQL Editor
-- ================================================

CREATE TABLE IF NOT EXISTS activity_logs (
    id          BIGSERIAL PRIMARY KEY,
    event_type  TEXT        NOT NULL DEFAULT 'INFO',
    username    TEXT        NOT NULL DEFAULT 'system',
    user_role   TEXT        NOT NULL DEFAULT 'SYSTEM',
    message     TEXT        NOT NULL DEFAULT '',
    detail      TEXT                 DEFAULT '',
    status      TEXT        NOT NULL DEFAULT 'INFO',
    ip_address  TEXT                 DEFAULT '',
    user_agent  TEXT                 DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast time-based and type-based queries
CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at  ON activity_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_logs_event_type  ON activity_logs (event_type);
CREATE INDEX IF NOT EXISTS idx_activity_logs_username    ON activity_logs (username);
CREATE INDEX IF NOT EXISTS idx_activity_logs_status      ON activity_logs (status);

-- RLS: Only admin users (authenticated service role) can read
-- Frontend writes are done via the backend API which uses the service key
-- so public writes should remain disabled for security.
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;

-- Allow service_role (backend) to do all operations
CREATE POLICY IF NOT EXISTS "service_role_full_access"
ON activity_logs FOR ALL
TO service_role
USING (true) WITH CHECK (true);

-- Deny all access to anon / public (all writes go through backend API)
-- No SELECT policy for anon means anon cannot read logs.

COMMENT ON TABLE activity_logs IS 'System-wide activity audit log for PharmaCast — logins, logouts, API calls, errors, admin actions, simulation events.';
