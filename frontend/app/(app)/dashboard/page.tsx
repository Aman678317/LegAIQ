"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Plus, FolderOpen, FileText, AlertTriangle, ArrowRight, Loader2,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { ensureDefaultOrg } from "@/lib/auth";
import { Button, Card, Badge } from "@/components/ui";
import { formatDateTime, CASE_TYPES, INDIAN_STATES } from "@/lib/utils";

export default function DashboardPage() {
  const [cases, setCases] = useState<any[]>([]);
  const [orgId, setOrgId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  // Create form state
  const [name, setName] = useState("");
  const [caseType, setCaseType] = useState("PROPERTY");
  const [state, setState] = useState("");
  const [district, setDistrict] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const org = (await ensureDefaultOrg()) || "default-org";
        setOrgId(org);
        const data = await api.listCases(org);
        setCases(data?.items || []);
      } catch (e: any) {
        try {
          const fallbackData = await api.listCases("default-org");
          setCases(fallbackData?.items || []);
        } catch {
          setCases([]);
        }
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!orgId) return;
    setCreating(true);
    try {
      const newCase = await api.createCase({
        name, case_type: caseType, organization_id: orgId,
        jurisdiction_state: state || undefined,
        jurisdiction_district: district || undefined,
        description: description || undefined,
      });
      window.location.href = `/cases/${newCase.id}`;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create case");
      setCreating(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Cases</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Your organization&rsquo;s legal matters and property workspaces.
          </p>
        </div>
        <Button onClick={() => setShowCreate(!showCreate)}>
          <Plus size={16} />
          New Case
        </Button>
      </div>

      {error && (
        <div className="mt-6 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {showCreate && (
        <Card className="mt-6 p-6">
          <h2 className="text-base font-semibold text-white">Create a new case</h2>
          <form onSubmit={handleCreate} className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className="mb-1.5 block text-sm text-text-secondary">Case name *</label>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Whitefield property — Sy. No. 124/3"
                className="w-full rounded-lg border border-border bg-bg px-3.5 py-2.5 text-sm text-white placeholder-text-muted outline-none focus:border-primary"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm text-text-secondary">Case type</label>
              <select
                value={caseType}
                onChange={(e) => setCaseType(e.target.value)}
                className="w-full rounded-lg border border-border bg-bg px-3.5 py-2.5 text-sm text-white outline-none focus:border-primary"
              >
                {CASE_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-sm text-text-secondary">State</label>
              <select
                value={state}
                onChange={(e) => setState(e.target.value)}
                className="w-full rounded-lg border border-border bg-bg px-3.5 py-2.5 text-sm text-white outline-none focus:border-primary"
              >
                <option value="">Select state…</option>
                {INDIAN_STATES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-sm text-text-secondary">District</label>
              <input
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                placeholder="e.g., Bengaluru Urban"
                className="w-full rounded-lg border border-border bg-bg px-3.5 py-2.5 text-sm text-white placeholder-text-muted outline-none focus:border-primary"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1.5 block text-sm text-text-secondary">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                placeholder="Brief description of the matter"
                className="w-full rounded-lg border border-border bg-bg px-3.5 py-2.5 text-sm text-white placeholder-text-muted outline-none focus:border-primary"
              />
            </div>
            <div className="sm:col-span-2">
              <Button type="submit" disabled={creating}>
                {creating && <Loader2 size={16} className="animate-spin" />}
                Create Case
              </Button>
            </div>
          </form>
        </Card>
      )}

      {cases.length === 0 ? (
        <Card className="mt-8 flex flex-col items-center justify-center p-16 text-center">
          <FolderOpen size={40} className="mb-4 text-text-muted" />
          <h3 className="text-base font-semibold text-white">No cases yet</h3>
          <p className="mt-2 max-w-sm text-sm text-text-secondary">
            Create your first case to start uploading documents, building the
            ownership chain, and running AI analysis.
          </p>
          <Button onClick={() => setShowCreate(true)} className="mt-6">
            <Plus size={16} />
            Start a Property Case
          </Button>
        </Card>
      ) : (
        <div className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {cases.map((c) => (
            <Link key={c.id} href={`/cases/${c.id}`}>
              <Card className="group h-full p-5 transition-colors hover:border-primary/40">
                <div className="flex items-start justify-between">
                  <Badge className="border-primary/30 bg-primary/10 text-blue-300">
                    {CASE_TYPES.find((t) => t.value === c.case_type)?.label || c.case_type}
                  </Badge>
                  {c.status === "ARCHIVED" && (
                    <Badge className="border-slate-500/30 bg-slate-500/15 text-slate-400">Archived</Badge>
                  )}
                </div>
                <h3 className="mt-3 line-clamp-2 text-base font-semibold text-white group-hover:text-blue-300">
                  {c.name}
                </h3>
                <p className="mt-1 text-xs text-text-muted">
                  {c.jurisdiction_state || "Jurisdiction not set"} · Updated {formatDateTime(c.updated_at)}
                </p>
                <div className="mt-4 flex items-center gap-4 text-xs text-text-secondary">
                  <span className="flex items-center gap-1.5">
                    <FileText size={13} className="text-text-muted" />
                    Documents
                  </span>
                  <span className="flex items-center gap-1.5">
                    <AlertTriangle size={13} className="text-text-muted" />
                    Risks
                  </span>
                  <ArrowRight size={14} className="ml-auto text-text-muted transition-transform group-hover:translate-x-1 group-hover:text-primary" />
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
