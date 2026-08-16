import { createClient } from "./supabase";

export interface OrgMembership {
  organization: { id: string; name: string; slug: string };
  role: string;
}

export async function getUserOrgs(): Promise<OrgMembership[]> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return [];

  const { data } = await supabase
    .from("memberships")
    .select("role, organizations(id, name, slug)")
    .eq("user_id", user.id);

  return (data || []).map((m: any) => ({
    organization: m.organizations,
    role: m.role,
  }));
}

export async function ensureDefaultOrg(): Promise<string | null> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return null;

  const orgs = await getUserOrgs();
  if (orgs.length > 0) return orgs[0].organization.id;

  // Create a personal org on first login
  const baseName = user.email?.split("@")[0] || "my-workspace";
  const slug = `${baseName}-${Date.now().toString(36)}`;
  const { data: org } = await supabase
    .from("organizations")
    .insert({ name: `${baseName}'s Workspace`, slug })
    .select()
    .single();

  if (!org) return null;
  await supabase.from("memberships").insert({
    organization_id: org.id,
    user_id: user.id,
    role: "OWNER",
  });
  return org.id;
}
