-- ============================================================
-- 015: Security & Row Level Security (RLS) Multi-Tenant Hardening
-- Complete PostgreSQL-level isolation for review tables, contracts,
-- shared spaces, BSA certificates, agent workflows, and SSO providers.
-- ============================================================

-- ============================================================
-- 1. Enable RLS on Migration 013 Tables
-- ============================================================

alter table if exists public.review_tables enable row level security;
alter table if exists public.review_table_columns enable row level security;
alter table if exists public.review_table_cells enable row level security;
alter table if exists public.clause_library enable row level security;
alter table if exists public.contract_playbooks enable row level security;
alter table if exists public.contract_evaluations enable row level security;

-- ---------- Review Tables (Case-scoped) ----------
create policy "case members read review_tables" on public.review_tables
  for select using (public.is_case_member(case_id));

create policy "case members insert review_tables" on public.review_tables
  for insert with check (public.is_case_member(case_id));

create policy "case members update review_tables" on public.review_tables
  for update using (public.is_case_member(case_id))
  with check (public.is_case_member(case_id));

create policy "case admins delete review_tables" on public.review_tables
  for delete using (public.can_manage_case(case_id));

-- ---------- Review Table Columns (Case-scoped via table_id) ----------
create policy "case members read review_table_columns" on public.review_table_columns
  for select using (
    public.is_case_member((select t.case_id from public.review_tables t where t.id = table_id))
  );

create policy "case members insert review_table_columns" on public.review_table_columns
  for insert with check (
    public.is_case_member((select t.case_id from public.review_tables t where t.id = table_id))
  );

create policy "case members update review_table_columns" on public.review_table_columns
  for update using (
    public.is_case_member((select t.case_id from public.review_tables t where t.id = table_id))
  )
  with check (
    public.is_case_member((select t.case_id from public.review_tables t where t.id = table_id))
  );

create policy "case admins delete review_table_columns" on public.review_table_columns
  for delete using (
    public.can_manage_case((select t.case_id from public.review_tables t where t.id = table_id))
  );

-- ---------- Review Table Cells (Case-scoped via table_id) ----------
create policy "case members read review_table_cells" on public.review_table_cells
  for select using (
    public.is_case_member((select t.case_id from public.review_tables t where t.id = table_id))
  );

create policy "case members insert review_table_cells" on public.review_table_cells
  for insert with check (
    public.is_case_member((select t.case_id from public.review_tables t where t.id = table_id))
  );

create policy "case members update review_table_cells" on public.review_table_cells
  for update using (
    public.is_case_member((select t.case_id from public.review_tables t where t.id = table_id))
  )
  with check (
    public.is_case_member((select t.case_id from public.review_tables t where t.id = table_id))
  );

create policy "case admins delete review_table_cells" on public.review_table_cells
  for delete using (
    public.can_manage_case((select t.case_id from public.review_tables t where t.id = table_id))
  );

-- ---------- Clause Library (Org-scoped with system-wide defaults) ----------
create policy "org members read clause_library" on public.clause_library
  for select using (
    organization_id is null or public.is_org_member(organization_id)
  );

create policy "org managers manage clause_library" on public.clause_library
  for all using (
    organization_id is not null and public.can_manage_org(organization_id)
  )
  with check (
    organization_id is not null and public.can_manage_org(organization_id)
  );

-- ---------- Contract Playbooks (Org-scoped with system-wide defaults) ----------
create policy "org members read contract_playbooks" on public.contract_playbooks
  for select using (
    organization_id is null or public.is_org_member(organization_id)
  );

create policy "org managers manage contract_playbooks" on public.contract_playbooks
  for all using (
    organization_id is not null and public.can_manage_org(organization_id)
  )
  with check (
    organization_id is not null and public.can_manage_org(organization_id)
  );

-- ---------- Contract Evaluations (Case-scoped) ----------
create policy "case members read contract_evaluations" on public.contract_evaluations
  for select using (
    case_id is not null and public.is_case_member(case_id)
  );

create policy "case members insert contract_evaluations" on public.contract_evaluations
  for insert with check (
    case_id is not null and public.is_case_member(case_id)
  );

create policy "case members update contract_evaluations" on public.contract_evaluations
  for update using (
    case_id is not null and public.is_case_member(case_id)
  )
  with check (
    case_id is not null and public.is_case_member(case_id)
  );

create policy "case admins delete contract_evaluations" on public.contract_evaluations
  for delete using (
    case_id is not null and public.can_manage_case(case_id)
  );


-- ============================================================
-- 2. DDL & RLS for Missing Backend Tables
-- ============================================================

-- ---------- 2.1 Shared Spaces (Case-scoped) ----------
create table if not exists public.shared_spaces (
  id uuid primary key default gen_random_uuid(),
  token text unique not null,
  case_id uuid not null references public.cases(id) on delete cascade,
  case_name text,
  name text not null,
  recipient_email text not null,
  recipient_name text,
  role text not null default 'VIEWER',
  duration text not null default '24h',
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  created_by uuid references auth.users(id),
  is_active boolean not null default true,
  has_passcode boolean not null default false,
  passcode_hash text,
  document_ids jsonb default '[]'::jsonb,
  allow_download boolean not null default true,
  watermark_enabled boolean not null default true,
  access_count integer not null default 0,
  failed_attempts integer not null default 0,
  last_failed_at timestamptz,
  last_accessed_at timestamptz
);

