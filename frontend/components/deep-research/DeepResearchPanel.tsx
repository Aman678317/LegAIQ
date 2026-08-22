"use client";

import { useState, useEffect, useCallback } from "react";
import { Terminal, Download, Play, X, Loader2 } from "lucide-react";
import { API_URL, safeApiUrl } from "@/lib/api";

interface DeepResearchEvent {
  id: string;
  event_type: string;
  event_data: any;
  created_at: string;
}

interface DeepResearchResult {
  id: string;
  question: string;
  report_content: string;
  citations: any[];
  created_at: string;
}

interface DeepResearchPanelProps {
  caseId: string;
  onClose?: () => void;
}

export function DeepResearchPanel({ caseId, onClose }: DeepResearchPanelProps) {
  const [question, setQuestion] = useState("");
  const [model, setModel] = useState("o4-mini-deep-research");
  const [maxToolCalls, setMaxToolCalls] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [events, setEvents] = useState<DeepResearchEvent[]>([]);
  const [result, setResult] = useState<DeepResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(safeApiUrl(`/cases/${caseId}/deep-research`));
      if (res.ok) {
        const history = await res.json();
        if (Array.isArray(history) && history.length > 0) {
          setResult(history[0]);
        }
      }
    } catch {
      // Offline fallback
    }
  }, [caseId]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleRunResearch = async () => {
    if (!question.trim()) {
      setError("Please enter a legal research question");
      return;
    }

    setIsRunning(true);
    setError(null);
    setEvents([]);
    setResult(null);

    try {
      const res = await fetch(safeApiUrl(`/cases/${caseId}/deep-research`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          model,
          max_tool_calls: maxToolCalls,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to start deep research");
      }

      const { task_id } = await res.json();
      connectToStream(task_id);
    } catch (err: any) {
      setError(err.message || "Failed to start research");
      setIsRunning(false);
    }
  };

  const connectToStream = (taskId: string) => {
    const streamUrl = safeApiUrl(`/cases/${caseId}/deep-research/stream/${taskId}`);
    const eventSource = new EventSource(streamUrl);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "event") {
          setEvents((prev) => [...prev, data.event]);
        } else if (data.type === "complete") {
          eventSource.close();
          setResult(data.result);
          setIsRunning(false);
        }
      } catch (e) {
        console.error("Failed to parse SSE payload", e);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      setIsRunning(false);
      if (!result) {
        setError("Connection to deep research streaming endpoint dropped");
      }
    };
  };

  const handleDownload = () => {
    if (!result) return;
    const blob = new Blob([result.report_content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `deep-research-${caseId}-${new Date().toISOString().split("T")[0]}.md`;
    a.click();
  };

  const examples = [
    "What are landmark Supreme Court precedents on unregistered agreements under Section 54 TPA?",
    "Admissibility requirements of electronic call recordings under Section 63 BSA 2023.",
    "Section 27 Indian Contract Act strict prohibition on post-employment non-compete clauses.",
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 text-slate-100 shadow-xl space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2 font-semibold text-lg text-emerald-400">
          <Terminal size={20} />
          <span>Deep Legal Research Engine (BSA & Landmark Precedents)</span>
        </div>
        {onClose && (
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1">
            <X size={18} />
          </button>
        )}
      </div>

      <div className="space-y-3 bg-slate-950/60 p-4 rounded-lg border border-slate-800/80">
        <div>
          <label className="block text-xs font-medium uppercase tracking-wider text-slate-400 mb-1.5">
            Research Prompt / Case Legal Issue
          </label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-sm focus:outline-none focus:border-emerald-500 min-h-[90px]"
            placeholder="Describe the legal proposition, dispute, or statute to research..."
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Reasoning Model</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-sm"
            >
              <option value="o4-mini-deep-research">o4-mini-deep-research (Fast Statutory Synthesis)</option>
              <option value="o3-deep-research">o3-deep-research (Exhaustive Judicial Precedent Graph)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Max Autonomous Tool Calls</label>
            <input
              type="range"
              min="0"
              max="10"
              value={maxToolCalls}
              onChange={(e) => setMaxToolCalls(parseInt(e.target.value))}
              className="w-full accent-emerald-500"
            />
            <span className="text-xs text-slate-400">{maxToolCalls === 0 ? "Auto (Optimized)" : `${maxToolCalls} calls`}</span>
          </div>
        </div>

        <div>
          <span className="text-xs text-slate-400 font-medium">Example Legal Queries:</span>
          <div className="flex flex-col gap-1.5 mt-1.5">
            {examples.map((ex, i) => (
              <button
                key={i}
                onClick={() => setQuestion(ex)}
                className="text-left text-xs bg-slate-900/80 hover:bg-slate-800 text-slate-300 p-2 rounded border border-slate-800 transition"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleRunResearch}
          disabled={isRunning || !question.trim()}
          className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition shadow-lg shadow-emerald-950"
        >
          {isRunning ? <Loader2 className="animate-spin" size={18} /> : <Play size={18} />}
          {isRunning ? "Running Multi-Pass Deep Research..." : "Execute Deep Research"}
        </button>
      </div>

      {events.length > 0 && (
        <div className="bg-slate-950 rounded-lg border border-slate-800 p-3 max-h-48 overflow-y-auto space-y-1.5 font-mono text-xs">
          <div className="text-slate-400 uppercase font-semibold text-[10px] tracking-wider mb-1">Live Research Telemetry</div>
          {events.map((ev) => (
            <div key={ev.id} className="flex items-start gap-2">
              <span className="text-emerald-400 font-bold">[{ev.event_type}]</span>
              <span className="text-slate-300">{ev.event_data?.message || ev.event_data?.query || ev.event_data?.citation || JSON.stringify(ev.event_data)}</span>
            </div>
          ))}
        </div>
      )}

      {result && (
        <div className="bg-slate-950 rounded-lg border border-slate-800 p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h4 className="font-semibold text-emerald-400 text-sm">Deep Legal Synthesis Report</h4>
            <button
              onClick={handleDownload}
              className="flex items-center gap-1.5 text-xs text-slate-300 hover:text-white bg-slate-800 px-3 py-1.5 rounded border border-slate-700 transition"
            >
              <Download size={14} />
              <span>Download Markdown</span>
            </button>
          </div>
          <div className="text-xs text-slate-200 leading-relaxed whitespace-pre-wrap max-h-96 overflow-y-auto pr-2">
            {result.report_content}
          </div>
        </div>
      )}

      {error && (
        <div className="bg-rose-950/50 border border-rose-800 text-rose-300 p-3 rounded-lg text-xs">
          {error}
        </div>
      )}
    </div>
  );
}
