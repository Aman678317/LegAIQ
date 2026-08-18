"use client";

import React, { useEffect, useState } from "react";
import { Loader2, ChevronDown } from "lucide-react";
import { api } from "@/lib/api";
import { Card, Badge } from "@/components/ui";
import { formatDateTime } from "@/lib/utils";

export default function AdminAgentRunsPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    api.adminAgentRuns(100).then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>;
  if (!data) return <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;

  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-text-muted">
              <th className="px-5 py-3 font-medium">Agent</th>
              <th className="px-5 py-3 font-medium">Status</th>
              <th className="px-5 py-3 font-medium">LLM calls</th>
              <th className="px-5 py-3 font-medium">Tokens</th>
              <th className="px-5 py-3 font-medium">Cost</th>
              <th className="px-5 py-3 font-medium">Time</th>
              <th className="px-5 py-3 font-medium">Started</th>
              <th className="px-5 py-3" />
            </tr>
          </thead>
          <tbody>
            {data.items.map((run: any) => (
              <React.Fragment key={run.id}>
                <tr className="border-b border-border/50 hover:bg-bg-elevated/50">
                  <td className="px-5 py-3 font-medium text-white">{run.agent_name}</td>
                  <td className="px-5 py-3">
                    <Badge className={
                      run.status === "COMPLETED"
                        ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-400"
                        : run.status === "FAILED"
                        ? "border-red-500/30 bg-red-500/15 text-red-400"
                        : "border-blue-500/30 bg-blue-500/15 text-blue-400"
                    }>
                      {run.status}
                    </Badge>
                  </td>
                  <td className="px-5 py-3 text-white">{run.llm_calls}</td>
                  <td className="px-5 py-3 text-text-secondary">
                    {(run.prompt_tokens + run.completion_tokens).toLocaleString("en-IN")}
                  </td>
                  <td className="px-5 py-3 text-text-secondary">
                    ${(run.estimated_cost_usd || 0).toFixed(4)}
                  </td>
                  <td className="px-5 py-3 text-text-secondary">{run.elapsed_seconds}s</td>
                  <td className="px-5 py-3 text-text-secondary">{formatDateTime(run.started_at)}</td>
                  <td className="px-5 py-3 text-right">
                    <button
                      onClick={() => setExpanded(expanded === run.id ? null : run.id)}
                      className="rounded p-1 text-text-muted hover:text-white"
                    >
                      <ChevronDown size={15} className={expanded === run.id ? "rotate-180 transition-transform" : "transition-transform"} />
                    </button>
                  </td>
                </tr>
                {expanded === run.id && (
                  <tr key={`${run.id}-detail`} className="border-b border-border/50 bg-bg/50">
                    <td colSpan={8} className="px-5 py-4">
                      {run.error_message && (
                        <p className="mb-3 rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2 font-mono text-xs text-red-400">
                          {run.error_message}
                        </p>
                      )}
                      <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                        Tool calls ({run.tool_calls?.length || 0}) — every call is permission-checked and audited
                      </p>
                      <div className="space-y-1.5">
                        {(run.tool_calls || []).map((tc: any, i: number) => (
                          <div key={i} className="flex items-center justify-between rounded-lg border border-border bg-bg px-3 py-2 text-xs">
                            <span className="font-mono text-white">{tc.tool_name}</span>
                            <span className="flex items-center gap-3">
                              <span className={tc.status === "COMPLETED" ? "text-emerald-400" : "text-red-400"}>{tc.status}</span>
                              <span className="text-text-muted">{tc.duration_ms}ms</span>
                            </span>
                          </div>
                        ))}
                        {(!run.tool_calls || run.tool_calls.length === 0) && (
                          <p className="text-xs text-text-muted">No tool calls in this run.</p>
                        )}
                      </div>
                      <p className="mt-3 text-[11px] text-text-muted">
                        Iterations: {run.iterations} · chain-of-thought is never stored
                      </p>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
            {data.items.length === 0 && (
              <tr><td colSpan={8} className="px-5 py-8 text-center text-text-muted">No agent runs yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
