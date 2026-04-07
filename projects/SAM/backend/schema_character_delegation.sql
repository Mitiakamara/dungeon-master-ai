-- ============================================================
-- Migration: Character delegation
-- Run in Supabase SQL Editor
-- ============================================================

ALTER TABLE characters
ADD COLUMN IF NOT EXISTS controlled_by uuid REFERENCES profiles(id) DEFAULT NULL;

COMMENT ON COLUMN characters.controlled_by IS
  'If set, this user controls the character instead of the owner. Used for /delegate.';
