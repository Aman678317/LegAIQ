-- ============================================================
-- 004: Extraction, Entities, Embeddings (pgvector)
-- ============================================================

-- Enable pgvector extension
create extension if not exists vector;

-- Extracted entities with full evidence chain
create table if not exists public.extracted_entities (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  document_id uuid not null references public.documents(id) on delete cascade,
  page_number integer not null,
  entity_type text not null, -- person, seller, buyer, owner, heir, witness, survey_number, ...
  value text not null,
  normalized_value text, -- canonical form for comparison
  source_text text not null, -- exact quote from the document
  confidence numeric not null default 0.0,
  verification text not null default 'UNVERIFIED' check (
    verification in ('USER_PROVIDED', 'DOCUMENT_VERIFIED', 'EXTERNAL_SOURCE_VERIFIED', 'UNVERIFIED')
  ),
  created_at timestamptz not null default now()
);

create index if not exists idx_entities_case on public.extracted_entities(case_id);
create index if not exists idx_entities_doc on public.extracted_entities(document_id);
create index if not exists idx_entities_type on public.extracted_entities(entity_type);

-- Canonical persons resolved across documents
create table if not exists public.persons (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  full_name text not null,
  normalized_name text not null,
  father_name text,
  mother_name text,
  aliases text[],
  created_at timestamptz not null default now()
);

create index if not exists idx_persons_case on public.persons(case_id);
create index if not exists idx_persons_norm on public.persons(normalized_name);

-- Document chunks for RAG
create table if not exists public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  document_id uuid not null references public.documents(id) on delete cascade,
  page_number integer not null,
  chunk_index integer not null,
  content text not null,
  embedding vector(1536),
  token_count integer,
  created_at timestamptz not null default now()
);

create index if not exists idx_chunks_case on public.document_chunks(case_id);
create index if not exists idx_chunks_doc on public.document_chunks(document_id);
-- IVFFlat index for vector similarity search (built after data load)
create index if not exists idx_chunks_embedding
  on public.document_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- Full-text search index for hybrid retrieval
create index if not exists idx_chunks_fts
  on public.document_chunks using gin (to_tsvector('simple', content));

-- AI chat messages with citations
create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  user_id uuid references auth.users(id),
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  citations jsonb, -- [{document_id, document_name, page_number, source_text}]
  created_at timestamptz not null default now()
);

create index if not exists idx_chat_case on public.chat_messages(case_id, created_at);
