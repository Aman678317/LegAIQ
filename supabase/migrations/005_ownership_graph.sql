-- ============================================================
-- 005: Ownership Graph, Timeline, Comparison, Risks
-- ============================================================

-- Ownership graph nodes: Person, Property, Document, Transaction
create table if not exists public.ownership_nodes (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  node_type text not null check (node_type in ('PERSON', 'PROPERTY', 'DOCUMENT', 'TRANSACTION')),
  label text not null,
  ref_id uuid, -- optional FK to persons/properties/documents
  metadata jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_onodes_case on public.ownership_nodes(case_id);

-- Ownership graph edges; every relationship requires evidence
create table if not exists public.ownership_edges (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  source_id uuid not null references public.ownership_nodes(id) on delete cascade,
  target_id uuid not null references public.ownership_nodes(id) on delete cascade,
  edge_type text not null check (
    edge_type in ('OWNED', 'TRANSFERRED', 'INHERITED', 'GIFTED', 'MORTGAGED', 'RELEASED', 'PARTITIONED')
  ),
  event_date date,
  evidence jsonb not null, -- [{document_id, page_number, source_text}]
  confidence numeric not null default 0.0,
  created_at timestamptz not null default now()
);

create index if not exists idx_oedges_case on public.ownership_edges(case_id);
create index if not exists idx_oedges_source on public.ownership_edges(source_id);
create index if not exists idx_oedges_target on public.ownership_edges(target_id);

-- Chronological ownership/transaction timeline
create table if not exists public.timeline_events (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  event_date date,
  sort_date date, -- coalesced/inferred date for ordering
  party text,
  transaction_type text not null,
  description text not null,
  document_id uuid references public.documents(id) on delete set null,
  page_number integer,
  evidence_text text,
  confidence numeric,
  created_at timestamptz not null default now()
);

create index if not exists idx_timeline_case on public.timeline_events(case_id, sort_date);

-- Multi-document comparison results
create table if not exists public.comparison_results (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  field_name text not null,
  verdict text not null check (verdict in ('MATCH', 'MISMATCH', 'MISSING', 'UNCERTAIN')),
  values jsonb not null, -- [{document_id, document_name, value, page_number, source_text}]
  explanation text,
  created_at timestamptz not null default now()
);

create index if not exists idx_comparison_case on public.comparison_results(case_id);

-- Risk register; never created without evidence
create table if not exists public.risks (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  category text not null check (
    category in ('OWNERSHIP', 'TITLE', 'DOCUMENT', 'IDENTITY', 'BOUNDARY', 'REGISTRATION', 'ENCUMBRANCE', 'LITIGATION', 'MISSING_EVIDENCE')
  ),
  level text not null check (level in ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
  title text not null,
  description text not null,
  evidence jsonb not null, -- [{document_id, document_name, page_number, source_text}]
  compare_with jsonb, -- optional counter-evidence
  recommended_action text,
  resolved boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists idx_risks_case on public.risks(case_id);
create index if not exists idx_risks_level on public.risks(level);

-- AI findings (evidence-first analysis output)
create table if not exists public.findings (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  finding text not null,
  explanation text,
  evidence jsonb not null,
  compare_with jsonb,
  risk_level text check (risk_level in ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
  recommended_action text,
  created_at timestamptz not null default now()
);

create index if not exists idx_findings_case on public.findings(case_id);
