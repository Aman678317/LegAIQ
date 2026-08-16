"use client";

import { useEffect, useState } from "react";
import { Loader2, ScrollText } from "lucide-react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui";
import { formatDateTime } from "@/lib/utils";

export default function AdminAuditPage() {
  const [data, setData] = useState<any>(null);
  const [actions, setActions] = useState<string[]>([]);
  const [action, setAction] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.adminAuditActions().then((r) => setActions(r.actions)).catch(() => {});
    load();
  }, []);

  function load(actionFilter?: string) {
    setData(null);
    api.adminAuditEvents(200, 0, actionFilter || undefined)
      .then(setData)
      .catch((e) => setError(e.message));
  }

  useEffect(() => { load(action || undefined); }, [action]);

  if (error && !data) {
    return <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setAction("")}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
            action === "" ? "bg-primary/15 text-blue-300" : "text-text-secondary hover:bg-bg-elevated hover:text-white"
          }`}
        >
          All actions
        </button>
        {actions.map((a) => (
          <button
            key={a}
            onClick={() => setAction(a)}
            className={`rounded-lg px-3 py-1.5 font-mono text-xs transition-colors ${
              action === a ? "bg-primary/15 text-blue-300" : "text-text-secondary hover:bg-bg-elevated hover:text-white"
            }`}
          >
            {a}
          </button>
        ))}
      </div>

      {!data ? (
        <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>
      ) : data.items.length === 0 ? (
        <Card className="flex flex-col items-center p-12 text-center">
          <ScrollText size={32} className="mb-3 text-text-muted" />
          <p className="text-sm text-text-secondary">
            No audit events yet. Member changes, uploads, downloads, and admin actions will appear here.
          </p>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-text-muted">
                  <th className="px-5 py-3 font-medium">Time</th>
                  <th className="px-5 py-3 font-medium">Action</th>
                  <th className="px-5 py-3 font-medium">Resource</th>
                  <th className="px-5 py-3 font-medium">Details</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((event: any) => (
                  <tr key={event.id} className="border-b border-border/50 hover:bg-bg-elevated/50">
                    <td className="whitespace-nowrap px-5 py-3 text-text-secondary">{formatDateTime(event.created_at)}</td>
                    <td className="px-5 py-3">
                      <span className="rounded-md bg-bg-elevated px-2 py-0.5 font-mono text-xs text-blue-300">
                        {event.action}
                      </span>
                    </td>
                    <td className="px-5 py-3 font-mono text-[11px] text-text-muted">
                      {event.resource_type ? `${event.resource_type}:${(event.resource_id || "").slice(0, 8)}…` : "—"}
                    </td>
                    <td className="max-w-md px-5 py-3">
                      <code className="block truncate text-xs text-text-secondary" title={JSON.stringify(event.metadata)}>
                        {event.metadata ? JSON.stringify(event.metadata) : "—"}
                      </code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
