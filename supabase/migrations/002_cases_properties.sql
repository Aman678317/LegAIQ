-- ============================================================
-- 002: Cases and Properties
-- ============================================================

create table if not exists public.cases (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  created_by uuid not null references auth.users(id),
  name text not null,
  case_type text not null default 'OTHER' check (
    case_type in ('PROPERTY', 'CIVIL', 'CRIMINAL', 'COMMERCIAL', 'CORPORATE', 'FAMILY', 'LABOUR', 'TAX', 'OTHER')
  ),
  status text not null default 'ACTIVE' check (status in ('ACTIVE', 'ARCHIVED', 'CLOSED')),
  jurisdiction_state text,
  jurisdiction_district text,
  description text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_cases_org on public.cases(organization_id);
create index if not exists idx_cases_status on public.cases(status);

-- Case collaborators: extra users with access beyond org membership
create table if not exists public.case_collaborators (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'LAWYER' check (role in ('LAWYER', 'REVIEWER', 'STAFF', 'CLIENT')),
  created_at timestamptz not null default now(),
  unique (case_id, user_id)
);

-- Properties attached to a case
create table if not exists public.properties (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  name text,
  address text,
  state text,
  district text,
  taluk text,
  village text,
  survey_number text,
  hissa_number text,
  plot_number text,
  khata_number text,
  registration_number text,
  property_id_number text,
  description text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_properties_case on public.properties(case_id);

-- Field-level verification for property attributes:
-- distinguishes USER_PROVIDED vs DOCUMENT_VERIFIED vs EXTERNAL_SOURCE_VERIFIED
create table if not exists public.property_field_sources (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references public.properties(id) on delete cascade,
  field_name text not null,
  value text not null,
  verification text not null default 'USER_PROVIDED' check (
    verification in ('USER_PROVIDED', 'DOCUMENT_VERIFIED', 'EXTERNAL_SOURCE_VERIFIED', 'UNVERIFIED')
  ),
  source_document_id uuid,
  source_page integer,
  confidence numeric,
  created_at timestamptz not null default now()
);

create index if not exists idx_pfs_property on public.property_field_sources(property_id);
