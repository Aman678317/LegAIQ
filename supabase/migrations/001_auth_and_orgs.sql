-- ============================================================
-- 001: Organizations, Profiles, Memberships
-- Jurisiva AI — India-first legal AI platform
-- ============================================================

-- Organizations (tenants)
create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  plan text not null default 'FREE' check (plan in ('FREE', 'PROFESSIONAL', 'FIRM', 'ENTERPRISE')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Extended user profile (1:1 with auth.users)
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  full_name text,
  avatar_url text,
  default_org_id uuid references public.organizations(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Memberships: user <-> organization with role
create table if not exists public.memberships (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('OWNER', 'ADMIN', 'LAWYER', 'REVIEWER', 'STAFF', 'CLIENT')),
  created_at timestamptz not null default now(),
  unique (organization_id, user_id)
);

create index if not exists idx_memberships_user on public.memberships(user_id);
create index if not exists idx_memberships_org on public.memberships(organization_id);

-- Automatically create a profile when a user signs up
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, email, full_name)
  values (new.id, new.email, coalesce(new.raw_user_meta_data->>'full_name', null))
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Helper: current user's role in an org (null if not a member)
create or replace function public.user_role_in_org(org_id uuid)
returns text
language sql
security definer set search_path = public
stable
as $$
  select role from public.memberships
  where organization_id = org_id and user_id = auth.uid()
$$;

-- Helper: is the current user a member of the org (any role)?
create or replace function public.is_org_member(org_id uuid)
returns boolean
language sql
security definer set search_path = public
stable
as $$
  select exists (
    select 1 from public.memberships
    where organization_id = org_id and user_id = auth.uid()
  )
$$;

-- Helper: can the current user manage the org (OWNER or ADMIN)?
create or replace function public.can_manage_org(org_id uuid)
returns boolean
language sql
security definer set search_path = public
stable
as $$
  select exists (
    select 1 from public.memberships
    where organization_id = org_id and user_id = auth.uid()
      and role in ('OWNER', 'ADMIN')
  )
$$;
