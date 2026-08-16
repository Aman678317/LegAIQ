"use client";

import { useEffect, useState } from "react";
import { Loader2, CheckCircle2, XCircle, Activity, HardDrive, Cpu } from "lucide-react";
import { api } from "@/lib/api";
import { Card, Badge } from "@/components/ui";
import { formatBytes, formatDateTime, STATUS_STYLES } from "@/lib/utils";

export default function AdminOverviewPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.adminOverview().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) {
    return <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>;
  }
  if (!data) {
    return <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  const { counts, storage_bytes, job_states, recent_jobs, providers, worker, database } = data;

  return (
    <div className="space-y-6">
      {/* Count cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Organizations", value: counts.organizations },
          { label: "Users", value: counts.users },
          { label: "Cases", value: counts.cases },
          { label: "Documents", value: counts.documents },
        ].map((c) => (
          <Card key={c.label} className="p-5">
            <div className="text-3xl font-semibold text-white">{c.value}</div>
            <div className="mt-1 text-xs text-text-muted">{c.label}</div>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Health */}
        <Card className="p-6">
          <h2 className="flex items-center gap-2 text-base font-semibold text-white">
            <Activity size={16} className="text-primary" /> System health
          </h2>
          <div className="mt-4 space-y-3">
            <HealthRow ok={database.connected} label="Database (PostgreSQL)" />
            <HealthRow ok={worker.healthy} label={`Worker — ${worker.stuck_running_jobs} stuck RUNNING job(s)`} />
            <div className="flex items-center justify-between rounded-lg border border-border bg-bg px-4 py-3">
              <span className="flex items-center gap-2 text-sm text-text-secondary">
                <HardDrive size={15} className="text-text-muted" /> Document storage
              </span>
              <span className="text-sm font-medium text-white">{formatBytes(storage_bytes)}</span>
            </div>
          </div>

          <h3 className="mt-6 flex items-center gap-2 text-sm font-semibold text-white">
            <Cpu size={14} className="text-primary" /> Providers
          </h3>
          <p className="mt-1 text-[11px] text-text-muted">Configured status only — keys are never exposed.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {Object.entries(providers).map(([name, value]) => (
              <Badge
                key={name}
                className={
                  value === true
                    ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-400"
                    : value === false
                    ? "border-slate-500/30 bg-slate-500/15 text-slate-400"
                    : "border-blue-500/30 bg-blue-500/15 text-blue-300"
                }
              >
                {name}: {typeof value === "boolean" ? (value ? "configured" : "not configured") : String(value)}
              </Badge>
            ))}
          </div>
        </Card>

        {/* Jobs */}
        <Card className="p-6">
          <h2 className="text-base font-semibold text-white">Jobs by state</h2>
          <div className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-6">
            {["QUEUED", "RUNNING", "COMPLETED", "FAILED", "RETRYING", "CANCELLED"].map((s) => (
              <div key={s} className="rounded-lg border border-border bg-bg px-3 py-2.5 text-center">
                <div className="text-xl font-semibold text-white">{job_states[s] || 0}</div>
                <div className="text-[10px] uppercase text-text-muted">{s.slice(0, 5)}</div>
              </div>
            ))}
          </div>

          <h3 className="mt-6 text-sm font-semibold text-white">Recent jobs</h3>
          <div className="mt-3 space-y-2">
            {recent_jobs.length === 0 ? (
              <p className="text-sm text-text-muted">No jobs yet.</p>
            ) : (
              recent_jobs.map((job: any) => (
                <div key={job.id} className="flex items-center justify-between rounded-lg border border-border bg-bg px-3 py-2">
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-white">{job.job_type}</div>
                    <div className="text-[11px] text-text-muted">{formatDateTime(job.created_at)}</div>
                  </div>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS_STYLES[job.state] || "bg-slate-500/15 text-slate-400"}`}>
                    {job.state}{job.progress != null && job.state === "RUNNING" ? ` ${job.progress}%` : ""}
                  </span>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

function HealthRow({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-bg px-4 py-3">
      <span className="text-sm text-text-secondary">{label}</span>
      {ok ? (
        <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-400">
          <CheckCircle2 size={14} /> Healthy
        </span>
      ) : (
        <span className="flex items-center gap-1.5 text-xs font-medium text-red-400">
          <XCircle size={14} /> Check required
        </span>
      )}
    </div>
  );
}