create index if not exists idx_shared_spaces_token on public.shared_spaces(token);
create index if not exists idx_shared_spaces_case on public.shared_spaces(case_id);

alter table public.shared_spaces enable row level security;

create policy "case members read shared_spaces" on public.shared_spaces
  for select using (public.is_case_member(case_id));

create policy "case members insert shared_spaces" on public.shared_spaces
  for insert with check (public.is_case_member(case_id));

create policy "case members update shared_spaces" on public.shared_spaces
  for update using (public.is_case_member(case_id))
  with check (public.is_case_member(case_id));

create policy "case admins delete shared_spaces" on public.shared_spaces
  for delete using (public.can_manage_case(case_id));


-- ---------- 2.2 BSA Section 63 Evidence Certificates (Case-scoped) ----------
create table if not exists public.bsa_certificates (
  id text primary key,
  case_id uuid not null references public.cases(id) on delete cascade,
  certificate_data jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_bsa_certificates_case on public.bsa_certificates(case_id);

alter table public.bsa_certificates enable row level security;

create policy "case members read bsa_certificates" on public.bsa_certificates
  for select using (public.is_case_member(case_id));

create policy "case members insert bsa_certificates" on public.bsa_certificates
  for insert with check (public.is_case_member(case_id));

create policy "case admins delete bsa_certificates" on public.bsa_certificates
  for delete using (public.can_manage_case(case_id));


-- ---------- 2.3 Agent Workflows (Org & Case Scoped) ----------
create table if not exists public.agent_workflows (
  id text primary key,
  case_id uuid references public.cases(id) on delete cascade,
  organization_id uuid references public.organizations(id) on delete cascade,
  user_id uuid references auth.users(id) on delete set null,
  status text not null,
  current_node text,
  node_results jsonb default '{}'::jsonb,
  node_statuses jsonb default '{}'::jsonb,
  error text,
  started_at timestamptz,
  completed_at timestamptz,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_agent_workflows_case on public.agent_workflows(case_id);
create index if not exists idx_agent_workflows_org on public.agent_workflows(organization_id);

alter table public.agent_workflows enable row level security;

create policy "org members read agent_workflows" on public.agent_workflows
  for select using (
    (organization_id is null or public.is_org_member(organization_id))
    and (case_id is null or public.is_case_member(case_id))
    and (user_id is null or user_id = auth.uid())
    and (organization_id is not null or case_id is not null or user_id is not null)
  );

create policy "org members manage agent_workflows" on public.agent_workflows
  for all using (
    (organization_id is null or public.is_org_member(organization_id))
    and (case_id is null or public.is_case_member(case_id))
    and (user_id is null or user_id = auth.uid())
    and (organization_id is not null or case_id is not null or user_id is not null)
  )
  with check (
    (organization_id is null or public.is_org_member(organization_id))
    and (case_id is null or public.is_case_member(case_id))
    and (user_id is null or user_id = auth.uid())
    and (organization_id is not null or case_id is not null or user_id is not null)
  );


-- ---------- 2.4 SSO Providers (Org-scoped) ----------
create table if not exists public.sso_providers (
  provider_id text primary key,
  organization_id uuid references public.organizations(id) on delete cascade,
  default_organization_id text,
  provider_type text not null,
  display_name text,
  name text,
  enabled boolean not null default true,
  domain text,
  entity_id text,
  saml_entity_id text,
  saml_sso_url text,
  saml_slo_url text,
  saml_x509_cert text,
  saml_private_key text,
  saml_name_id_format text,
  saml_attribute_mapping jsonb default '{}'::jsonb,
  saml_binding text,
  saml_want_assertions_signed boolean default true,
  saml_want_response_signed boolean default true,
  oidc_issuer_url text,
  oidc_client_id text,
  oidc_client_secret text,
  oidc_discovery_url text,
  oidc_authorization_endpoint text,
  oidc_token_endpoint text,
  oidc_jwks_uri text,
  oidc_userinfo_endpoint text,
  oidc_end_session_endpoint text,
  oidc_scopes jsonb default '["openid", "email", "profile"]'::jsonb,
  oidc_response_type text,
  oidc_pkce_enabled boolean default true,
  oidc_attribute_mapping jsonb default '{}'::jsonb,
  auto_provision_users boolean default true,
  default_role text default 'LAWYER',
  allowed_domains jsonb default '[]'::jsonb,
  attribute_require_email boolean default true,
  sign_requests boolean default false,
  encrypt_assertions boolean default false,
  sso_url text,
  x509_cert text,
  issuer text,
  client_id text,
  attribute_mapping jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_sso_providers_org on public.sso_providers(organization_id);

alter table public.sso_providers enable row level security;

create policy "org admins read sso_providers" on public.sso_providers
  for select using (
    organization_id is not null and public.can_manage_org(organization_id)
  );

create policy "org admins manage sso_providers" on public.sso_providers
  for all using (
    organization_id is not null and public.can_manage_org(organization_id)
  )
  with check (
    organization_id is not null and public.can_manage_org(organization_id)
  );
