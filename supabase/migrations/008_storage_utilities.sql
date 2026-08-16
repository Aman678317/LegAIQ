-- ============================================================
-- 008: Storage buckets, triggers, utilities
-- ============================================================

-- Private documents bucket (insert via storage policies)
insert into storage.buckets (id, name, public)
values ('case-documents', 'case-documents', false)
on conflict (id) do nothing;

insert into storage.buckets (id, name, public)
values ('case-reports', 'case-reports', false)
on conflict (id) do nothing;

-- Storage policy: users can upload into their org's folder path
-- Path format: organizations/{org_id}/cases/{case_id}/documents/{doc_id}/{filename}
create policy "authenticated can upload case docs"
  on storage.objects for insert to authenticated
  with check (
    bucket_id = 'case-documents'
    and public.is_case_member(
      (storage.foldername(name))[4]::uuid
    )
  );

create policy "case members can read case docs"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'case-documents'
    and public.is_case_member(
      (storage.foldername(name))[4]::uuid
    )
  );

create policy "case members can read reports"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'case-reports'
    and public.is_case_member(
      (storage.foldername(name))[4]::uuid
    )
  );

-- updated_at auto-touch trigger
create or replace function public.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

do $$
declare
  t text;
begin
  foreach t in array array[
    'organizations', 'profiles', 'cases', 'properties',
    'documents', 'drafts'
  ]
  loop
    execute format('drop trigger if exists touch_%I on public.%I', t, t);
    execute format(
      'create trigger touch_%I before update on public.%I
       for each row execute function public.touch_updated_at()', t, t
    );
  end loop;
end $$;

-- Case activity helper
create or replace function public.log_activity(
  p_case_id uuid,
  p_event_type text,
  p_description text,
  p_metadata jsonb default null
)
returns void
language sql
security definer set search_path = public
as $$
  insert into public.activity_events (case_id, actor_id, event_type, description, metadata)
  values (p_case_id, auth.uid(), p_event_type, p_description, p_metadata);
$$;

-- Risk summary view for case dashboards
create or replace view public.case_risk_summary as
select
  case_id,
  count(*) as total,
  count(*) filter (where level = 'CRITICAL') as critical,
  count(*) filter (where level = 'HIGH') as high,
  count(*) filter (where level = 'MEDIUM') as medium,
  count(*) filter (where level = 'LOW') as low
from public.risks
where not resolved
group by case_id;
