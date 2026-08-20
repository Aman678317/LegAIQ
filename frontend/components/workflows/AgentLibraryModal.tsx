"use client";

import { useEffect, useState } from "react";
import { X, ShieldCheck, FileSearch, AlertTriangle, Scale, FileCode, Award, Plus, Check } from "lucide-react";
import { api } from "@/lib/api";
import { Button, Card } from "@/components/ui";

const AGENT_ICONS: Record<string, any> = {
  due_diligence_agent: ShieldCheck,
  title_examiner_agent: FileSearch,
  risk_auditor_agent: AlertTriangle,
  litigation_strategist_agent: Scale,
  contract_reviewer_agent: FileCode,
  bsa_compliance_agent: Award,
};

interface AgentLibraryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectAgent: (agent: any) => void;
}

export function AgentLibraryModal({ isOpen, onClose, onSelectAgent }: AgentLibraryModalProps) {
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>("All");

  useEffect(() => {
    if (!isOpen) return;
    api.getAgentLibrary().then((res) => {
      setAgents(res.agents || []);
      setLoading(false);
    });
  }, [isOpen]);

  if (!isOpen) return null;

  const categories = ["All", ...Array.from(new Set(agents.map((a) => a.category).filter(Boolean)))];
  const filtered = selectedCategory === "All" ? agents : agents.filter((a) => a.category === selectedCategory);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="flex max-h-[85vh] w-full max-w-4xl flex-col rounded-2xl border border-border-light bg-[#121826] shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div>
            <h2 className="text-xl font-semibold text-white">Specialist Legal Agent Library</h2>
            <p className="mt-0.5 text-xs text-text-secondary">
              Pre-built specialist agents with strict permission scoping and domain legal reasoning
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-white/10 hover:text-white"
          >
            <X size={18} />
          </button>
        </div>

        {/* Category Filters */}
        <div className="flex gap-2 border-b border-border px-6 py-3">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                selectedCategory === cat
                  ? "bg-primary text-white"
                  : "bg-surface-light text-text-secondary hover:bg-surface-elevated hover:text-white"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Agent Cards Grid */}
        <div className="grid flex-1 gap-4 overflow-y-auto p-6 md:grid-cols-2">
          {filtered.map((agent) => {
            const Icon = AGENT_ICONS[agent.agent_type] || Scale;
            return (
              <Card
                key={agent.agent_type}
                className="flex flex-col justify-between border-border bg-surface p-5 transition-all hover:border-primary/50 hover:bg-surface-elevated"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/15 text-primary">
                        <Icon size={20} />
                      </div>
                      <div>
                        <h3 className="font-semibold text-white">{agent.name}</h3>
                        <span className="text-[11px] font-medium text-blue-400">{agent.category}</span>
                      </div>
                    </div>
                  </div>

                  <p className="mt-3 text-xs leading-relaxed text-text-secondary">{agent.description}</p>

                  <div className="mt-4 space-y-2">
                    <div>
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                        Permissions
                      </span>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {(agent.permissions || []).map((perm: string) => (
                          <span
                            key={perm}
                            className="rounded border border-border bg-bg px-2 py-0.5 font-mono text-[10px] text-text-secondary"
                          >
                            {perm}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-5 pt-3 border-t border-border/60 flex justify-end">
                  <Button
                    size="sm"
                    onClick={() => {
                      onSelectAgent(agent);
                      onClose();
                    }}
                    className="flex items-center gap-1.5"
                  >
                    <Plus size={14} /> Add to Workflow
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
