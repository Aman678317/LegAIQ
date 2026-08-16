"use client";

import { useEffect, useState } from "react";
import { Loader2, Cpu, Bot } from "lucide-react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui";

export default function AdminAiUsagePage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.adminAiUsage().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>;
  if (!data) return <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;

  const { totals, by_workflow, by_agent } = data;

  return (
    <div className="space-y-6">
      {/* Totals */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {[
          { label: "AI runs", value: totals.ai_runs },
          { label: "Agent runs", value: totals.agent_runs },
          { label: "Prompt tokens", value: totals.prompt_tokens.toLocaleString("en-IN") },
          { label: "Completion tokens", value: totals.completion_tokens.toLocaleString("en-IN") },
          { label: "Est. cost (USD)", value: `$${totals.estimated_cost_usd.toFixed(4)}` },
        ].map((c) => (
          <Card key={c.label} className="p-5">
            <div className="text-2xl font-semibold text-white">{c.value}</div>
            <div className="mt-1 text-xs text-text-muted">{c.label}</div>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* By workflow */}
        <Card className="p-6">
          <h2 className="flex items-center gap-2 text-base font-semibold text-white">
            <Cpu size={16} className="text-primary" /> By workflow
          </h2>
          <div className="mt-4 space-y-2">
            {Object.entries(by_workflow as Record<string, any>).length === 0 ? (
              <p className="text-sm text-text-muted">No AI runs recorded yet.</p>
            ) : (
              Object.entries(by_workflow).map(([name, u]: [string, any]) => (
                <UsageRow key={name} name={name} usage={u} />
              ))
            )}
          </div>
        </Card>

        {/* By agent */}
        <Card className="p-6">
          <h2 className="flex items-center gap-2 text-base font-semibold text-white">
            <Bot size={16} className="text-accent" /> By agent
          </h2>
          <div className="mt-4 space-y-2">
            {Object.entries(by_agent as Record<string, any>).length === 0 ? (
              <p className="text-sm text-text-muted">No agent runs recorded yet.</p>
            ) : (
              Object.entries(by_agent).map(([name, u]: [string, any]) => (
                <UsageRow key={name} name={name} usage={u} />
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

function UsageRow({ name, usage }: { name: string; usage: any }) {
  const maxCount = 1; // relative bars within a card are per-list; simple absolute display instead
  return (
    <div className="rounded-lg border border-border bg-bg px-4 py-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium capitalize text-white">{name.replace(/_/g, " ")}</span>
        <span className="text-xs text-text-muted">
          {usage.count} run{usage.count === 1 ? "" : "s"}
          {usage.failed > 0 && <span className="text-red-400"> · {usage.failed} failed</span>}
        </span>
      </div>
      <div className="mt-1.5 flex items-center gap-4 text-[11px] text-text-secondary">
        <span>{(usage.prompt_tokens + usage.completion_tokens).toLocaleString("en-IN")} tokens</span>
        <span>${usage.estimated_cost_usd.toFixed(4)}</span>
      </div>
    </div>
  );
}
