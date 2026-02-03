/*
  # Push Notifications System (M166-170)

  1. New Tables
    - `notifications`
      - Store all notifications for users
      - Types: info, success, warning, error, achievement
      - Channels: in_app, email, push
      - Read/unread tracking
    
    - `notification_preferences`
      - User preferences for notification channels
      - Mute/unmute specific notification types
      - Frequency settings (instant, daily_digest, weekly_digest)
    
    - `notification_templates`
      - Reusable notification templates
      - Support for variables/placeholders
      - Multi-language support
    
    - `notification_queue`
      - Queue for scheduled/batched notifications
      - Retry logic for failed deliveries
      - Priority levels

  2. Changes
    - Add notification columns to users table for subscription info
    - Create indexes for performance

  3. Security
    - Enable RLS on all new tables
    - Users can only view own notifications
    - Only system/admin can create templates
*/

-- Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  type text NOT NULL DEFAULT 'info',
  title text NOT NULL,
  message text NOT NULL,
  channel text NOT NULL DEFAULT 'in_app',
  category text DEFAULT 'general',
  action_url text,
  action_label text,
  is_read boolean DEFAULT false,
  read_at timestamptz,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  expires_at timestamptz,
  CONSTRAINT valid_notification_type CHECK (type IN ('info', 'success', 'warning', 'error', 'achievement', 'system')),
  CONSTRAINT valid_channel CHECK (channel IN ('in_app', 'email', 'push', 'all'))
);

-- Notification Preferences Table
CREATE TABLE IF NOT EXISTS notification_preferences (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  email_enabled boolean DEFAULT true,
  push_enabled boolean DEFAULT true,
  in_app_enabled boolean DEFAULT true,
  daily_digest boolean DEFAULT false,
  weekly_digest boolean DEFAULT false,
  muted_categories jsonb DEFAULT '[]'::jsonb,
  quiet_hours_start time,
  quiet_hours_end time,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(user_id)
);

-- Notification Templates Table
CREATE TABLE IF NOT EXISTS notification_templates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_key text NOT NULL UNIQUE,
  title_template text NOT NULL,
  message_template text NOT NULL,
  category text NOT NULL DEFAULT 'general',
  default_channel text DEFAULT 'in_app',
  variables jsonb DEFAULT '[]'::jsonb,
  is_active boolean DEFAULT true,
  created_by uuid REFERENCES auth.users(id),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Notification Queue Table
CREATE TABLE IF NOT EXISTS notification_queue (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  notification_id uuid REFERENCES notifications(id) ON DELETE CASCADE,
  scheduled_for timestamptz NOT NULL,
  priority integer DEFAULT 1,
  retry_count integer DEFAULT 0,
  max_retries integer DEFAULT 3,
  last_error text,
  status text DEFAULT 'pending',
  processed_at timestamptz,
  created_at timestamptz DEFAULT now(),
  CONSTRAINT valid_queue_status CHECK (status IN ('pending', 'processing', 'sent', 'failed', 'cancelled')),
  CONSTRAINT valid_priority CHECK (priority BETWEEN 1 AND 5)
);

-- Add notification subscription fields to users table (if not exists)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'push_subscription'
  ) THEN
    ALTER TABLE users ADD COLUMN push_subscription jsonb;
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'email_verified'
  ) THEN
    ALTER TABLE users ADD COLUMN email_verified boolean DEFAULT false;
  END IF;
END $$;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_notifications_user_created ON notifications(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(user_id, is_read) WHERE is_read = false;
CREATE INDEX IF NOT EXISTS idx_notification_queue_scheduled ON notification_queue(scheduled_for) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_notification_queue_status ON notification_queue(status, priority DESC);

-- Enable RLS
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_queue ENABLE ROW LEVEL SECURITY;

-- RLS Policies for notifications
CREATE POLICY "Users can view own notifications"
  ON notifications FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update own notifications"
  ON notifications FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "System can insert notifications"
  ON notifications FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Users can delete own notifications"
  ON notifications FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- RLS Policies for notification_preferences
CREATE POLICY "Users can view own preferences"
  ON notification_preferences FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own preferences"
  ON notification_preferences FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own preferences"
  ON notification_preferences FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- RLS Policies for notification_templates
CREATE POLICY "Anyone can view active templates"
  ON notification_templates FOR SELECT
  TO authenticated
  USING (is_active = true);

CREATE POLICY "Admins can manage templates"
  ON notification_templates FOR ALL
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM users
      WHERE users.id = auth.uid() AND users.role = 'admin'
    )
  );

-- RLS Policies for notification_queue
CREATE POLICY "Users can view own queued notifications"
  ON notification_queue FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Insert default notification templates
INSERT INTO notification_templates (template_key, title_template, message_template, category, variables) VALUES
  ('daily_reward_claimed', 'Daily Reward Claimed', 'You earned {{tokens}} RLM tokens! Current streak: {{streak}} days', 'rewards', '["tokens", "streak"]'::jsonb),
  ('course_completed', 'Course Completed!', 'Congratulations on completing {{course_name}}! You earned {{xp}} XP', 'education', '["course_name", "xp"]'::jsonb),
  ('job_application', 'New Job Application', '{{username}} applied for {{job_title}}', 'jobs', '["username", "job_title"]'::jsonb),
  ('proposal_passed', 'Proposal Passed', 'The proposal "{{proposal_title}}" has passed with {{votes_for}} votes', 'governance', '["proposal_title", "votes_for"]'::jsonb),
  ('token_received', 'Tokens Received', 'You received {{amount}} RLM from {{sender}}', 'transactions', '["amount", "sender"]'::jsonb),
  ('level_up', 'Level Up!', 'Congratulations! You reached level {{level}}', 'achievements', '["level"]'::jsonb),
  ('badge_earned', 'New Badge Earned', 'You unlocked the {{badge_name}} badge!', 'achievements', '["badge_name"]'::jsonb),
  ('project_milestone', 'Project Milestone', 'Project {{project_name}} reached {{progress}}% completion', 'projects', '["project_name", "progress"]'::jsonb)
ON CONFLICT (template_key) DO NOTHING;
