"use client";

import { useEffect, useState } from "react";
import { X, Play, CheckCircle2, AlertCircle, Loader2, Terminal, ChevronRight } from "lucide-react";
import { Button, Card } from "@/components/ui";

interface ExecutionStreamModalProps {
  isOpen: boolean;
  onClose: () => void;
  executionId: string | null;
  workflowName: string;
}

export function ExecutionStreamModal({ isOpen, onClose, executionId, workflowName }: ExecutionStreamModalProps) {
  const [status, setStatus] = useState<string>("running");
  const [logs, setLogs] = useState<string[]>([]);
  const [nodeStatuses, setNodeStatuses] = useState<Record<string, string>>({});
  const [nodeResults, setNodeResults] = useState<Record<string, any>>({});
  const [activeStep, setActiveStep] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !executionId) return;

    setLogs([`Connecting to live execution stream for ${workflowName}...`]);
    setStatus("running");

    const eventSource = new EventSource(`/api/v1/workflows/executions/${executionId}/stream`);

    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const { event: evType, data } = payload;

        if (evType === "initial_state") {
          setStatus(data.status || "running");
          setLogs(data.logs || []);
          setNodeStatuses(data.node_statuses || {});
          setNodeResults(data.node_results || {});
        } else if (evType === "step_progress") {
          setNodeStatuses((prev) => ({ ...prev, [data.step_id]: data.status }));
          setActiveStep(data.step_id);
          if (data.output) {
            setNodeResults((prev) => ({ ...prev, [data.step_id]: data.output }));
          }
          if (data.logs) {
            setLogs((prev) => [...prev, ...data.logs]);
          }
        } else if (evType === "completed") {
          setStatus("completed");
          setNodeStatuses(data.node_statuses || {});
          setNodeResults(data.node_results || {});
          setLogs(data.logs || []);
          eventSource.close();
        } else if (evType === "failed") {
          setStatus("failed");
          setLogs((prev) => [...prev, `Execution failed: ${data.error}`]);
          eventSource.close();
        } else if (evType === "done") {
          setStatus(data.status || "completed");
          eventSource.close();
        }
      } catch {
        // Ping or non-JSON message
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [isOpen, executionId, workflowName]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
      <div className="flex max-h-[90vh] w-full max-w-5xl flex-col rounded-2xl border border-border-light bg-[#0f1420] shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/20 text-primary">
              <Play size={18} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold text-white">{workflowName}</h2>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                    status === "completed"
                      ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                      : status === "failed"
                      ? "bg-red-500/20 text-red-400 border border-red-500/30"
                      : "bg-blue-500/20 text-blue-400 border border-blue-500/30 animate-pulse"
                  }`}
                >
                  {status.toUpperCase()}
                </span>
              </div>
              <p className="font-mono text-xs text-text-muted">Execution ID: {executionId}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-white/10 hover:text-white"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content Layout */}
        <div className="grid flex-1 grid-cols-1 gap-4 overflow-hidden p-6 md:grid-cols-2">
          {/* Left: Step Progression */}
          <div className="flex flex-col space-y-3 overflow-y-auto">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted">Workflow Steps</h3>
            {Object.keys(nodeStatuses).length === 0 ? (
              <div className="flex h-40 items-center justify-center text-xs text-text-muted">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Initializing execution pipeline...
              </div>
            ) : (
              Object.entries(nodeStatuses).map(([nodeId, nStatus]) => (
                <div
                  key={nodeId}
                  className={`rounded-xl border p-4 transition-colors ${
                    nStatus === "completed"
                      ? "border-emerald-500/30 bg-emerald-500/5"
                      : nStatus === "running"
                      ? "border-primary/50 bg-primary/10 animate-pulse"
                      : "border-border bg-surface"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      {nStatus === "completed" ? (
                        <CheckCircle2 size={16} className="text-emerald-400" />
                      ) : nStatus === "running" ? (
                        <Loader2 size={16} className="animate-spin text-primary" />
                      ) : (
                        <div className="h-4 w-4 rounded-full border border-text-muted/40" />
                      )}
                      <span className="text-sm font-medium text-white">{nodeId}</span>
                    </div>
                    <span className="font-mono text-xs text-text-secondary">{nStatus}</span>
                  </div>

                  {nodeResults[nodeId] && (
                    <div className="mt-3 rounded-lg border border-border/80 bg-bg p-2.5 font-mono text-[11px] text-text-secondary overflow-x-auto max-h-32">
                      <pre>{JSON.stringify(nodeResults[nodeId], null, 2)}</pre>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Right: Live Terminal Logs */}
          <div className="flex flex-col rounded-xl border border-border bg-[#0a0d14] p-4">
            <div className="flex items-center gap-2 border-b border-border/60 pb-2 text-xs font-semibold text-text-muted">
              <Terminal size={14} className="text-primary" />
              <span>Real-time SSE Telemetry Log</span>
            </div>
            <div className="mt-3 flex-1 overflow-y-auto font-mono text-xs leading-relaxed text-emerald-400 space-y-1 max-h-[350px]">
              {logs.map((log, idx) => (
                <div key={idx} className="flex gap-2">
                  <span className="select-none text-text-muted opacity-50">&gt;</span>
                  <span>{log}</span>
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
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border px-6 py-4 bg-surface/50">
          <span className="text-xs text-text-muted">
            Telemetry streamed via Server-Sent Events (SSE) · Zero latency
          </span>
          <Button onClick={onClose} variant="secondary" size="sm">
            Close Panel
          </Button>
        </div>
      </div>
    </div>
  );
}
