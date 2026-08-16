"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui";
import { formatDateTime, STATUS_STYLES } from "@/lib/utils";

export default function AdminJobsPage() {
  const [data, setData] = useState<any>(null);
  const [state, setState] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    api.adminJobs(100, 0, state || undefined)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [state]);

  if (error) return <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>;
  if (!data) return <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {["", "QUEUED", "RUNNING", "COMPLETED", "FAILED", "RETRYING"].map((s) => (
          <button
            key={s}
            onClick={() => setState(s)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              state === s ? "bg-primary/15 text-blue-300" : "text-text-secondary hover:bg-bg-elevated hover:text-white"
            }`}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-text-muted">
                <th className="px-5 py-3 font-medium">Job</th>
                <th className="px-5 py-3 font-medium">Type</th>
                <th className="px-5 py-3 font-medium">State</th>
                <th className="px-5 py-3 font-medium">Attempts</th>
                <th className="px-5 py-3 font-medium">Created</th>
                <th className="px-5 py-3 font-medium">Error</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((job: any) => (
                <tr key={job.id} className="border-b border-border/50 hover:bg-bg-elevated/50">
                  <td className="px-5 py-3 font-mono text-[11px] text-text-muted">{job.id.slice(0, 8)}…</td>
                  <td className="px-5 py-3 font-medium text-white">{job.job_type}</td>
                  <td className="px-5 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS_STYLES[job.state] || "bg-slate-500/15 text-slate-400"}`}>
                      {job.state}{job.progress != null && job.state === "RUNNING" ? ` ${job.progress}%` : ""}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-white">{job.attempts}/{job.max_attempts}</td>
                  <td className="px-5 py-3 text-text-secondary">{formatDateTime(job.created_at)}</td>
                  <td className="max-w-xs px-5 py-3">
                    <span className="block truncate text-xs text-red-400" title={job.error_message || ""}>
                      {job.error_message || "—"}
                    </span>
                  </td>
                </tr>
              ))}
              {data.items.length === 0 && (
                <tr><td colSpan={6} className="px-5 py-8 text-center text-text-muted">No jobs.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
