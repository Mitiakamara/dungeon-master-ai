-- WARN: This will delete all existing document embeddings!
-- Google 'text-embedding-004' uses 768 dimensions. OpenAI used 1536.

-- 1. Reset Table
TRUNCATE TABLE documents;

-- 2. Update Column (if supported) or Drop/Create
-- Faster to drop often in dev
DROP TABLE IF EXISTS documents;

-- 3. Recreate Table
create table documents (
  id bigserial primary key,
  content text,
  metadata jsonb,
  embedding vector(768) -- Changed to 768 for Google
);

-- 4. Recreate Search Function
drop function if exists match_documents;
create or replace function match_documents (
  query_embedding vector(768),
  match_threshold float,
  match_count int
)
returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where 1 - (documents.embedding <=> query_embedding) > match_threshold
  order by similarity desc
  limit match_count;
end;
$$;
