-- ============================================================
-- Migration: Invitations + Profile Fields + Auto-Profile Trigger
-- Run in Supabase SQL Editor
-- Date: 27 Mar 2026
-- ============================================================

-- ============================================================
-- 1. Add status and role columns to profiles
-- ============================================================
ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'approved',
ADD COLUMN IF NOT EXISTS role text NOT NULL DEFAULT 'player';

-- Set existing admin
UPDATE profiles SET role = 'admin' WHERE id = '726c6923-b63c-4981-b0fc-bb7191fd42e4';

COMMENT ON COLUMN profiles.status IS 'pending | approved | rejected';
COMMENT ON COLUMN profiles.role IS 'admin | player';

-- ============================================================
-- 2. Create invitations table
-- ============================================================
CREATE TABLE IF NOT EXISTS invitations (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  code text UNIQUE NOT NULL,
  created_by uuid REFERENCES profiles(id) NOT NULL,
  campaign_id uuid REFERENCES campaigns(id),
  max_uses integer NOT NULL DEFAULT 1,
  current_uses integer NOT NULL DEFAULT 0,
  expires_at timestamptz,
  created_at timestamptz DEFAULT now(),
  is_active boolean NOT NULL DEFAULT true
);

-- RLS
ALTER TABLE invitations ENABLE ROW LEVEL SECURITY;

-- Admins can do everything
CREATE POLICY "Admins can manage invitations" ON invitations
  FOR ALL USING (
    EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin')
  );

-- Anyone can read active invitations (needed for code validation during signup)
CREATE POLICY "Anyone can validate invitation codes" ON invitations
  FOR SELECT USING (is_active = true);

-- ============================================================
-- 3. Auto-create profile on user signup
-- ============================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, email, username, created_at)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'username', split_part(NEW.email, '@', 1)),
    now()
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop if exists to avoid duplicates
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================
-- 4. Profile UPDATE policies
-- ============================================================
CREATE POLICY "Users can update own profile" ON profiles
  FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Admins can update any profile" ON profiles
  FOR UPDATE USING (
    EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin')
  );
