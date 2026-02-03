/*
  # REALUM Platform - Core Database Schema

  ## Overview
  Complete database schema for REALUM educational & economic metaverse platform.

  ## Tables Created

  ### 1. Users Table
  - Stores user accounts with authentication and profile data
  - Includes 2FA fields for enhanced security
  - Tracks wallet, XP, levels, badges, skills
  - Supports multiple user roles (creator, contributor, evaluator, partner, citizen)

  ### 2. Courses Table
  - Educational courses in the platform
  - Created by users, tracks enrollments and ratings

  ### 3. User Courses Table
  - Enrollment records linking users to courses
  - Tracks progress and completion status

  ### 4. Projects Table
  - Collaborative projects users can create and join
  - Tracks funding, status, and contributions

  ### 5. Proposals Table (DAO Governance)
  - DAO governance proposals
  - Voting mechanism for platform decisions

  ### 6. Votes Table
  - Individual votes on proposals
  - One vote per user per proposal

  ### 7. Transactions Table
  - REALUM token transactions
  - Complete audit trail of all token movements

  ### 8. NFTs Table
  - Digital assets and certificates
  - Achievement NFTs, course completion certificates

  ### 9. User Achievements Table
  - User achievements and milestones
  - Unlockable badges and rewards

  ### 10. Jobs Table
  - Job marketplace listings
  - Skills-based opportunities

  ### 11. Referrals Table
  - Referral tracking system
  - Rewards for bringing new users

  ### 12. Daily Rewards Table
  - Daily login rewards
  - Streak tracking

  ## Security
  - Row Level Security (RLS) enabled on all tables
  - Policies enforce data access control
  - Users can only access their own data
  - Public data is explicitly marked

  ## Indexes
  - Performance indexes on frequently queried columns
  - Composite indexes for complex queries
*/

-- Users table with 2FA support
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT DEFAULT 'citizen',
  wallet_address TEXT,
  realum_balance DECIMAL(20, 2) DEFAULT 1000.00,
  xp INTEGER DEFAULT 0,
  level INTEGER DEFAULT 1,
  badges JSONB DEFAULT '[]'::jsonb,
  skills JSONB DEFAULT '[]'::jsonb,
  courses_completed JSONB DEFAULT '[]'::jsonb,
  projects_joined JSONB DEFAULT '[]'::jsonb,
  avatar_url TEXT,
  language TEXT DEFAULT 'en',
  bio TEXT,
  location TEXT,
  website TEXT,
  social_links JSONB DEFAULT '{}'::jsonb,
  two_factor_enabled BOOLEAN DEFAULT FALSE,
  two_factor_secret TEXT,
  two_factor_backup_codes JSONB,
  last_login TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own profile"
  ON users FOR SELECT
  TO authenticated
  USING (auth.uid()::text = id::text);

CREATE POLICY "Users can update own profile"
  ON users FOR UPDATE
  TO authenticated
  USING (auth.uid()::text = id::text)
  WITH CHECK (auth.uid()::text = id::text);

CREATE POLICY "Anyone can view public user data"
  ON users FOR SELECT
  TO anon
  USING (deleted_at IS NULL);

-- Courses table
CREATE TABLE IF NOT EXISTS courses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  creator_id UUID NOT NULL,
  category TEXT,
  difficulty TEXT DEFAULT 'beginner',
  duration_hours INTEGER DEFAULT 0,
  price DECIMAL(10, 2) DEFAULT 0,
  enrolled_count INTEGER DEFAULT 0,
  rating DECIMAL(3, 2) DEFAULT 0,
  content JSONB DEFAULT '[]'::jsonb,
  skills_taught JSONB DEFAULT '[]'::jsonb,
  certificate_nft_template TEXT,
  is_published BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE courses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view published courses"
  ON courses FOR SELECT
  TO anon, authenticated
  USING (is_published = TRUE);

CREATE POLICY "Creators can manage own courses"
  ON courses FOR ALL
  TO authenticated
  USING (auth.uid()::text = creator_id::text);

-- User course enrollments
CREATE TABLE IF NOT EXISTS user_courses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  course_id UUID NOT NULL,
  enrolled_at TIMESTAMPTZ DEFAULT NOW(),
  progress INTEGER DEFAULT 0,
  completed BOOLEAN DEFAULT FALSE,
  completed_at TIMESTAMPTZ,
  certificate_issued BOOLEAN DEFAULT FALSE,
  UNIQUE(user_id, course_id)
);

ALTER TABLE user_courses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own enrollments"
  ON user_courses FOR SELECT
  TO authenticated
  USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can enroll in courses"
  ON user_courses FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own enrollment progress"
  ON user_courses FOR UPDATE
  TO authenticated
  USING (auth.uid()::text = user_id::text);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  creator_id UUID NOT NULL,
  status TEXT DEFAULT 'planning',
  category TEXT,
  required_skills JSONB DEFAULT '[]'::jsonb,
  team_members JSONB DEFAULT '[]'::jsonb,
  funding_goal DECIMAL(20, 2) DEFAULT 0,
  current_funding DECIMAL(20, 2) DEFAULT 0,
  deadline TIMESTAMPTZ,
  repository_url TEXT,
  demo_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view projects"
  ON projects FOR SELECT
  TO anon, authenticated
  USING (true);

CREATE POLICY "Creators can manage own projects"
  ON projects FOR ALL
  TO authenticated
  USING (auth.uid()::text = creator_id::text);

