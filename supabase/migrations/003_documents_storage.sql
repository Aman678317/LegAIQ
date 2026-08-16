-- ============================================================
-- 003: Documents, Pages, Jobs
-- ============================================================

create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  uploaded_by uuid not null references auth.users(id),
  file_name text not null,
  file_type text not null,
  file_size bigint not null,
  storage_path text not null,
  document_type text, -- sale_deed, gift_deed, mutation_record, etc.
  status text not null default 'UPLOADED' check (
    status in ('UPLOADED', 'VALIDATING', 'PROCESSING', 'OCR_RUNNING', 'EXTRACTING', 'ANALYZING', 'COMPLETED', 'FAILED')
  ),
  page_count integer,
  language text,
  ocr_confidence numeric,
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_documents_case on public.documents(case_id);
create index if not exists idx_documents_status on public.documents(status);

-- Page-by-page OCR results; original file is never modified
create table if not exists public.document_pages (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  page_number integer not null,
  text text,
  language text,
  confidence numeric,
  bounding_boxes jsonb, -- [{x, y, w, h, text, conf}]
  processing_version text,
  created_at timestamptz not null default now(),
  unique (document_id, page_number)
);

create index if not exists idx_pages_document on public.document_pages(document_id);

-- Page-level translations (original always preserved)
create table if not exists public.page_translations (
  id uuid primary key default gen_random_uuid(),
  page_id uuid not null references public.document_pages(id) on delete cascade,
  target_language text not null,
  translated_text text not null,
  provider text,
  created_at timestamptz not null default now(),
  unique (page_id, target_language)
);

-- Async job tracking for workers
create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  case_id uuid references public.cases(id) on delete cascade,
  document_id uuid references public.documents(id) on delete cascade,
  job_type text not null, -- ocr, extraction, embeddings, analysis, comparison, research, report
  state text not null default 'QUEUED' check (
    state in ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'RETRYING', 'CANCELLED')
  ),
  progress integer not null default 0,
  attempts integer not null default 0,
  max_attempts integer not null default 3,
  payload jsonb,
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_jobs_state on public.jobs(state);
create index if not exists idx_jobs_document on public.jobs(document_id);
create index if not exists idx_jobs_case on public.jobs(case_id);

-- Case activity feed
create table if not exists public.activity_events (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  actor_id uuid references auth.users(id),
  event_type text not null,
  description text not null,
  metadata jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_activity_case on public.activity_events(case_id, created_at desc);
