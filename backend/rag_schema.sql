-- Ensure pgvector is enabled
create extension if not exists vector;

-- Create a table to store your documents
create table documents (
  id uuid primary key default gen_random_uuid(),
  content text, -- corresponds to Document.page_content
  metadata jsonb, -- corresponds to Document.metadata
  embedding vector(1536) -- 1536 works for OpenAI embeddings
);

-- Create a function to search for documents
create function match_documents (
  query_embedding vector(1536),
  match_threshold float,
  match_count int
) returns table (
  id uuid,
  content text,
  metadata jsonb,
  similarity float
) language plpgsql stable as $$
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
