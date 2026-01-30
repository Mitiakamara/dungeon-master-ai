-- Enable the pgvector extension to work with embedding vectors
create extension if not exists vector;

-- Create a table for user profiles
create table profiles (
  id uuid references auth.users not null primary key,
  email text,
  username text,
  avatar_url text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Create a table for campaigns
create table campaigns (
  id uuid default gen_random_uuid() primary key,
  name text not null,
  description text,
  gm_id uuid references profiles(id) not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  status text default 'active'
);

-- Create a table for chat messages
create table messages (
  id uuid default gen_random_uuid() primary key,
  campaign_id uuid references campaigns(id) on delete cascade not null,
  sender_id uuid references profiles(id), -- Null if system/AI
  content text not null,
  is_diceroll boolean default false,
  roll_result jsonb, -- Stores the full dice result object
  visibility text default 'public', -- 'public', 'private', 'whisper'
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable Row Level Security (RLS)
alter table profiles enable row level security;
alter table campaigns enable row level security;
alter table messages enable row level security;

-- Create security policies (Simplified for prototype)
create policy "Public profiles are viewable by everyone." on profiles for select using ( true );
create policy "Users can insert their own profile." on profiles for insert with check ( auth.uid() = id );

create policy "Campaigns are viewable by everyone (for now)." on campaigns for select using ( true );
create policy "Authenticated users can create campaigns." on campaigns for insert with check ( auth.role() = 'authenticated' );

create policy "Everyone can read messages." on messages for select using ( true );
create policy "Authenticated users can insert messages." on messages for insert with check ( auth.role() = 'authenticated' );
