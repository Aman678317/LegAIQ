-- ============================================================
-- 007: Row Level Security — Tenant Isolation
-- Every table is scoped to organization membership.
-- ============================================================

-- Enable RLS on all tables
alter table public.organizations enable row level security;
alter table public.profiles enable row level security;
alter table public.memberships enable row level security;
alter table public.cases enable row level security;
alter table public.case_collaborators enable row level security;
alter table public.properties enable row level security;
alter table public.property_field_sources enable row level security;
alter table public.documents enable row level security;
alter table public.document_pages enable row level security;
alter table public.page_translations enable row level security;
alter table public.jobs enable row level security;
alter table public.activity_events enable row level security;
alter table public.extracted_entities enable row level security;
alter table public.persons enable row level security;
alter table public.document_chunks enable row level security;
alter table public.chat_messages enable row level security;
alter table public.ownership_nodes enable row level security;
alter table public.ownership_edges enable row level security;
alter table public.timeline_events enable row level security;
alter table public.comparison_results enable row level security;
alter table public.risks enable row level security;
alter table public.findings enable row level security;
alter table public.research_sessions enable row level security;
alter table public.research_sources enable row level security;
alter table public.drafts enable row level security;
alter table public.reports enable row level security;
alter table public.ai_runs enable row level security;
alter table public.audit_events enable row level security;

-- ---------- Profiles ----------
create policy "read own profile" on public.profiles
  for select using (auth.uid() = id);
create policy "update own profile" on public.profiles
  for update using (auth.uid() = id);

-- ---------- Organizations ----------
create policy "read own orgs" on public.organizations
  for select using (public.is_org_member(id));
create policy "create org" on public.organizations
  for insert with check (auth.uid() is not null);
create policy "update org if manager" on public.organizations
  for update using (public.can_manage_org(id));

-- ---------- Memberships ----------
create policy "read memberships of own orgs" on public.memberships
  for select using (public.is_org_member(organization_id));
create policy "manage memberships if admin" on public.memberships
  for all using (public.can_manage_org(organization_id))
  with check (public.can_manage_org(organization_id));

-- ---------- Cases ----------
create policy "read cases in own org" on public.cases
  for select using (public.is_org_member(organization_id));
create policy "create case in own org" on public.cases
  for insert with check (public.is_org_member(organization_id));
create policy "update case if org member" on public.cases
  for update using (public.is_org_member(organization_id));
create policy "delete case if admin" on public.cases
  for delete using (public.can_manage_org(organization_id));

-- ---------- Case-scoped child tables ----------
-- Helper: is the current user a member of the case's org?
create or replace function public.is_case_member(case_uuid uuid)
returns boolean
language sql
security definer set search_path = public
stable
as $$
  select exists (
    select 1 from public.cases c
    where c.id = case_uuid and public.is_org_member(c.organization_id)
  )
$$;

create or replace function public.can_manage_case(case_uuid uuid)
returns boolean
language sql
security definer set search_path = public
stable
as $$
  select exists (
    select 1 from public.cases c
    where c.id = case_uuid and public.can_manage_org(c.organization_id)
  )
$$;

-- Generic case-scoped policies applied to each child table
do $$
declare
  t text;
begin
  foreach t in array array[
    'case_collaborators', 'properties',
    'documents',
    'jobs', 'activity_events',
    'extracted_entities', 'persons', 'document_chunks', 'chat_messages',
    'ownership_nodes', 'ownership_edges', 'timeline_events',
    'comparison_results', 'risks', 'findings',
    'research_sessions', 'drafts', 'reports'
  ]
  loop
    execute format('create policy "case members read" on public.%I for select using (public.is_case_member(case_id))', t);
    execute format('create policy "case members insert" on public.%I for insert with check (public.is_case_member(case_id))', t);
    execute format('create policy "case members update" on public.%I for update using (public.is_case_member(case_id))', t);
    execute format('create policy "case admins delete" on public.%I for delete using (public.can_manage_case(case_id))', t);
  end loop;
end $$;

-- property_field_sources is scoped via properties.case_id
create policy "case members read pfs" on public.property_field_sources
  for select using (
    public.is_case_member((select p.case_id from public.properties p where p.id = property_id))
  );
create policy "case members insert pfs" on public.property_field_sources
  for insert with check (
    public.is_case_member((select p.case_id from public.properties p where p.id = property_id))
  );
create policy "case members update pfs" on public.property_field_sources
  for update using (
    public.is_case_member((select p.case_id from public.properties p where p.id = property_id))
  );
create policy "case admins delete pfs" on public.property_field_sources
  for delete using (
    public.can_manage_case((select p.case_id from public.properties p where p.id = property_id))
  );

-- document_pages is scoped via documents.case_id
create policy "case members read pages" on public.document_pages
  for select using (
    public.is_case_member((select d.case_id from public.documents d where d.id = document_id))
  );
create policy "case members insert pages" on public.document_pages
  for insert with check (
    public.is_case_member((select d.case_id from public.documents d where d.id = document_id))
  );
create policy "case members update pages" on public.document_pages
  for update using (
    public.is_case_member((select d.case_id from public.documents d where d.id = document_id))
  );
create policy "case admins delete pages" on public.document_pages
  for delete using (
    public.can_manage_case((select d.case_id from public.documents d where d.id = document_id))
  );

-- page_translations is scoped via pages -> documents -> case_id
create policy "case members read translations" on public.page_translations
  for select using (
    public.is_case_member((select d.case_id from public.documents d join public.document_pages p on p.document_id = d.id where p.id = page_id))
  );
create policy "case members insert translations" on public.page_translations
  for insert with check (
    public.is_case_member((select d.case_id from public.documents d join public.document_pages p on p.document_id = d.id where p.id = page_id))
  );
create policy "case members update translations" on public.page_translations
  for update using (
    public.is_case_member((select d.case_id from public.documents d join public.document_pages p on p.document_id = d.id where p.id = page_id))
  );
create policy "case admins delete translations" on public.page_translations
  for delete using (
    public.can_manage_case((select d.case_id from public.documents d join public.document_pages p on p.document_id = d.id where p.id = page_id))
  );

-- research_sources references session_id instead of case_id
create policy "case members read sources" on public.research_sources
  for select using (
    exists (
      select 1 from public.research_sessions s
      where s.id = session_id and public.is_case_member(s.case_id)
    )
  );

-- ---------- AI Runs & Audit (read restricted to admins) ----------
create policy "org members read ai runs" on public.ai_runs
  for select using (public.is_org_member(organization_id));

create policy "org admins read audit" on public.audit_events
  for select using (public.can_manage_org(organization_id));
create policy "system inserts audit" on public.audit_events
  for insert with check (auth.uid() is not null);
