"use client";

import { useEffect, useState } from "react";
import { Loader2, UserPlus, Trash2, ShieldCheck, CreditCard } from "lucide-react";
import { api } from "@/lib/api";
import { getUserOrgs } from "@/lib/auth";
import { Button, Card, Badge } from "@/components/ui";
import { formatDate } from "@/lib/utils";

const ROLES = ["OWNER", "ADMIN", "LAWYER", "REVIEWER", "STAFF", "CLIENT"];

export default function SettingsPage() {
  const [orgs, setOrgs] = useState<any[]>([]);
  const [activeOrg, setActiveOrg] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [billing, setBilling] = useState<any>(null);

  // Add member form
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("LAWYER");
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  async function loadMembers(org: any) {
    setError(null);
    try {
      setMembers(await api.listMembers(org.id));
    } catch (e: any) {
      setError(e.message);  // non-managers get a clear 403 message
      setMembers([]);
    }
  }

  useEffect(() => {
    async function init() {
      const orgList = await getUserOrgs();
      setOrgs(orgList);
      if (orgList.length > 0) {
        setActiveOrg(orgList[0]);
        loadMembers(orgList[0].organization);
        api.getBilling(orgList[0].organization.id)
          .then(setBilling)
          .catch(() => setBilling(null));
      }
      setLoading(false);
    }
    init();
  }, []);

  async function addMember(e: React.FormEvent) {
    e.preventDefault();
    if (!activeOrg) return;
    setAdding(true);
    setError(null);
    try {
      await api.addMember(activeOrg.organization.id, email, role);
      setEmail("");
      await loadMembers(activeOrg);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setAdding(false);
    }
  }

  async function changeRole(userId: string, newRole: string) {
    if (!activeOrg) return;
    setBusy(userId);
    try {
      await api.updateMemberRole(activeOrg.organization.id, userId, newRole);
      await loadMembers(activeOrg);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  }

  async function removeMember(userId: string, name: string) {
    if (!activeOrg || !confirm(`Remove ${name} from this organization?`)) return;
    setBusy(userId);
    try {
      await api.removeMember(activeOrg.organization.id, userId);
      await loadMembers(activeOrg);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  }

  if (loading) {
    return <div className="flex h-96 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Settings</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Manage your organization&rsquo;s members and their roles. All changes are audit-logged.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {/* Org switcher */}
      {orgs.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {orgs.map((m) => (
            <button
              key={m.organization.id}
              onClick={() => { setActiveOrg(m); loadMembers(m); }}
              className={`rounded-lg px-3.5 py-2 text-xs font-medium transition-colors ${
                activeOrg?.organization.id === m.organization.id
                  ? "bg-primary/15 text-blue-300"
                  : "text-text-secondary hover:bg-bg-elevated hover:text-white"
              }`}
            >
              {m.organization.name} <span className="text-text-muted">· {m.role}</span>
            </button>
          ))}
        </div>
      )}

      {activeOrg ? (
        <>
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">{activeOrg.organization.name}</h2>
                <p className="text-xs text-text-muted">You are {activeOrg.role}</p>
              </div>
              <Badge className="border-primary/30 bg-primary/10 text-blue-300">
                <ShieldCheck size={11} className="mr-1" /> Roles enforced server-side
              </Badge>
            </div>
          </Card>

          {/* Plan & usage */}
          {billing && (
            <Card className="p-6">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-white">
                    <CreditCard size={15} className="text-primary" /> Plan &amp; usage
                  </h3>
                  <p className="mt-1 text-xs text-text-muted">
                    Current period: {formatDate(billing.period?.start)} – {formatDate(billing.period?.end)}
                  </p>
                </div>
                <Badge className="border-primary/30 bg-primary/10 text-blue-300">
                  {billing.plan?.name || "Free"}
                  {billing.status === "TRIALING" ? " (trial)" : ""}
                </Badge>
              </div>

              <div className="mt-5 grid gap-4 sm:grid-cols-3">
                {[
                  { label: "Pages processed", used: billing.usage?.pages ?? 0, limit: billing.limits?.pages_per_month },
                  { label: "AI runs", used: billing.usage?.ai_runs ?? 0, limit: billing.limits?.ai_runs_per_month },
                  { label: "Cases", used: billing.usage?.cases ?? 0, limit: billing.limits?.cases },
                ].map((row) => {
                  const pct = row.limit ? Math.min(100, Math.round((row.used / row.limit) * 100)) : null;
                  return (
                    <div key={row.label} className="rounded-lg border border-border bg-bg p-4">
                      <div className="text-xs text-text-muted">{row.label}</div>
                      <div className="mt-1 text-lg font-semibold text-white">
                        {row.used.toLocaleString("en-IN")}
                        <span className="text-sm font-normal text-text-muted">
                          {row.limit != null ? ` / ${row.limit.toLocaleString("en-IN")}` : " · unlimited"}
                        </span>
                      </div>
                      {pct != null && (
                        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-bg-elevated">
                          <div
                            className={`h-full rounded-full ${pct >= 100 ? "bg-red-500" : pct >= 80 ? "bg-amber-500" : "bg-primary"}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              <p className="mt-4 rounded-lg border border-border bg-bg px-4 py-3 text-xs leading-relaxed text-text-muted">
                Usage is metered from real document processing and AI runs. Online
                checkout is not enabled on this deployment — contact
                sales@jurisiva.ai to change plans. No charges are simulated.
              </p>
            </Card>
          )}

          {/* Add member */}
          <Card className="p-6">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-white">
              <UserPlus size={15} className="text-primary" /> Add member
            </h3>
            <p className="mt-1 text-xs text-text-muted">
              The person must already have a Jurisiva account with that email.
            </p>
            <form onSubmit={addMember} className="mt-4 flex flex-wrap gap-3">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="colleague@firm.com"
                className="min-w-64 flex-1 rounded-lg border border-border bg-bg px-3.5 py-2.5 text-sm text-white placeholder-text-muted outline-none focus:border-primary"
              />
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="rounded-lg border border-border bg-bg px-3.5 py-2.5 text-sm text-white outline-none focus:border-primary"
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
              <Button type="submit" disabled={adding}>
                {adding && <Loader2 size={14} className="animate-spin" />}
                Add
              </Button>
            </form>
          </Card>

          {/* Members */}
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-text-muted">
                    <th className="px-5 py-3 font-medium">Member</th>
                    <th className="px-5 py-3 font-medium">Role</th>
                    <th className="px-5 py-3 font-medium">Joined</th>
                    <th className="px-5 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((m: any) => (
                    <tr key={m.id} className="border-b border-border/50 hover:bg-bg-elevated/50">
                      <td className="px-5 py-3">
                        <div className="font-medium text-white">{m.full_name || m.email}</div>
                        <div className="text-xs text-text-muted">{m.email}</div>
                      </td>
                      <td className="px-5 py-3">
                        <select
                          value={m.role}
                          disabled={busy === m.user_id}
                          onChange={(e) => changeRole(m.user_id, e.target.value)}
                          className="rounded-lg border border-border bg-bg px-2.5 py-1.5 text-xs text-white outline-none focus:border-primary"
                        >
                          {ROLES.map((r) => (
                            <option key={r} value={r}>{r}</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-5 py-3 text-text-secondary">{formatDate(m.created_at)}</td>
                      <td className="px-5 py-3 text-right">
                        <button
                          onClick={() => removeMember(m.user_id, m.full_name || m.email)}
                          disabled={busy === m.user_id}
                          className="rounded-lg p-2 text-text-muted transition-colors hover:bg-red-500/10 hover:text-red-400"
                          title="Remove member"
                        >
                          <Trash2 size={15} />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {members.length === 0 && (
                    <tr><td colSpan={4} className="px-5 py-8 text-center text-text-muted">
                      {error ? "You need OWNER or ADMIN role to view members." : "No members found."}
                    </td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      ) : (
        <Card className="p-8 text-center text-sm text-text-secondary">
          No organization found. Create a case first to initialize your workspace.
        </Card>
      )}
    </div>
  );
}
