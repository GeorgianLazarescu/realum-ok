/*
  # Advanced Chat System (M171-175)

  1. New Tables
    - `chat_channels`
      - Support for 1-on-1, group chats, and DAO-specific channels
      - Channel types: direct, group, dao, public
      - Member management and permissions
    
    - `chat_messages`
      - Store all messages with threading support
      - Support for file/image attachments (URLs)
      - Emoji reactions
      - Message editing and deletion tracking
    
    - `chat_members`
      - Track channel membership
      - Online status and last seen
      - Read receipts and typing indicators
    
    - `chat_reactions`
      - Emoji reactions to messages
      - Multiple reactions per user per message
    
    - `chat_threads`
      - Message threading for organized discussions
      - Thread-specific metadata

  2. Changes
    - Add chat-related indexes for performance
    - Support for file attachments via URLs

  3. Security
    - Enable RLS on all tables
    - Members can only see messages in their channels
    - Channel creators/admins have additional permissions
*/

-- Chat Channels Table
CREATE TABLE IF NOT EXISTS chat_channels (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  description text,
  type text NOT NULL DEFAULT 'group',
  avatar_url text,
  created_by uuid NOT NULL REFERENCES auth.users(id),
  dao_id uuid,
  is_private boolean DEFAULT true,
  is_archived boolean DEFAULT false,
  last_message_at timestamptz DEFAULT now(),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT valid_channel_type CHECK (type IN ('direct', 'group', 'dao', 'public'))
);

-- Chat Messages Table
CREATE TABLE IF NOT EXISTS chat_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_id uuid NOT NULL REFERENCES chat_channels(id) ON DELETE CASCADE,
  sender_id uuid NOT NULL REFERENCES auth.users(id),
  content text NOT NULL,
  message_type text DEFAULT 'text',
  reply_to_id uuid REFERENCES chat_messages(id),
  thread_id uuid,
  attachments jsonb DEFAULT '[]'::jsonb,
  is_edited boolean DEFAULT false,
  is_deleted boolean DEFAULT false,
  edited_at timestamptz,
  deleted_at timestamptz,
  created_at timestamptz DEFAULT now(),
  CONSTRAINT valid_message_type CHECK (message_type IN ('text', 'image', 'file', 'system'))
);

-- Chat Members Table
CREATE TABLE IF NOT EXISTS chat_members (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_id uuid NOT NULL REFERENCES chat_channels(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role text DEFAULT 'member',
  is_muted boolean DEFAULT false,
  last_read_message_id uuid,
  last_seen_at timestamptz DEFAULT now(),
  is_online boolean DEFAULT false,
  is_typing boolean DEFAULT false,
  joined_at timestamptz DEFAULT now(),
  UNIQUE(channel_id, user_id),
  CONSTRAINT valid_member_role CHECK (role IN ('owner', 'admin', 'member'))
);

-- Chat Reactions Table
CREATE TABLE IF NOT EXISTS chat_reactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id uuid NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  emoji text NOT NULL,
  created_at timestamptz DEFAULT now(),
  UNIQUE(message_id, user_id, emoji)
);

-- Chat Threads Table
CREATE TABLE IF NOT EXISTS chat_threads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_id uuid NOT NULL REFERENCES chat_channels(id) ON DELETE CASCADE,
  root_message_id uuid NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
  title text,
  message_count integer DEFAULT 0,
  participant_count integer DEFAULT 0,
  last_message_at timestamptz DEFAULT now(),
  created_at timestamptz DEFAULT now(),
  UNIQUE(root_message_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_chat_channels_type ON chat_channels(type) WHERE is_archived = false;
CREATE INDEX IF NOT EXISTS idx_chat_channels_dao ON chat_channels(dao_id) WHERE dao_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_chat_messages_channel ON chat_messages(channel_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_sender ON chat_messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_thread ON chat_messages(thread_id) WHERE thread_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_chat_members_user ON chat_members(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_members_channel ON chat_members(channel_id);
CREATE INDEX IF NOT EXISTS idx_chat_reactions_message ON chat_reactions(message_id);

-- Enable RLS
ALTER TABLE chat_channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_reactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_threads ENABLE ROW LEVEL SECURITY;

-- RLS Policies for chat_channels
CREATE POLICY "Users can view channels they are members of"
  ON chat_channels FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM chat_members
      WHERE chat_members.channel_id = chat_channels.id
      AND chat_members.user_id = auth.uid()
    )
    OR type = 'public'
  );

CREATE POLICY "Users can create channels"
  ON chat_channels FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = created_by);

CREATE POLICY "Channel owners can update channels"
  ON chat_channels FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM chat_members
      WHERE chat_members.channel_id = chat_channels.id
      AND chat_members.user_id = auth.uid()
      AND chat_members.role IN ('owner', 'admin')
    )
  );

-- RLS Policies for chat_messages
CREATE POLICY "Users can view messages in their channels"
  ON chat_messages FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM chat_members
      WHERE chat_members.channel_id = chat_messages.channel_id
      AND chat_members.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can send messages to their channels"
  ON chat_messages FOR INSERT
  TO authenticated
  WITH CHECK (
    auth.uid() = sender_id
    AND EXISTS (
      SELECT 1 FROM chat_members
      WHERE chat_members.channel_id = chat_messages.channel_id
      AND chat_members.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can update their own messages"
  ON chat_messages FOR UPDATE
  TO authenticated
  USING (auth.uid() = sender_id)
  WITH CHECK (auth.uid() = sender_id);

-- RLS Policies for chat_members
CREATE POLICY "Users can view members of their channels"
  ON chat_members FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM chat_members cm
      WHERE cm.channel_id = chat_members.channel_id
      AND cm.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can join channels"
  ON chat_members FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own membership"
  ON chat_members FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can leave channels"
  ON chat_members FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- RLS Policies for chat_reactions
CREATE POLICY "Users can view reactions in their channels"
  ON chat_reactions FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM chat_messages
      JOIN chat_members ON chat_members.channel_id = chat_messages.channel_id
      WHERE chat_messages.id = chat_reactions.message_id
      AND chat_members.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can add reactions"
  ON chat_reactions FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own reactions"
  ON chat_reactions FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- RLS Policies for chat_threads
CREATE POLICY "Users can view threads in their channels"
  ON chat_threads FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM chat_members
      WHERE chat_members.channel_id = chat_threads.channel_id
      AND chat_members.user_id = auth.uid()
    )
  );
