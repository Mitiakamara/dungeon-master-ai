
-- Phase 11: Campaign Management

create table if not exists checkpoints (
    id uuid default gen_random_uuid() primary key,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    name text not null unique,
    chat_history jsonb default '[]'::jsonb,
    character_states jsonb default '{}'::jsonb, -- Snapshot of HP, stats, etc. for active characters
    notes text
);

-- Index for quick lookup by name
create index if not exists idx_checkpoints_name on checkpoints(name);
