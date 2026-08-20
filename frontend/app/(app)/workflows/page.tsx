"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  GitBranch,
  Plus,
  Play,
  Copy,
  Layers,
  Sparkles,
  ShieldCheck,
  FileSearch,
  Scale,
  Award,
  ArrowRight,
  Loader2,
} from "lucide-react";
import { Button, Card } from "@/components/ui";
import { api } from "@/lib/api";
import { WorkflowCanvas } from "@/components/workflows/WorkflowCanvas";

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeWorkflow, setActiveWorkflow] = useState<any | null>(null);

  useEffect(() => {
    api.listWorkflows().then((res) => {
      setWorkflows(res.workflows || []);
      if (res.workflows?.length > 0) {
        setActiveWorkflow(res.workflows[0]);
      }
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6">
      {/* Top Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-white tracking-tight">Legal Multi-Agent Workflows</h1>
            <span className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-blue-400">
              Visual Builder v2
            </span>
          </div>
          <p className="mt-1 text-sm text-text-secondary">
            Orchestrate 6 specialist agents with synchronous and async execution, SSE telemetry, and Harvey-class reasoning.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={() => {
              const customWf = {
                id: "wf-custom-" + Date.now(),
                name: "New Custom Legal Pipeline",
                description: "Custom multi-agent workflow assembled from specialist agent library.",
                nodes: [
                  {
                    id: "node_1",
                    name: "Due Diligence Agent",
                    agent_type: "due_diligence_agent",
                    label: "Holistic Due Diligence Check",
                    dependencies: [],
                  },
                ],
              };
              setWorkflows([customWf, ...workflows]);
              setActiveWorkflow(customWf);
            }}
            className="flex items-center gap-2 bg-primary font-medium shadow-lg shadow-primary/25"
          >
            <Plus size={16} /> New Workflow
          </Button>
        </div>
      </div>

      {/* Template Gallery Bar */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-text-muted">
          <Sparkles size={14} className="text-accent" />
          <span>Pre-built Specialist Pipelines</span>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {workflows.map((wf) => {
            const isSelected = activeWorkflow?.id === wf.id;
            return (
              <Card
                key={wf.id}
                onClick={() => setActiveWorkflow(wf)}
                className={`cursor-pointer p-5 transition-all duration-200 ${
                  isSelected
                    ? "border-primary bg-primary/10 shadow-lg shadow-primary/10"
                    : "border-border bg-surface hover:border-primary/40 hover:bg-surface-elevated"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20 text-primary">
                      <GitBranch size={16} />
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-white">{wf.name}</h4>
                      <span className="text-[11px] text-text-muted">{wf.category || "General"}</span>
                    </div>
                  </div>
                  {wf.is_template && (
                    <span className="rounded bg-blue-500/10 px-2 py-0.5 text-[10px] font-medium text-blue-400">
                      TEMPLATE
                    </span>
                  )}
                </div>

                <p className="mt-3 text-xs leading-relaxed text-text-secondary line-clamp-2">{wf.description}</p>

                <div className="mt-4 flex items-center justify-between border-t border-border/60 pt-3 text-xs">
                  <span className="text-text-muted">{wf.nodes?.length || 0} Agent Steps</span>
                  <span className="flex items-center gap-1 font-medium text-primary">
                    Open Canvas <ArrowRight size={13} />
                  </span>
                </div>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Visual Workflow Canvas Area */}
      {activeWorkflow && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-text-muted">
              <Layers size={14} className="text-primary" />
              <span>Interactive Workflow Canvas — {activeWorkflow.name}</span>
            </div>
          </div>
          <WorkflowCanvas
            workflow={activeWorkflow}
            onSave={(updated) => {
              setWorkflows(workflows.map((w) => (w.id === updated.id ? updated : w)));
              setActiveWorkflow(updated);
            }}
          />
        </div>
      )}
    </div>
  );
}
