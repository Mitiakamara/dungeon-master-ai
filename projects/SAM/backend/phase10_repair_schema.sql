-- Phase 10 Repair: Monsters and Items
-- Run this in Supabase SQL Editor if these tables are missing

-- 1. Monsters Table
create table if not exists monsters (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  size text,
  type text,
  alignment text,
  ac int,
  hp int,
  cr float, -- Challenge Rating
  speed text,
  stats jsonb, -- {str, dex, con, int, wis, cha}
  skills jsonb, -- {perception: 5, ...}
  actions jsonb, -- List of actions
  source text default 'System',
  embedding vector(768)
);

-- Index for Monsters
create index if not exists idx_monsters_embedding on monsters using hnsw (embedding vector_cosine_ops);
create index if not exists idx_monsters_name on monsters(name);

-- 2. Items Table (Weapons, Armor, Gear)
create table if not exists items (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  type text, -- Weapon, Armor, Potion, Wondrous Item
  rarity text, -- Common, Rare, Legendary
  description text,
  properties jsonb, -- {damage: "1d8", weight: "2lb", cost: "15gp"}
  source text default 'System',
  embedding vector(768)
);

-- Index for Items
create index if not exists idx_items_embedding on items using hnsw (embedding vector_cosine_ops);
create index if not exists idx_items_name on items(name);

-- 3. Update Match Function to include these (idempotent)
create or replace function match_compendium (
  query_embedding vector(768),
  match_threshold float,
  match_count int,
  table_name text
)
returns table (
  id uuid,
  name text,
  content text, 
  similarity float
)
language plpgsql
as $$
begin
  if table_name = 'spells' then
    return query
    select
      spells.id,
      spells.name,
      format('Spell: %s (Lvl %s %s). Cast: %s. Range: %s. Duration: %s. Desc: %s', 
             spells.name, spells.level, spells.school, spells.casting_time, spells.range, spells.duration, spells.description) as content,
      1 - (spells.embedding <=> query_embedding) as similarity
    from spells
    where 1 - (spells.embedding <=> query_embedding) > match_threshold
    order by spells.embedding <=> query_embedding
    limit match_count;
    
  elsif table_name = 'monsters' then
    return query
    select
      monsters.id,
      monsters.name,
      format('Monster: %s (CR %s %s). AC %s, HP %s. Stats: %s. Actions: %s', 
             monsters.name, monsters.cr, monsters.type, monsters.ac, monsters.hp, monsters.stats, monsters.actions) as content,
      1 - (monsters.embedding <=> query_embedding) as similarity
    from monsters
    where 1 - (monsters.embedding <=> query_embedding) > match_threshold
    order by monsters.embedding <=> query_embedding
    limit match_count;
    
  elsif table_name = 'items' then
    return query
    select
      items.id,
      items.name,
      format('Item: %s (%s %s). Desc: %s. Props: %s', 
             items.name, items.rarity, items.type, items.description, items.properties) as content,
      1 - (items.embedding <=> query_embedding) as similarity
    from items
    where 1 - (items.embedding <=> query_embedding) > match_threshold
    order by items.embedding <=> query_embedding
    limit match_count;
  end if;
end;
$$;
