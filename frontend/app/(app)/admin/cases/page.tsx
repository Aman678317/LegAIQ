"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { Card, Badge } from "@/components/ui";
import { formatDate, formatDateTime, STATUS_STYLES, CASE_TYPES } from "@/lib/utils";

export default function AdminCasesPage() {
  const [data, setData] = useState<any>(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    api.adminCases(100, 0, status || undefined)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [status]);

  if (error) return <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>;
  if (!data) return <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {["", "ACTIVE", "ARCHIVED", "CLOSED"].map((s) => (
          <button
            key={s}
            onClick={() => setStatus(s)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              status === s ? "bg-primary/15 text-blue-300" : "text-text-secondary hover:bg-bg-elevated hover:text-white"
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
                <th className="px-5 py-3 font-medium">Case</th>
                <th className="px-5 py-3 font-medium">Type</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Documents</th>
                <th className="px-5 py-3 font-medium">Updated</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((c: any) => (
                <tr key={c.id} className="border-b border-border/50 hover:bg-bg-elevated/50">
                  <td className="px-5 py-3">
                    <Link href={`/cases/${c.id}`} className="font-medium text-white hover:text-blue-300">
                      {c.name}
                    </Link>
                    <div className="font-mono text-[11px] text-text-muted">{c.id.slice(0, 8)}…</div>
                  </td>
                  <td className="px-5 py-3">
                    <Badge>{CASE_TYPES.find((t) => t.value === c.case_type)?.label || c.case_type}</Badge>
                  </td>
                  <td className="px-5 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS_STYLES[c.status] || "bg-slate-500/15 text-slate-400"}`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-white">{c.document_count}</td>
                  <td className="px-5 py-3 text-text-secondary">{formatDate(c.updated_at)}</td>
                </tr>
              ))}
              {data.items.length === 0 && (
                <tr><td colSpan={5} className="px-5 py-8 text-center text-text-muted">No cases.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
