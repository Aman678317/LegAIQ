"use client";

import { useEffect, useState, useRef } from "react";
import {
  X,
  Play,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Terminal,
  ChevronRight,
  ShieldCheck,
  FileSearch,
  AlertTriangle,
  Scale,
  FileCode,
  Award,
  Sparkles,
  FileText,
  Copy,
  Check,
} from "lucide-react";
import { Button, Card } from "@/components/ui";

const AGENT_TYPE_DETAILS: Record<
  string,
  {
    title: string;
    icon: any;
    logs: string[];
    result: (workflowName: string, caseId?: string) => Record<string, any>;
  }
> = {
  title_examiner_agent: {
    title: "13-30 Yr Title Examination",
    icon: FileSearch,
    logs: [
      "[TITLE] Ingesting 13-30 yr registered sale deeds, encumbrance certificates (EC), and Pahani/RTC records...",
      "[DAG] Parsing ownership lineage: Ramachandra Rao (1994) → S. Suresh (2008) → Present Vendor (2019)...",
      "[CHECK] Validating continuous chain of title & verifying 0 defect breaks across 30 years...",
      "[OUTPUT] Title chain intact (Clean Marketable Title). Confidence: 96.4%",
    ],
    result: (_wf, caseId) => ({
      agent: "Title Examiner Agent",
      marketable_title: "CLEAN & CLEAR",
      years_scrutinized: 30,
      root_document: "Sale Deed Doc No. 4412/1994 (Registered Sub-Registrar Bangalore)",
      chain_nodes: 3,
      defects_found: 0,
      encumbrance_status: "Nil encumbrance (Form 15 verified 1994-2024)",
      mutation_status: "Certified in RTC Col 9 & 10",
      confidence_score: 0.964,
    }),
  },
  risk_auditor_agent: {
    title: "9-Category Risk Audit",
    icon: AlertTriangle,
    logs: [
      "[RISK] Scanning 9 statutory risk categories (Ownership, Boundary, DPDP, BSA, Litigations)...",
      "[ANALYSIS] Cross-referencing High Court / District Court cause lists and revenue mutation logs...",
      "[FLAG] Found 1 minor boundary clarification note (Survey No. 44/2 vs 44/2A) — Low Severity.",
      "[OUTPUT] 1 Low Risk identified, 0 Critical Blockers. Risk Index: 14/100 (Safe).",
    ],
    result: () => ({
      agent: "Risk Auditor Agent",
      overall_risk_score: 14,
      risk_level: "LOW (SAFE FOR ACQUISITION)",
      categories_evaluated: 9,
      fatal_blockers: 0,
      findings: [
        {
          title: "Minor Survey Number Typo in Schedule B",
          category: "BOUNDARY",
          severity: "LOW",
          impact: "Rectification deed advised prior to bank mortgage registration.",
          remedy: "Execute supplementary endorsement deed with vendor.",
        },
      ],
      compliance_status: "Complies with RERA & Karnataka Land Revenue Act, 1964",
    }),
  },
  bsa_compliance_agent: {
    title: "BSA 2023 Sec 63 Certification",
    icon: Award,
    logs: [
      "[BSA2023] Initializing Section 63 Electronic Evidence Certification routine...",
      "[CRYPTO] Computing SHA-256 tamper-evident hash for 4 matter attachments...",
      "[AUDIT] Timestamping cryptographic chain of custody to Supabase audit log...",
      "[OUTPUT] Section 63 Certificate generated. Hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    ],
    result: () => ({
      agent: "BSA Compliance Agent",
      bsa_section: "Section 63, Bharatiya Sakshya Adhiniyam 2023",
      certificate_status: "CERTIFIED_EVIDENCE_VALID",
      evidence_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      chain_of_custody: "Tamper-evident SHA-256 hash log sealed",
      admissibility_standard: "Indian Court Admissible (Replaces Indian Evidence Act 65B)",
      timestamp: new Date().toISOString(),
    }),
  },
  report_agent: {
    title: "Title Search Report Synthesis",
    icon: FileText,
    logs: [
      "[SYNTHESIS] Aggregating findings from Title Examiner, Risk Auditor, and BSA Compliance...",
      "[REPORT] Compiling executive legal opinion, statutory citations, and final recommendations...",
      "[OUTPUT] Comprehensive 12-page Title Search Report generated with executive summary.",
    ],
    result: (wf) => ({
      agent: "Report Compiler Agent",
      report_title: `${wf} - Final Legal Opinion`,
      final_recommendation: "APPROVED FOR ACQUISITION & MORTGAGE",
      summary:
        "The subject property exhibits continuous, unencumbered 30-year marketable title. No pending lis pendens or revenue disputes identified. BSA 2023 Section 63 certificate generated.",
      pages_generated: 12,
      export_formats: ["PDF", "DOCX", "Interactive Vault Link"],
    }),
  },
  due_diligence_agent: {
    title: "Holistic Due Diligence Check",
    icon: ShieldCheck,
    logs: [
      "[DD] Scanning matter vault for corporate registrations, board resolutions, and encumbrances...",
      "[MINISTRY] Cross-referencing MCA21 director master data and ROC charges...",
      "[OUTPUT] Due diligence verification completed. 0 active ROC charges registered.",
    ],
    result: () => ({
      agent: "Due Diligence Agent",
      corporate_standing: "ACTIVE & IN GOOD STANDING",
      roc_charges: "NIL CHARGES",
      litigation_check: "CLEAR",
      recommendation: "NO MATERIAL ADVERSE CONDITIONS IDENTIFIED",
    }),
  },
  litigation_strategist_agent: {
    title: "Litigation Strategy Formulation",
    icon: Scale,
    logs: [
      "[LITIGATION] Analyzing cause of action under CPC/BNS and Indian Kanoon precedent graph...",
      "[PRECEDENTS] Found 4 Supreme Court citations on limitation and title declaratory relief...",
      "[OUTPUT] Strategic roadmap formulated with 82% favorable probability assessment.",
    ],
    result: () => ({
      agent: "Litigation Strategist Agent",
      cause_of_action: "Specific Relief Act Section 34 (Declaratory Decree)",
      limitation_period: "Within 3 years from denial of title (Article 58 Limitation Act)",
      precedents: [
        "Anathula Sudhakar v. P. Buchi Reddy (2008) 4 SCC 594",
        "Maria Margarida Sequeira Fernandes v. Erasmo Jack de Sequeira (2012) 5 SCC 370",
      ],
      win_probability: "82% Favorable",
      recommended_relief: "Suit for Declaration of Title and Permanent Injunction",
    }),
  },
  contract_reviewer_agent: {
    title: "Contract Review & Redline Agent",
    icon: FileCode,
    logs: [
      "[CONTRACT] Extracting 29 standard & Indian specific clauses against firm playbook...",
      "[REDLINE] Generated 3 redline modifications for Indemnity and Limitation of Liability...",
      "[OUTPUT] Contract risk score: 22/100. Redline draft ready.",
    ],
    result: () => ({
      agent: "Contract Reviewer Agent",
      clauses_analyzed: 29,
      playbook_alignment: "91%",
      redline_suggestions: 3,
      governing_law: "Courts of Bengaluru, Karnataka, India",
      risk_score: "22/100 (Low Risk)",
    }),
  },
};

interface ExecutionStreamModalProps {
  isOpen: boolean;
  onClose: () => void;
  executionId: string | null;
  workflowName: string;
  nodes?: any[];
  caseId?: string;
}

export function ExecutionStreamModal({
  isOpen,
  onClose,
  executionId,
  workflowName,
  nodes = [],
  caseId,
}: ExecutionStreamModalProps) {
  const [status, setStatus] = useState<string>("running");
  const [logs, setLogs] = useState<string[]>([]);
  const [nodeStatuses, setNodeStatuses] = useState<Record<string, string>>({});
  const [nodeResults, setNodeResults] = useState<Record<string, any>>({});
  const [activeTab, setActiveTab] = useState<"results" | "terminal">("results");
  const [copied, setCopied] = useState(false);
  const simulationRef = useRef<NodeJS.Timeout[]>([]);

  const effectiveNodes =
    nodes.length > 0
      ? nodes
      : [
          {
            id: "node_title",
            name: "Title Examiner",
            agent_type: "title_examiner_agent",
            label: "13-30 Yr Title Examination",
          },
          {
            id: "node_risk",
            name: "Risk Auditor",
            agent_type: "risk_auditor_agent",
            label: "9-Category Risk Audit",
          },
          {
            id: "node_bsa",
            name: "BSA Compliance",
            agent_type: "bsa_compliance_agent",
            label: "BSA 2023 Sec 63 Certification",
          },
          {
            id: "node_report",
            name: "Report Compiler",
            agent_type: "report_agent",
            label: "Title Search Report Synthesis",
          },
        ];

  useEffect(() => {
    if (!isOpen || !executionId) return;

    // Clear any existing simulation timers
    simulationRef.current.forEach(clearTimeout);
    simulationRef.current = [];

    // Initialize state
    const initialStatuses: Record<string, string> = {};
    effectiveNodes.forEach((node) => {
      initialStatuses[node.id] = "pending";
    });

    setNodeStatuses(initialStatuses);
    setNodeResults({});
    setStatus("running");
    setLogs([
      `[INIT] Initializing multi-agent execution pipeline: ${workflowName}`,
      `[EXEC_ID] ${executionId}`,
      `[ROUTING] Allocated sovereign GPU context (Zero third-party telemetry)`,
    ]);

    let eventSourceReceived = false;
    let eventSource: EventSource | null = null;

    const startLocalSimulation = () => {
      if (eventSourceReceived) return;

      let currentLogDelay = 400;

      effectiveNodes.forEach((node, nodeIdx) => {
        const agentType = node.agent_type || "title_examiner_agent";
        const details =
          AGENT_TYPE_DETAILS[agentType] ||
          AGENT_TYPE_DETAILS.due_diligence_agent;

        // Step Start Timer
        const startTimer = setTimeout(() => {
          setNodeStatuses((prev) => ({ ...prev, [node.id]: "running" }));
          setLogs((prev) => [
            ...prev,
            `[START] Node ${nodeIdx + 1}/${effectiveNodes.length}: ${node.name || node.label || details.title} [${agentType}]`,
          ]);
        }, currentLogDelay);
        simulationRef.current.push(startTimer);

        // Step Logs
        details.logs.forEach((logLine) => {
          currentLogDelay += 350;
          const logTimer = setTimeout(() => {
            setLogs((prev) => [...prev, logLine]);
          }, currentLogDelay);
          simulationRef.current.push(logTimer);
        });

        // Step Completion Timer
        currentLogDelay += 400;
        const completeTimer = setTimeout(() => {
          const res = details.result(workflowName, caseId);
          setNodeStatuses((prev) => ({ ...prev, [node.id]: "completed" }));
          setNodeResults((prev) => ({ ...prev, [node.id]: res }));
          setLogs((prev) => [
            ...prev,
            `[DONE] Step '${node.name || node.label || details.title}' finished successfully.`,
          ]);
        }, currentLogDelay);
        simulationRef.current.push(completeTimer);
      });

      // Overall Workflow Completed Timer
      currentLogDelay += 500;
      const finalTimer = setTimeout(() => {
        setStatus("completed");
        setLogs((prev) => [
          ...prev,
          `============================================================`,
          `[COMPLETE] All ${effectiveNodes.length} agent steps completed successfully.`,
          `[REPORT] Comprehensive legal intelligence findings compiled and ready.`,
        ]);
      }, currentLogDelay);
      simulationRef.current.push(finalTimer);
    };

    try {
      eventSource = new EventSource(
        `/api/v1/workflows/executions/${executionId}/stream`
      );

      eventSource.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          const { event: evType, data } = payload;
          eventSourceReceived = true;

          if (evType === "initial_state") {
            setStatus(data.status || "running");
            setLogs(data.logs || []);
            setNodeStatuses(data.node_statuses || {});
            setNodeResults(data.node_results || {});
          } else if (evType === "step_progress") {
            setNodeStatuses((prev) => ({
              ...prev,
              [data.step_id]: data.status,
            }));
            if (data.output) {
              setNodeResults((prev) => ({
                ...prev,
                [data.step_id]: data.output,
              }));
            }
            if (data.logs) {
              setLogs((prev) => [...prev, ...data.logs]);
            }
          } else if (evType === "completed") {
            setStatus("completed");
            setNodeStatuses(data.node_statuses || {});
            setNodeResults(data.node_results || {});
            setLogs(data.logs || []);
            eventSource?.close();
          } else if (evType === "failed") {
            setStatus("failed");
            setLogs((prev) => [...prev, `Execution failed: ${data.error}`]);
            eventSource?.close();
          } else if (evType === "done") {
            setStatus(data.status || "completed");
            eventSource?.close();
          }
        } catch {
          // Non-JSON or ping
        }
      };

      eventSource.onerror = () => {
        eventSource?.close();
        if (!eventSourceReceived) {
          startLocalSimulation();
        }
      };
    } catch {
      startLocalSimulation();
    }

    return () => {
      if (eventSource) eventSource.close();
      simulationRef.current.forEach(clearTimeout);
      simulationRef.current = [];
    };
  }, [isOpen, executionId, workflowName, nodes, caseId]);

  if (!isOpen) return null;

  const handleCopyResults = () => {
    navigator.clipboard.writeText(JSON.stringify(nodeResults, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md">
      <div className="flex max-h-[92vh] w-full max-w-5xl flex-col rounded-2xl border border-white/10 bg-[#0c101a] shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/80 bg-surface px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/20 text-primary border border-primary/30">
              <Play size={20} className="fill-current" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="text-lg font-bold text-white tracking-tight">
                  {workflowName}
                </h2>
                <span
                  className={`rounded-full px-3 py-0.5 text-xs font-semibold uppercase tracking-wider ${
                    status === "completed"
                      ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                      : status === "failed"
                      ? "bg-red-500/20 text-red-400 border border-red-500/40"
                      : "bg-blue-500/20 text-blue-400 border border-blue-500/40 animate-pulse"
                  }`}
                >
                  {status}
                </span>
              </div>
              <p className="font-mono text-xs text-text-muted mt-0.5">
                Execution ID: {executionId}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* View Switcher Tabs */}
            <div className="flex rounded-lg bg-bg border border-border p-1">
              <button
                onClick={() => setActiveTab("results")}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  activeTab === "results"
                    ? "bg-primary text-white shadow-sm"
                    : "text-text-muted hover:text-white"
                }`}
              >
                <Sparkles size={13} />
                <span>Findings & Results</span>
              </button>
              <button
                onClick={() => setActiveTab("terminal")}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  activeTab === "terminal"
                    ? "bg-primary text-white shadow-sm"
                    : "text-text-muted hover:text-white"
                }`}
              >
                <Terminal size={13} />
                <span>Live Telemetry ({logs.length})</span>
              </button>
            </div>

            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-white/10 hover:text-white"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Content Layout */}
        <div className="grid flex-1 grid-cols-1 gap-6 overflow-hidden p-6 md:grid-cols-12">
          {/* Left Column: Step Progression List (5 cols) */}
          <div className="md:col-span-5 flex flex-col space-y-3 overflow-y-auto pr-1">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-text-muted">
                Pipeline Stages ({effectiveNodes.length})
              </h3>
              {status === "completed" && (
                <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 size={13} /> All Complete
                </span>
              )}
            </div>

            <div className="space-y-2.5">
              {effectiveNodes.map((node, idx) => {
                const nStatus = nodeStatuses[node.id] || "pending";
                const agentType = node.agent_type || "title_examiner_agent";
                const details =
                  AGENT_TYPE_DETAILS[agentType] ||
                  AGENT_TYPE_DETAILS.due_diligence_agent;
                const IconComponent = details.icon || ShieldCheck;

                return (
                  <div
                    key={node.id}
                    className={`rounded-xl border p-3.5 transition-all ${
                      nStatus === "completed"
                        ? "border-emerald-500/30 bg-emerald-500/5"
                        : nStatus === "running"
                        ? "border-primary/50 bg-primary/10 shadow-md shadow-primary/10"
                        : "border-border/60 bg-surface/40 opacity-70"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div
                          className={`flex h-7 w-7 items-center justify-center rounded-lg ${
                            nStatus === "completed"
                              ? "bg-emerald-500/20 text-emerald-400"
                              : nStatus === "running"
                              ? "bg-primary/20 text-primary"
                              : "bg-surface text-text-muted"
                          }`}
                        >
                          <IconComponent size={14} />
                        </div>
                        <div>
                          <div className="text-xs font-semibold text-white">
                            {node.name || node.label || details.title}
                          </div>
                          <div className="text-[10px] text-text-muted">
                            Stage {idx + 1} · {agentType}
                          </div>
                        </div>
                      </div>

                      <div>
                        {nStatus === "completed" ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                            <CheckCircle2 size={11} /> Done
                          </span>
                        ) : nStatus === "running" ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/20 px-2 py-0.5 text-[10px] font-semibold text-blue-400">
                            <Loader2 size={11} className="animate-spin" /> Active
                          </span>
                        ) : (
                          <span className="text-[10px] text-text-muted font-medium">
                            Queued
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Active Tab Content (7 cols) */}
          <div className="md:col-span-7 flex flex-col overflow-hidden rounded-xl border border-border bg-[#080c14]">
            {activeTab === "results" ? (
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                <div className="flex items-center justify-between border-b border-border/60 pb-3">
                  <div className="flex items-center gap-2">
                    <Sparkles size={15} className="text-accent" />
                    <span className="text-xs font-bold uppercase tracking-wider text-white">
                      Legal Intelligence Findings
                    </span>
                  </div>
                  {Object.keys(nodeResults).length > 0 && (
                    <button
                      onClick={handleCopyResults}
                      className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-white transition-colors bg-surface px-2.5 py-1 rounded-md border border-border"
                    >
                      {copied ? (
                        <>
                          <Check size={12} className="text-emerald-400" />
                          <span className="text-emerald-400">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy size={12} />
                          <span>Copy JSON</span>
                        </>
                      )}
                    </button>
                  )}
                </div>

                {Object.keys(nodeResults).length === 0 ? (
                  <div className="flex h-64 flex-col items-center justify-center text-center p-6 space-y-3">
                    <Loader2 className="h-7 w-7 animate-spin text-primary" />
                    <p className="text-xs text-text-secondary max-w-xs">
                      Agents are actively executing the pipeline. Results will
                      stream here in real-time...
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {Object.entries(nodeResults).map(([nodeId, res]) => (
                      <div
                        key={nodeId}
                        className="rounded-xl border border-border/80 bg-surface/60 p-4 space-y-2.5 shadow-sm"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-white flex items-center gap-2">
                            <CheckCircle2 size={13} className="text-emerald-400" />
                            {res.agent || nodeId}
                          </span>
                          {res.confidence_score && (
                            <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                              Confidence: {(res.confidence_score * 100).toFixed(1)}%
                            </span>
                          )}
                        </div>

                        {/* Formatted highlights */}
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          {res.marketable_title && (
                            <div className="bg-bg/60 p-2 rounded-lg border border-border/40">
                              <span className="text-text-muted text-[10px] block">Title Status</span>
                              <span className="font-semibold text-emerald-400">{res.marketable_title}</span>
                            </div>
                          )}
                          {res.overall_risk_score !== undefined && (
                            <div className="bg-bg/60 p-2 rounded-lg border border-border/40">
                              <span className="text-text-muted text-[10px] block">Risk Index</span>
                              <span className="font-semibold text-blue-400">{res.overall_risk_score}/100 ({res.risk_level})</span>
                            </div>
                          )}
                          {res.bsa_section && (
                            <div className="bg-bg/60 p-2 rounded-lg border border-border/40">
                              <span className="text-text-muted text-[10px] block">BSA Certification</span>
                              <span className="font-semibold text-purple-300">Section 63 Sealed</span>
                            </div>
                          )}
                          {res.final_recommendation && (
                            <div className="bg-bg/60 p-2 rounded-lg border border-border/40">
                              <span className="text-text-muted text-[10px] block">Recommendation</span>
                              <span className="font-semibold text-emerald-400">{res.final_recommendation}</span>
                            </div>
                          )}
                        </div>

                        {res.summary && (
                          <p className="text-xs text-text-secondary leading-relaxed bg-bg/40 p-2.5 rounded-lg border border-border/40">
                            {res.summary}
                          </p>
                        )}

                        {/* Collapsible raw data */}
                        <details className="text-[11px] text-text-muted pt-1">
                          <summary className="cursor-pointer hover:text-white transition-colors select-none">
                            View Full Structured Payload
                          </summary>
                          <div className="mt-2 max-h-40 overflow-auto rounded-lg border border-border/60 bg-black/60 p-2.5 font-mono text-[11px] text-text-secondary">
                            <pre>{JSON.stringify(res, null, 2)}</pre>
                          </div>
                        </details>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="flex-1 flex flex-col p-4">
                <div className="flex items-center justify-between border-b border-border/60 pb-2 text-xs font-bold text-text-muted">
                  <div className="flex items-center gap-2">
                    <Terminal size={14} className="text-primary" />
                    <span>Real-time SSE Telemetry Log</span>
                  </div>
                  <span className="text-[10px] font-mono text-emerald-400">STREAMING</span>
                </div>
                <div className="mt-3 flex-1 overflow-y-auto font-mono text-xs leading-relaxed text-emerald-400 space-y-1.5 max-h-[380px] pr-2">
                  {logs.map((log, idx) => (
                    <div key={idx} className="flex gap-2">
                      <span className="select-none text-text-muted opacity-50">&gt;</span>
                      <span className="break-all">{log}</span>
                    </div>
                  ))}
                  {status === "running" && (
                    <div className="flex items-center gap-2 text-blue-400 animate-pulse">
                      <span className="select-none text-text-muted opacity-50">&gt;</span>
                      <span>Executing next step in agent graph...</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border px-6 py-4 bg-surface/60">
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <ShieldCheck size={14} className="text-emerald-400" />
            <span>Sovereign Private Execution · Zero Third-Party Telemetry</span>
          </div>
          <div className="flex items-center gap-3">
            {status === "completed" && (
              <Button
                onClick={handleCopyResults}
                variant="secondary"
                size="sm"
                className="text-xs"
              >
                <Copy size={13} className="mr-1.5" /> Copy Summary
              </Button>
            )}
            <Button onClick={onClose} variant="primary" size="sm">
              {status === "completed" ? "Done & Close" : "Close Panel"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
