-- ============================================================
-- 009: RPC functions for RAG retrieval and risk summaries
-- ============================================================

-- Vector similarity search, case-scoped
create or replace function public.match_document_chunks(
  p_case_id uuid,
  p_query_embedding vector(1536),
  p_top_k integer default 12
)
returns table (
  id uuid,
  case_id uuid,
  document_id uuid,
  document_name text,
  page_number integer,
  chunk_index integer,
  content text,
  similarity float
)
language sql
stable
as $$
  select
    c.id, c.case_id, c.document_id,
    d.file_name as document_name,
    c.page_number, c.chunk_index, c.content,
    1 - (c.embedding <=> p_query_embedding) as similarity
  from public.document_chunks c
  join public.documents d on d.id = c.document_id
  where c.case_id = p_case_id
    and c.embedding is not null
  order by c.embedding <=> p_query_embedding
  limit p_top_k
$$;

-- Keyword full-text search, case-scoped
create or replace function public.keyword_search_chunks(
  p_case_id uuid,
  p_query text,
  p_top_k integer default 12
)
returns table (
  id uuid,
  case_id uuid,
  document_id uuid,
  document_name text,
  page_number integer,
  chunk_index integer,
  content text,
  rank float
)
language sql
stable
as $$
  select
    c.id, c.case_id, c.document_id,
    d.file_name as document_name,
    c.page_number, c.chunk_index, c.content,
    ts_rank(to_tsvector('simple', c.content), websearch_to_tsquery('simple', p_query)) as rank
  from public.document_chunks c
  join public.documents d on d.id = c.document_id
  where c.case_id = p_case_id
    and to_tsvector('simple', c.content) @@ websearch_to_tsquery('simple', p_query)
  order by rank desc
  limit p_top_k
$$;

-- Risk counts for case summary
create or replace function public.get_risk_counts(p_case_id uuid)
returns json
language sql
stable
as $$
  select coalesce(json_agg(t), '[]'::json) from (
    select level, count(*) as count
    from public.risks
    where case_id = p_case_id and not resolved
    group by level
  ) t
$$;
