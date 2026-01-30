-- Phase 9: Admin & Communications

-- 1. Campaign Settings (Difficulty, Tone, etc.)
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS settings JSONB DEFAULT '{}'::jsonb;

-- 2. Private Messages / "Whispers" / "Email"
CREATE TABLE IF NOT EXISTS private_messages (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE NOT NULL,
  
  -- Sender: If NULL, it is S.A.M. (AI) or System
  sender_id UUID REFERENCES profiles(id) ON DELETE SET NULL, 
  
  -- Receiver: The target User. If NULL, maybe a broadcast or error?
  -- We assume whispers are targeted.
  receiver_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
  
  -- Optional: Contextual character references (e.g. "From character X to character Y")
  -- This helps roleplay even if the underlying mechanic is User-to-User
  sender_character_id UUID REFERENCES characters(id) ON DELETE SET NULL,
  receiver_character_id UUID REFERENCES characters(id) ON DELETE SET NULL,

  subject TEXT, -- Email style subject line (optional)
  content TEXT NOT NULL,
  
  is_read BOOLEAN DEFAULT FALSE,
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS
ALTER TABLE private_messages ENABLE ROW LEVEL SECURITY;

-- Policies

-- Users can read messages sent TO them (receiver_id) or BY them (sender_id)
-- Also allow reading if they are the GM of the campaign (GM God Mode)
CREATE POLICY "Users view their own messages" ON private_messages
FOR SELECT USING (
  auth.uid() = sender_id OR 
  auth.uid() = receiver_id OR
  exists (select 1 from campaigns where id = private_messages.campaign_id and gm_id = auth.uid())
);

-- Users can send messages
CREATE POLICY "Users can send messages" ON private_messages
FOR INSERT WITH CHECK (
  auth.uid() = sender_id
);

-- Users can update 'is_read' on messages received
CREATE POLICY "Users can mark received messages as read" ON private_messages
FOR UPDATE USING (
  auth.uid() = receiver_id
);

-- NOTE: Since S.A.M. (AI) runs on the backend with a Service Key (bypass RLS) or as a special user, 
-- it can insert messages with NULL sender_id without RLS blocking it (if running backend logic).
