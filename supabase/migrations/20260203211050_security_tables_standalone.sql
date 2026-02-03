/*
  # Security Features - Standalone Tables

  Creates security tables that can work independently:
  - User consent management
  - Consent history tracking
  - Data access audit log
  - Scheduled deletions
  - Comprehensive audit logs

  Note: These tables are created without foreign key constraints
  to users table since it may not exist yet.
*/

-- User consent management
CREATE TABLE IF NOT EXISTS user_consent (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  marketing_emails BOOLEAN DEFAULT FALSE,
  data_analytics BOOLEAN DEFAULT TRUE,
  third_party_sharing BOOLEAN DEFAULT FALSE,
  cookie_consent BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE user_consent ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own consent"
  ON user_consent FOR SELECT
  TO authenticated
  USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own consent"
  ON user_consent FOR UPDATE
  TO authenticated
  USING (auth.uid()::text = user_id::text)
  WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can insert own consent"
  ON user_consent FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid()::text = user_id::text);

-- Consent history tracking
CREATE TABLE IF NOT EXISTS consent_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  consent_type TEXT NOT NULL,
  value BOOLEAN NOT NULL,
  changed_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE consent_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own consent history"
  ON consent_history FOR SELECT
  TO authenticated
  USING (auth.uid()::text = user_id::text);

CREATE POLICY "System can insert consent history"
  ON consent_history FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- Data access audit log
CREATE TABLE IF NOT EXISTS data_access_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID,
  accessed_by TEXT NOT NULL,
  purpose TEXT NOT NULL,
  accessed_at TIMESTAMPTZ DEFAULT NOW(),
  ip_address TEXT,
  user_agent TEXT
);

ALTER TABLE data_access_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own access logs"
  ON data_access_log FOR SELECT
  TO authenticated
  USING (auth.uid()::text = user_id::text);

CREATE POLICY "System can insert access logs"
  ON data_access_log FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- Scheduled account deletions
CREATE TABLE IF NOT EXISTS scheduled_deletions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  scheduled_for TIMESTAMPTZ NOT NULL,
  status TEXT DEFAULT 'pending',
  reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE scheduled_deletions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own deletion schedule"
  ON scheduled_deletions FOR SELECT
  TO authenticated
  USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can create own deletion schedule"
  ON scheduled_deletions FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid()::text = user_id::text);

-- Comprehensive audit logs
CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  event_type TEXT NOT NULL,
  user_id UUID,
  resource_type TEXT,
  resource_id TEXT,
  action TEXT,
  details JSONB DEFAULT '{}'::jsonb,
  ip_address TEXT,
  user_agent TEXT,
  severity TEXT DEFAULT 'info'
);

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own audit logs"
  ON audit_logs FOR SELECT
  TO authenticated
  USING (auth.uid()::text = user_id::text);

CREATE POLICY "System can insert audit logs"
  ON audit_logs FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_user_consent_user_id ON user_consent(user_id);
CREATE INDEX IF NOT EXISTS idx_consent_history_user_id ON consent_history(user_id);
CREATE INDEX IF NOT EXISTS idx_data_access_log_user_id ON data_access_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);
