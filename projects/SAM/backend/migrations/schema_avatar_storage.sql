-- Migration 009: Avatar Storage Bucket
-- Run in Supabase SQL Editor
-- Creates a public storage bucket for AI-generated character avatars

-- Create avatars bucket in Supabase Storage
INSERT INTO storage.buckets (id, name, public)
VALUES ('avatars', 'avatars', true)
ON CONFLICT (id) DO NOTHING;

-- Allow authenticated users to upload their own avatars
CREATE POLICY "Users can upload avatars" ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'avatars' AND
    auth.role() = 'authenticated'
  );

-- Allow public read access to avatars
CREATE POLICY "Public read access for avatars" ON storage.objects
  FOR SELECT USING (
    bucket_id = 'avatars'
  );

-- Allow users to update/delete their own avatars
CREATE POLICY "Users can manage their avatars" ON storage.objects
  FOR ALL USING (
    bucket_id = 'avatars' AND
    auth.role() = 'authenticated'
  );