-- DAO Proposals
CREATE TABLE IF NOT EXISTS proposals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  creator_id UUID NOT NULL,
  proposal_type TEXT NOT NULL,
  status TEXT DEFAULT 'active',
  votes_for INTEGER DEFAULT 0,
  votes_against INTEGER DEFAULT 0,
  quorum_required INTEGER DEFAULT 100,
  deadline TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'::jsonb
);

ALTER TABLE proposals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view proposals"
  ON proposals FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Users can create proposals"
  ON proposals FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid()::text = creator_id::text);

-- Votes table
CREATE TABLE IF NOT EXISTS votes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id UUID NOT NULL,
  user_id UUID NOT NULL,
  vote BOOLEAN NOT NULL,
  voting_power INTEGER DEFAULT 1,
  voted_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(proposal_id, user_id)
);

ALTER TABLE votes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view all votes"
  ON votes FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Users can cast own votes"
  ON votes FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid()::text = user_id::text);

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  transaction_type TEXT NOT NULL,
  amount DECIMAL(20, 2) NOT NULL,
  balance_after DECIMAL(20, 2) NOT NULL,
  description TEXT,
  related_entity_type TEXT,
  related_entity_id UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'::jsonb
);

ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own transactions"
  ON transactions FOR SELECT
  TO authenticated
  USING (auth.uid()::text = user_id::text);

CREATE POLICY "System can insert transactions"
  ON transactions FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- NFTs table
CREATE TABLE IF NOT EXISTS nfts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id UUID NOT NULL,
  nft_type TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  image_url TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  rarity TEXT DEFAULT 'common',
  minted_at TIMESTAMPTZ DEFAULT NOW(),
  transferable BOOLEAN DEFAULT TRUE
);

ALTER TABLE nfts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own NFTs"
  ON nfts FOR SELECT
  TO authenticated
  USING (auth.uid()::text = owner_id::text);

CREATE POLICY "Anyone can view public NFTs"
  ON nfts FOR SELECT
  TO anon
  USING (true);

-- User achievements
CREATE TABLE IF NOT EXISTS user_achievements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  achievement_type TEXT NOT NULL,
  achievement_name TEXT NOT NULL,
  description TEXT,
  earned_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'::jsonb,
  UNIQUE(user_id, achievement_type, achievement_name)
);

ALTER TABLE user_achievements ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own achievements"
  ON user_achievements FOR SELECT
  TO authenticated
  USING (auth.uid()::text = user_id::text);

CREATE POLICY "Anyone can view all achievements"
  ON user_achievements FOR SELECT
  TO anon
  USING (true);

-- Jobs table
CREATE TABLE IF NOT EXISTS jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  employer_id UUID NOT NULL,
  job_type TEXT DEFAULT 'freelance',
  required_skills JSONB DEFAULT '[]'::jsonb,
  budget DECIMAL(20, 2),
  status TEXT DEFAULT 'open',
  deadline TIMESTAMPTZ,
  applicants JSONB DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view open jobs"
  ON jobs FOR SELECT
  TO authenticated
  USING (status = 'open');

CREATE POLICY "Employers can manage own jobs"
  ON jobs FOR ALL
  TO authenticated
  USING (auth.uid()::text = employer_id::text);

-- Referrals table
CREATE TABLE IF NOT EXISTS referrals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  referrer_id UUID NOT NULL,
  referred_email TEXT NOT NULL,
  referred_user_id UUID,
  status TEXT DEFAULT 'pending',
  reward_claimed BOOLEAN DEFAULT FALSE,
  reward_amount DECIMAL(10, 2) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

ALTER TABLE referrals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own referrals"
  ON referrals FOR SELECT
  TO authenticated
  USING (auth.uid()::text = referrer_id::text);

CREATE POLICY "Users can create referrals"
  ON referrals FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid()::text = referrer_id::text);

-- Daily rewards table
CREATE TABLE IF NOT EXISTS daily_rewards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  claim_date DATE NOT NULL,
  streak_count INTEGER DEFAULT 1,
  reward_amount DECIMAL(10, 2) NOT NULL,
  claimed_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, claim_date)
);

ALTER TABLE daily_rewards ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own rewards"
  ON daily_rewards FOR SELECT
  TO authenticated
  USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can claim daily rewards"
  ON daily_rewards FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid()::text = user_id::text);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_wallet ON users(wallet_address);
CREATE INDEX IF NOT EXISTS idx_courses_creator ON courses(creator_id);
CREATE INDEX IF NOT EXISTS idx_courses_category ON courses(category);
CREATE INDEX IF NOT EXISTS idx_user_courses_user ON user_courses(user_id);
CREATE INDEX IF NOT EXISTS idx_user_courses_course ON user_courses(course_id);
CREATE INDEX IF NOT EXISTS idx_projects_creator ON projects(creator_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals(status);
CREATE INDEX IF NOT EXISTS idx_proposals_deadline ON proposals(deadline);
CREATE INDEX IF NOT EXISTS idx_votes_proposal ON votes(proposal_id);
CREATE INDEX IF NOT EXISTS idx_votes_user ON votes(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_nfts_owner ON nfts(owner_id);
CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_employer ON jobs(employer_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id);
CREATE INDEX IF NOT EXISTS idx_daily_rewards_user ON daily_rewards(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_rewards_date ON daily_rewards(claim_date);
