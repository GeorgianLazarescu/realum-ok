/*
  # Advanced Daily Rewards System (M149-150)

  1. New Tables
    - `daily_reward_streaks`
      - Track user login streaks with bonus multipliers
      - Store current streak, longest streak, last claim date
      - Streak bonuses: 7 days (1.5x), 30 days (2x), 90 days (3x)
    
    - `seasonal_rewards`
      - Special seasonal events (holidays, platform anniversaries)
      - Configurable reward pools and claim periods
      - Limited-time bonus rewards
    
    - `reward_calendar`
      - Monthly reward calendar showing past and future rewards
      - Track milestone achievements
      - Display streak progress visually

  2. Changes
    - Extend daily_rewards table with streak_multiplier column
    - Add seasonal_event_id foreign key to daily_rewards
    - Create indexes for performance

  3. Security
    - Enable RLS on all new tables
    - Policies for authenticated users to view own data
    - Only admins can create seasonal events
*/

-- Daily Reward Streaks Table
CREATE TABLE IF NOT EXISTS daily_reward_streaks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  current_streak integer DEFAULT 0,
  longest_streak integer DEFAULT 0,
  last_claim_date date,
  total_claims integer DEFAULT 0,
  streak_multiplier decimal(4,2) DEFAULT 1.00,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(user_id)
);

-- Seasonal Rewards Configuration Table
CREATE TABLE IF NOT EXISTS seasonal_rewards (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_name text NOT NULL,
  description text,
  start_date timestamptz NOT NULL,
  end_date timestamptz NOT NULL,
  base_reward_multiplier decimal(4,2) DEFAULT 2.00,
  bonus_tokens integer DEFAULT 1000,
  is_active boolean DEFAULT true,
  created_by uuid REFERENCES auth.users(id),
  created_at timestamptz DEFAULT now()
);

-- Reward Calendar Tracking Table
CREATE TABLE IF NOT EXISTS reward_calendar (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  claim_date date NOT NULL,
  tokens_earned integer NOT NULL,
  streak_day integer NOT NULL,
  was_seasonal_bonus boolean DEFAULT false,
  seasonal_event_id uuid REFERENCES seasonal_rewards(id),
  notes text,
  created_at timestamptz DEFAULT now(),
  UNIQUE(user_id, claim_date)
);

-- Extend daily_rewards table if needed
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'daily_rewards' AND column_name = 'streak_multiplier'
  ) THEN
    ALTER TABLE daily_rewards ADD COLUMN streak_multiplier decimal(4,2) DEFAULT 1.00;
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'daily_rewards' AND column_name = 'seasonal_event_id'
  ) THEN
    ALTER TABLE daily_rewards ADD COLUMN seasonal_event_id uuid REFERENCES seasonal_rewards(id);
  END IF;
END $$;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_daily_reward_streaks_user ON daily_reward_streaks(user_id);
CREATE INDEX IF NOT EXISTS idx_seasonal_rewards_dates ON seasonal_rewards(start_date, end_date) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_reward_calendar_user_date ON reward_calendar(user_id, claim_date DESC);

-- Enable RLS
ALTER TABLE daily_reward_streaks ENABLE ROW LEVEL SECURITY;
ALTER TABLE seasonal_rewards ENABLE ROW LEVEL SECURITY;
ALTER TABLE reward_calendar ENABLE ROW LEVEL SECURITY;

-- RLS Policies for daily_reward_streaks
CREATE POLICY "Users can view own streak data"
  ON daily_reward_streaks FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own streak data"
  ON daily_reward_streaks FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own streak data"
  ON daily_reward_streaks FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- RLS Policies for seasonal_rewards
CREATE POLICY "Anyone can view active seasonal rewards"
  ON seasonal_rewards FOR SELECT
  TO authenticated
  USING (is_active = true);

CREATE POLICY "Admins can manage seasonal rewards"
  ON seasonal_rewards FOR ALL
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM users
      WHERE users.id = auth.uid() AND users.role = 'admin'
    )
  );

-- RLS Policies for reward_calendar
CREATE POLICY "Users can view own reward calendar"
  ON reward_calendar FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own reward calendar"
  ON reward_calendar FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- Create initial seasonal reward for testing
INSERT INTO seasonal_rewards (event_name, description, start_date, end_date, base_reward_multiplier, bonus_tokens, is_active)
VALUES 
  ('Platform Launch Celebration', 'Special rewards for early adopters during platform launch month', now(), now() + interval '30 days', 2.00, 5000, true)
ON CONFLICT DO NOTHING;
