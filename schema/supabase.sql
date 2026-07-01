-- ============================================================================
-- Supabase Schema for Hombre
-- Run this in the Supabase SQL Editor to set up tables and RLS policies.
-- ============================================================================

-- Soft deletes table
CREATE TABLE IF NOT EXISTS soft_deletes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    resource_type TEXT NOT NULL CHECK (resource_type IN ('peer', 'message', 'conclusion')),
    resource_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(resource_type, resource_id, workspace_id)
);

CREATE INDEX IF NOT EXISTS idx_soft_deletes_type ON soft_deletes(resource_type);
CREATE INDEX IF NOT EXISTS idx_soft_deletes_workspace ON soft_deletes(workspace_id);
CREATE INDEX IF NOT EXISTS idx_soft_deletes_resource ON soft_deletes(resource_type, resource_id, workspace_id);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    type TEXT NOT NULL DEFAULT 'info',
    message TEXT NOT NULL,
    workspace_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    dismissed BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_notifications_workspace ON notifications(workspace_id);
CREATE INDEX IF NOT EXISTS idx_notifications_dismissed ON notifications(dismissed);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    action TEXT NOT NULL,
    username TEXT,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_username ON audit_logs(username);

-- ============================================================================
-- Row Level Security (RLS)
-- ============================================================================

ALTER TABLE soft_deletes ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Policies: service role can do everything, anon can read
-- (service role bypasses RLS by default, but these policies make intent explicit)

CREATE POLICY "Service role can do everything on soft_deletes"
    ON soft_deletes FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Anon can read soft_deletes"
    ON soft_deletes FOR SELECT
    USING (true);

CREATE POLICY "Service role can do everything on notifications"
    ON notifications FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Anon can read notifications"
    ON notifications FOR SELECT
    USING (true);

CREATE POLICY "Service role can do everything on audit_logs"
    ON audit_logs FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Anon can read audit_logs"
    ON audit_logs FOR SELECT
    USING (true);
