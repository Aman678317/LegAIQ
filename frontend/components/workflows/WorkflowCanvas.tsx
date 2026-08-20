"use client";

import { useState } from "react";
import {
  Play,
  Plus,
  Trash2,
  Settings,
  ArrowRight,
  ShieldCheck,
  FileSearch,
  AlertTriangle,
  Scale,
  FileCode,
  Award,
  Save,
  Check,
} from "lucide-react";
import { Button, Card } from "@/components/ui";
import { AgentLibraryModal } from "./AgentLibraryModal";
import { ExecutionStreamModal } from "./ExecutionStreamModal";
import { api } from "@/lib/api";

const AGENT_ICONS: Record<string, any> = {
  due_diligence_agent: ShieldCheck,
  title_examiner_agent: FileSearch,
  risk_auditor_agent: AlertTriangle,
  litigation_strategist_agent: Scale,
  contract_reviewer_agent: FileCode,
  bsa_compliance_agent: Award,
};

interface WorkflowCanvasProps {
  workflow?: any;
  caseId?: string;
  onSave?: (workflow: any) => void;
}

export function WorkflowCanvas({ workflow, caseId, onSave }: WorkflowCanvasProps) {
  const [nodes, setNodes] = useState<any[]>(
    workflow?.nodes || [
      {
        id: "node_1",
        name: "Title Examiner",
        agent_type: "title_examiner_agent",
        label: "13-30 Yr Title Examination",
        dependencies: [],
        position: { x: 80, y: 150 },
      },
      {
        id: "node_2",
        name: "Risk Auditor",
        agent_type: "risk_auditor_agent",
        label: "9-Category Risk Audit",
        dependencies: ["node_1"],
        position: { x: 380, y: 150 },
      },
      {
        id: "node_3",
        name: "BSA Compliance",
        agent_type: "bsa_compliance_agent",
        label: "BSA 2023 Sec 63 Certification",
        dependencies: ["node_2"],
        position: { x: 680, y: 150 },
      },
    ]
  );

  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [isLibraryOpen, setIsLibraryOpen] = useState(false);
  const [executionId, setExecutionId] = useState<string | null>(null);
  const [isStreamOpen, setIsStreamOpen] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleAddAgent = (agent: any) => {
    const newNodeId = `node_${nodes.length + 1}`;
    const lastNode = nodes[nodes.length - 1];
    const newNode = {
      id: newNodeId,
      name: agent.name,
      agent_type: agent.agent_type,
      label: agent.name,
      dependencies: lastNode ? [lastNode.id] : [],
      position: { x: 100 + nodes.length * 280, y: 150 },
      config: {},
    };
    setNodes([...nodes, newNode]);
    setSelectedNode(newNode);
  };

  const handleRemoveNode = (id: string) => {
    setNodes(nodes.filter((n) => n.id !== id));
    if (selectedNode?.id === id) setSelectedNode(null);
  };

  const handleRunWorkflow = async () => {
    setExecuting(true);
    try {
      const targetCaseId = caseId || "demo-case-101";
      const targetWorkflowId = workflow?.id || "tpl-prop-dd";
      const res = await api.executeWorkflow(targetWorkflowId, {
        case_id: targetCaseId,
        inputs: { nodes },
      });
      setExecutionId(res.execution_id || "demo-exec-" + Date.now());
      setIsStreamOpen(true);
    } catch {
      setExecutionId("demo-exec-" + Date.now());
      setIsStreamOpen(true);
    } finally {
      setExecuting(false);
    }
  };

  const handleSave = () => {
    const updated = {
      ...(workflow || {}),
      nodes,
      name: workflow?.name || "Custom Legal Intelligence Pipeline",
      updated_at: new Date().toISOString(),
    };
    if (onSave) onSave(updated);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  return (
    <div className="flex h-[750px] flex-col rounded-2xl border border-border bg-[#0b0f19] shadow-2xl overflow-hidden">
      {/* Canvas Top Bar */}
      <div className="flex items-center justify-between border-b border-border bg-surface px-6 py-3.5">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20 text-primary">
            <Scale size={16} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">
              {workflow?.name || "Legal Multi-Agent Workflow Canvas"}
            </h3>
            <p className="text-[11px] text-text-muted">
              {nodes.length} Specialist Agent Steps · Linear & Branching DAG Engine
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => setIsLibraryOpen(true)}
            className="flex items-center gap-1.5"
          >
            <Plus size={14} /> Add Agent Node
          </Button>

          <Button
            size="sm"
            variant="secondary"
            onClick={handleSave}
            className="flex items-center gap-1.5"
          >
            {savedSuccess ? <Check size={14} className="text-emerald-400" /> : <Save size={14} />}
            {savedSuccess ? "Saved!" : "Save Pipeline"}
          </Button>

          <Button
            size="sm"
            onClick={handleRunWorkflow}
            disabled={executing || nodes.length === 0}
            className="flex items-center gap-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 font-semibold shadow-lg shadow-blue-500/20"
          >
            <Play size={14} /> Execute Workflow
          </Button>
        </div>
      </div>

      {/* Main Builder Workspace */}
      <div className="relative flex flex-1 overflow-hidden">
        {/* Canvas Visual Area */}
        <div className="relative flex-1 overflow-auto p-8 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px]">
          <div className="flex items-center gap-6 min-w-max py-12">
            {nodes.map((node, index) => {
              const Icon = AGENT_ICONS[node.agent_type] || Scale;
              const isSelected = selectedNode?.id === node.id;

              return (
                <div key={node.id} className="flex items-center gap-6">
                  {/* Agent Node Card */}
                  <div
                    onClick={() => setSelectedNode(node)}
                    className={`group relative w-64 cursor-pointer rounded-2xl border p-5 transition-all duration-200 ${
                      isSelected
                        ? "border-primary bg-primary/10 shadow-xl shadow-primary/20 ring-2 ring-primary/40"
                        : "border-border bg-surface hover:border-primary/50 hover:bg-surface-elevated"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/20 text-primary">
                        <Icon size={20} />
                      </div>
                      <span className="rounded bg-bg px-2 py-0.5 font-mono text-[10px] text-text-muted">
                        STEP {index + 1}
                      </span>
                    </div>

                    <h4 className="mt-3 font-semibold text-white">{node.name}</h4>
                    <p className="mt-1 text-xs text-text-secondary line-clamp-2">{node.label}</p>

                    <div className="mt-4 flex items-center justify-between border-t border-border/60 pt-3 text-[11px]">
                      <span className="font-mono text-text-muted">{node.agent_type}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemoveNode(node.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 transition-opacity p-1"
                        title="Remove step"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>

                  {/* Flow Arrow Connection */}
                  {index < nodes.length - 1 && (
                    <div className="flex flex-col items-center justify-center text-primary/70">
                      <div className="h-0.5 w-8 bg-gradient-to-r from-primary to-blue-400" />
                      <ArrowRight size={16} className="-ml-1 text-blue-400" />
                    </div>
                  )}
                </div>
              );
            })}

            {/* Quick Add Placeholder */}
            <div
              onClick={() => setIsLibraryOpen(true)}
              className="flex h-40 w-52 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border-light bg-surface/30 text-text-muted transition-colors hover:border-primary hover:text-white"
            >
              <Plus size={24} className="mb-2" />
              <span className="text-xs font-semibold">Add Agent Step</span>
            </div>
          </div>
        </div>

        {/* Right Inspector Sidebar */}
        {selectedNode && (
          <div className="w-80 border-l border-border bg-surface p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <Settings size={15} className="text-primary" />
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted">Node Inspector</h4>
                </div>
                <button onClick={() => setSelectedNode(null)} className="text-text-muted hover:text-white text-xs">
                  Close
                </button>
              </div>

              <div className="mt-4 space-y-4">
                <div>
                  <label className="text-xs font-medium text-text-secondary">Node Name</label>
                  <input
                    type="text"
                    value={selectedNode.name}
                    onChange={(e) => {
                      const updated = { ...selectedNode, name: e.target.value };
                      setSelectedNode(updated);
                      setNodes(nodes.map((n) => (n.id === selectedNode.id ? updated : n)));
                    }}
                    className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-xs font-medium text-text-secondary">Agent Type</label>
                  <input
                    type="text"
                    disabled
                    value={selectedNode.agent_type}
                    className="mt-1 w-full rounded-lg border border-border bg-bg/50 px-3 py-2 font-mono text-xs text-text-muted"
                  />
                </div>

                <div>
                  <label className="text-xs font-medium text-text-secondary">Step Description / Goal</label>
                  <textarea
                    rows={3}
                    value={selectedNode.label}
                    onChange={(e) => {
                      const updated = { ...selectedNode, label: e.target.value };
                      setSelectedNode(updated);
                      setNodes(nodes.map((n) => (n.id === selectedNode.id ? updated : n)));
                    }}
                    className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>
              </div>
            </div>

            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleRemoveNode(selectedNode.id)}
              className="w-full text-red-400 hover:bg-red-500/10 hover:text-red-300"
            >
              Delete Node
            </Button>
          </div>
        )}
      </div>

      {/* Specialist Agent Library Modal */}
      <AgentLibraryModal
        isOpen={isLibraryOpen}
        onClose={() => setIsLibraryOpen(false)}
        onSelectAgent={handleAddAgent}
      />

      {/* Real-time SSE Execution Stream Modal */}
      <ExecutionStreamModal
        isOpen={isStreamOpen}
        onClose={() => setIsStreamOpen(false)}
        executionId={executionId}
        workflowName={workflow?.name || "Legal Intelligence Workflow"}
      />
    </div>
  );
}
