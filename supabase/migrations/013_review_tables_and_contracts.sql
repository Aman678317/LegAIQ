-- ============================================================
-- 013: Spreadsheet Review Tables, Clause Library & Playbooks
-- ============================================================

-- 1. Review Tables
create table if not exists public.review_tables (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  name text not null,
  description text default '',
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_review_tables_case on public.review_tables(case_id);

-- 2. Review Table Columns (dynamic extraction prompts)
create table if not exists public.review_table_columns (
  id uuid primary key default gen_random_uuid(),
  table_id uuid not null references public.review_tables(id) on delete cascade,
  name text not null,
  column_type text not null default 'prompt' check (
    column_type in ('prompt', 'text', 'number', 'date', 'boolean', 'enum')
  ),
  prompt text,
  model text default 'gpt-4o-mini',
  position integer default 0,
  created_at timestamptz not null default now()
);

create index if not exists idx_review_table_columns_table on public.review_table_columns(table_id);

-- 3. Review Table Cells (grounded values, confidence score, source evidence)
create table if not exists public.review_table_cells (
  id uuid primary key default gen_random_uuid(),
  table_id uuid not null references public.review_tables(id) on delete cascade,
  column_id uuid not null references public.review_table_columns(id) on delete cascade,
  document_id uuid not null references public.documents(id) on delete cascade,
  value text,
  confidence_score numeric(4,3) check (confidence_score >= 0.0 and confidence_score <= 1.0),
  evidence jsonb, -- { doc_id, doc_name, page_num, text_snippet, bbox, char_start, char_end }
  status text not null default 'completed' check (
    status in ('pending', 'processing', 'completed', 'failed', 'not_found')
  ),
  updated_at timestamptz not null default now(),
  unique (table_id, column_id, document_id)
);

create index if not exists idx_review_table_cells_table on public.review_table_cells(table_id);
create index if not exists idx_review_table_cells_doc on public.review_table_cells(document_id);

-- 4. Enterprise Clause Library
create table if not exists public.clause_library (
  id uuid primary key default gen_random_uuid(),
  clause_id text unique not null,
  clause_type text not null,
  title text not null,
  category text not null,
  standard_language text not null,
  fallback_tier_1 text not null,
  fallback_tier_2 text,
  walkaway_language text,
  guidance_notes text,
  statutory_reference text,
  jurisdiction text default 'India',
  tags text[],
  organization_id uuid references public.organizations(id) on delete cascade,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_clause_library_type on public.clause_library(clause_type);
create index if not exists idx_clause_library_cat on public.clause_library(category);

-- 5. Firm Playbooks
create table if not exists public.contract_playbooks (
  id uuid primary key default gen_random_uuid(),
  playbook_id text unique not null,
  name text not null,
  description text,
  contract_type text not null,
  rules jsonb not null default '[]'::jsonb,
  organization_id uuid references public.organizations(id) on delete cascade,
  created_at timestamptz not null default now()
);

create index if not exists idx_contract_playbooks_type on public.contract_playbooks(contract_type);

-- 6. Contract Evaluations & Deviations
create table if not exists public.contract_evaluations (
  id uuid primary key default gen_random_uuid(),
  case_id uuid references public.cases(id) on delete cascade,
  contract_id text not null,
  playbook_id text references public.contract_playbooks(playbook_id) on delete set null,
  compliance_score numeric(5,2),
  overall_status text,
  deviations jsonb default '[]'::jsonb,
  redline_recommendations jsonb default '[]'::jsonb,
  evaluated_at timestamptz not null default now()
);

create index if not exists idx_contract_evaluations_case on public.contract_evaluations(case_id);
