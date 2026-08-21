"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, UserPlus, Trash2, ShieldCheck, CreditCard, Cpu, RefreshCw, CheckCircle2, XCircle, Terminal, Sparkles, Lock } from "lucide-react";
import { api } from "@/lib/api";
import { getUserOrgs } from "@/lib/auth";
import { Button, Card, Badge } from "@/components/ui";
import { formatDate } from "@/lib/utils";
import { checkOllamaStatus, queryLocalOllama, getOllamaBaseUrl, OllamaStatus } from "@/lib/ollama";

const ROLES = ["OWNER", "ADMIN", "LAWYER", "REVIEWER", "STAFF", "CLIENT"];

export default function SettingsPage() {
  const [orgs, setOrgs] = useState<any[]>([]);
  const [activeOrg, setActiveOrg] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [billing, setBilling] = useState<any>(null);

  // Ollama states
  const [ollamaUrl, setOllamaUrl] = useState("");
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus>({
    online: false,
    models: [],
    activeModel: null,
  });
  const [testingOllama, setTestingOllama] = useState(false);
  const [ollamaTestResult, setOllamaTestResult] = useState<string | null>(null);

  // Add member form
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("LAWYER");
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  async function loadOllama(urlToTest?: string) {
    setTestingOllama(true);
    try {
      const status = await checkOllamaStatus(urlToTest);
      setOllamaStatus(status);
    } catch {
      setOllamaStatus({ online: false, models: [], activeModel: null });
    } finally {
      setTestingOllama(false);
    }
  }

  async function testOllamaCompletion() {
    setTestingOllama(true);
    setOllamaTestResult(null);
    try {
      const model = ollamaStatus.activeModel || "llama3";
      const res = await queryLocalOllama(
        "Explain Section 9(1)(i) of Income Tax Act in 1 sentence.",
        "You are Jurisiva AI Indian legal intelligence assistant.",
        model,
        ollamaUrl || undefined
      );
      if (res && res.text) {
        setOllamaTestResult(`Success (${res.duration_ms}ms, model: ${res.model}): ${res.text}`);
      } else {
        setOllamaTestResult("Ollama responded with empty content or error. Verify model weights are downloaded.");
      }
    } catch (e: any) {
      setOllamaTestResult(`Failed: ${e.message}`);
    } finally {
      setTestingOllama(false);
    }
  }

  function handleSaveOllamaUrl(e: React.FormEvent) {
    e.preventDefault();
    if (typeof window !== "undefined") {
      localStorage.setItem("jurisiva_ollama_url", ollamaUrl);
      loadOllama(ollamaUrl);
    }
  }

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
      const defaultUrl = getOllamaBaseUrl();
      setOllamaUrl(defaultUrl);
      loadOllama(defaultUrl);
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
        <h1 className="text-2xl font-semibold text-white">Settings & AI Configuration</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Configure organization settings, roles, and local Ollama AI connectivity.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {/* Ollama Local AI Card */}
      <Card className="p-6">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400">
              <Cpu size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold text-white">Ollama Local AI Engine</h2>
                <Badge
                  className={
                    ollamaStatus.online
                      ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-400"
                      : "border-amber-500/30 bg-amber-500/15 text-amber-400"
                  }
                >
                  {ollamaStatus.online ? (
                    <span className="flex items-center gap-1">
                      <CheckCircle2 size={12} /> Connected {ollamaStatus.latency_ms !== undefined ? `(${ollamaStatus.latency_ms}ms)` : ""}
                    </span>
                  ) : (
                    <span className="flex items-center gap-1">
                      <XCircle size={12} /> Offline / Fallback
                    </span>
                  )}
                </Badge>
              </div>
              <p className="text-xs text-text-muted">
                100% private on-device LLM inference & embeddings for Indian law without third-party API keys.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="secondary"
              disabled={testingOllama}
              onClick={() => loadOllama(ollamaUrl)}
            >
              <RefreshCw size={13} className={testingOllama ? "animate-spin" : ""} />
              Check Status
            </Button>
            <Button
              size="sm"
              disabled={testingOllama}
              onClick={testOllamaCompletion}
            >
              <Sparkles size={13} />
              Test Completion
            </Button>
          </div>
        </div>

        {/* Ollama endpoint config */}
        <form onSubmit={handleSaveOllamaUrl} className="mt-5 flex flex-wrap gap-2.5">
          <div className="min-w-64 flex-1">
            <label className="mb-1 block text-xs font-medium text-text-secondary">Ollama Server URL</label>
            <input
              type="text"
              value={ollamaUrl}
              onChange={(e) => setOllamaUrl(e.target.value)}
              placeholder="http://localhost:11434"
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-xs font-mono text-white outline-none focus:border-primary"
            />
          </div>
          <div className="flex items-end">
            <Button type="submit" size="sm" variant="secondary">
              Save URL
            </Button>
          </div>
        </form>

        {/* Installed Models list */}
        {ollamaStatus.online && (
          <div className="mt-4 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3.5">
            <div className="text-xs font-semibold text-emerald-400">
              Installed Models ({ollamaStatus.models.length}):
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {ollamaStatus.models.map((m) => (
                <span
                  key={m}
                  className={`rounded-md px-2 py-1 font-mono text-[11px] ${
                    m === ollamaStatus.activeModel
                      ? "bg-emerald-500/20 font-semibold text-emerald-300 ring-1 ring-emerald-400/40"
                      : "bg-bg text-text-secondary"
                  }`}
                >
                  {m}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Test Result Box */}
        {ollamaTestResult && (
          <div className="mt-4 rounded-lg border border-border bg-bg p-3 text-xs">
            <div className="font-semibold text-white">Diagnostic Output:</div>
            <p className="mt-1 font-mono text-text-secondary">{ollamaTestResult}</p>
          </div>
        )}

        {/* Quick terminal instructions */}
        <div className="mt-4 rounded-lg border border-border bg-bg p-3.5 text-xs text-text-muted">
          <div className="flex items-center gap-1.5 font-semibold text-white">
            <Terminal size={14} className="text-primary" /> Start Ollama in your Terminal:
          </div>
          <div className="mt-2 space-y-1.5 font-mono text-[11px]">
            <div className="rounded bg-bg-elevated px-2 py-1 text-slate-300">
              <span className="text-text-muted"># Windows PowerShell:</span> $env:OLLAMA_ORIGINS="*" ; ollama serve
            </div>
            <div className="rounded bg-bg-elevated px-2 py-1 text-slate-300">
              <span className="text-text-muted"># Pull models:</span> ollama pull llama3 ; ollama pull nomic-embed-text
            </div>
          </div>
        </div>
      </Card>

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
                    <CreditCard size={15} className="text-primary" /> Plan & usage
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
