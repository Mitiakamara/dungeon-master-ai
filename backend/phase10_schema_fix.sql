
-- Fix missing columns if schema was old
alter table monsters add column if not exists speed text;
alter table monsters add column if not exists source text default 'System';
alter table monsters add column if not exists stats jsonb;
alter table monsters add column if not exists skills jsonb;
alter table monsters add column if not exists actions jsonb;

-- Also fix items just in case
alter table items add column if not exists properties jsonb;
