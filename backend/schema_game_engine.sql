-- 1. Update Campaigns to support specific rules (Hierarchy Priority #1)
alter table campaigns add column if not exists rules text;

-- 2. Create Characters table (Distinction: User vs Character)
create table characters (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references profiles(id) not null, -- The Player (Owner)
  campaign_id uuid references campaigns(id) not null, -- The Context
  name text not null,
  race text,
  class text,
  level int default 1,
  
  -- Flexible JSONB for stats to allow easy D&D evolution
  -- Example: {"str": 16, "dex": 14, "con": 12, "int": 10, "wis": 8, "cha": 13}
  stats jsonb default '{}'::jsonb,
  
  -- Example: [{"name": "Bless", "turns": 9, "effect": "1d4 attack"}]
  active_effects jsonb default '[]'::jsonb,
  
  -- Example: {"hp_max": 20, "hp_current": 15, "imitative": 2}
  status jsonb default '{}'::jsonb,
  
  bio text, -- Backstory
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable RLS
alter table characters enable row level security;

-- Policies
create policy "Players can view characters in their campaigns" 
on characters for select using ( true ); 

create policy "Players can update their own characters" 
on characters for update using ( auth.uid() = user_id );

create policy "Players can create their own characters" 
on characters for insert with check ( auth.uid() = user_id );
