"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  ScrollText, ShieldAlert, AlertTriangle, CheckCircle2,
  FileCode, Layers, GitCompare, BookOpen, Sparkles, Copy,
  Check, ArrowRight, Loader2, RefreshCw, XCircle, Search,
  ChevronDown, Scale
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const SAMPLE_CONTRACT = `SOFTWARE DEVELOPMENT & SERVICES AGREEMENT

This Agreement is entered into on 15th January 2024
BETWEEN:
TechCorp Solutions Private Limited, Bangalore ("Client" or "Party A")
AND
DevSoft India LLP, Mumbai ("Developer" or "Party B")

1. SCOPE OF WORK
Developer shall build, test, and deploy the enterprise web application as specified in Schedule A.

2. PAYMENT & CONSIDERATION
Client shall pay Developer INR 50,00,000 (Fifty Lakhs) in four milestones upon completion. All payments subject to TDS deduction under Section 194J of the Income Tax Act.

3. TERM & TERMINATION
This Agreement commences on 15th January 2024 and continues for 12 months. Either party may terminate for material breach with 30 days notice. Client may terminate immediately without cause.

4. INDEMNIFICATION
Developer shall provide unlimited indemnity and hold harmless Client from and against any and all claims, liabilities, and consequential damages arising from this Agreement without any limitation of liability.

5. LIMITATION OF LIABILITY
In no event shall Client be liable for any indirect or consequential damages. Client's liability is capped at INR 10,000.

6. RESTRICTIVE COVENANTS & NON-COMPETE
Developer and its personnel shall not engage in any competing software business or provide services to any competitor in India for a period of 2 years following termination of this Agreement.

7. GOVERNING LAW & DISPUTE RESOLUTION
This Agreement is governed by the substantive laws of India. Disputes shall be resolved by arbitration under the Arbitration and Conciliation Act, 1996. Seat of arbitration: Bengaluru.

8. STAMP DUTY & REGISTRATION
This instrument is executed on requisite non-judicial stamp paper of Rs. 100 under the Karnataka Stamp Act.`;

export default function ContractsPage() {
  const params = useParams();
  const caseId = params.caseId as string;

  const [activeTab, setActiveTab] = useState<"analysis" | "heatmap" | "playbook" | "redline" | "library">("analysis");
  const [contractText, setContractText] = useState(SAMPLE_CONTRACT);
  const [contractTitle, setContractTitle] = useState("Software Development Agreement");
  const [loading, setLoading] = useState(false);

  // Analysis State
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [heatmapData, setHeatmapData] = useState<any>(null);

  // Playbook State
  const [playbooks, setPlaybooks] = useState<any[]>([]);
  const [selectedPlaybookId, setSelectedPlaybookId] = useState<string>("PB-MSA-001");
  const [playbookResult, setPlaybookResult] = useState<any>(null);
  const [evaluatingPlaybook, setEvaluatingPlaybook] = useState(false);

  // Redline State
  const [modifiedText, setModifiedText] = useState("");
  const [redlineResult, setRedlineResult] = useState<any>(null);
  const [comparingRedline, setComparingRedline] = useState(false);

  // Clause Library State
  const [clauseLibraryItems, setClauseLibraryItems] = useState<any[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    loadPlaybooks();
    loadClauseLibrary();
    handleAnalyze();
  }, [caseId]);

  async function loadPlaybooks() {
    try {
      const res = await api.listPlaybooks(caseId);
      setPlaybooks(res?.items || []);
    } catch (err) {
      console.error(err);
    }
  }

  async function loadClauseLibrary() {
    try {
      const res = await api.listClauseLibrary({ category: selectedCategory || undefined, q: searchQuery || undefined });
      setClauseLibraryItems(res?.items || []);
    } catch (err) {
      console.error(err);
    }
  }

  useEffect(() => {
    loadClauseLibrary();
  }, [selectedCategory, searchQuery]);

  async function handleAnalyze() {
    if (!contractText.trim()) return;
    setLoading(true);
    try {
      const [analysis, heatmap] = await Promise.all([
        api.analyzeContract(caseId, { full_text: contractText, title: contractTitle }),
        api.getContractHeatmap(caseId, { full_text: contractText, title: contractTitle }),
      ]);
      setAnalysisResult(analysis);
      setHeatmapData(heatmap);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleEvaluatePlaybook(pId?: string) {
    const targetId = pId || selectedPlaybookId;
    setEvaluatingPlaybook(true);
    try {
      const res = await api.evaluatePlaybook(caseId, {
        playbook_id: targetId,
        full_text: contractText,
        title: contractTitle,
      });
      setPlaybookResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setEvaluatingPlaybook(false);
    }
  }

  async function handleRunRedline() {
    setComparingRedline(true);
    try {
      const mod = modifiedText || contractText.replace("unlimited indemnity", "indemnity capped at 12 months fees").replace("for a period of 2 years following termination", "during the active term only (per §27 ICA)");
      const res = await api.redlineContract(caseId, {
        original_text: contractText,
        modified_text: mod,
      });
      setRedlineResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setComparingRedline(false);
    }
  }

  function handleCopy(text: string, id: string) {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  function renderRiskBadge(risk: string) {
    const r = (risk || "").toLowerCase();
    if (r === "critical") {
      return <span className="rounded bg-red-500/15 border border-red-500/30 px-2 py-0.5 text-[10px] font-bold text-red-400 uppercase">Critical Risk</span>;
    }
    if (r === "high") {
      return <span className="rounded bg-orange-500/15 border border-orange-500/30 px-2 py-0.5 text-[10px] font-bold text-orange-400 uppercase">High Risk</span>;
    }
    if (r === "medium") {
      return <span className="rounded bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 text-[10px] font-bold text-amber-300 uppercase">Medium Risk</span>;
    }
    return <span className="rounded bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-bold text-emerald-400 uppercase">Low Risk</span>;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <ScrollText size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Contract Intelligence & Playbooks</h1>
            <p className="text-xs text-text-secondary">
              29+ Clause Extraction, 0-100 Risk Scoring, Firm Playbook Deviations & Indian Statutory Moat
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleAnalyze}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg bg-primary px-3.5 py-2 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
            Analyze Contract
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border space-x-6 text-xs font-medium text-text-muted">
        <button
          onClick={() => setActiveTab("analysis")}
          className={cn("pb-2.5 transition-colors border-b-2 flex items-center gap-1.5", activeTab === "analysis" ? "border-primary text-white font-semibold" : "border-transparent hover:text-white")}
        >
          <Layers size={14} />
          29+ Clause Extraction
        </button>
        <button
          onClick={() => setActiveTab("heatmap")}
          className={cn("pb-2.5 transition-colors border-b-2 flex items-center gap-1.5", activeTab === "heatmap" ? "border-primary text-white font-semibold" : "border-transparent hover:text-white")}
        >
          <ShieldAlert size={14} />
          Risk Heatmap Matrix
        </button>
        <button
          onClick={() => {
            setActiveTab("playbook");
            if (!playbookResult) handleEvaluatePlaybook();
          }}
          className={cn("pb-2.5 transition-colors border-b-2 flex items-center gap-1.5", activeTab === "playbook" ? "border-primary text-white font-semibold" : "border-transparent hover:text-white")}
        >
          <Scale size={14} />
          Playbook Deviations
        </button>
        <button
          onClick={() => {
            setActiveTab("redline");
            if (!redlineResult) handleRunRedline();
          }}
          className={cn("pb-2.5 transition-colors border-b-2 flex items-center gap-1.5", activeTab === "redline" ? "border-primary text-white font-semibold" : "border-transparent hover:text-white")}
        >
          <GitCompare size={14} />
          Visual Redline Diff
        </button>
        <button
          onClick={() => setActiveTab("library")}
          className={cn("pb-2.5 transition-colors border-b-2 flex items-center gap-1.5", activeTab === "library" ? "border-primary text-white font-semibold" : "border-transparent hover:text-white")}
        >
          <BookOpen size={14} />
          Enterprise Clause Library
        </button>
      </div>

      {/* TAB 1: CLAUSE EXTRACTION & RISK SCORING */}
      {activeTab === "analysis" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left: Input Text / Source */}
          <div className="lg:col-span-5 space-y-4">
            <div className="rounded-xl border border-border bg-bg-surface p-4 space-y-3 shadow-lg">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white uppercase tracking-wider">Contract Text Under Review</span>
                <button
                  onClick={() => setContractText(SAMPLE_CONTRACT)}
                  className="text-[11px] text-primary hover:underline"
                >
                  Reset Sample
                </button>
              </div>
              <textarea
                value={contractText}
                onChange={(e) => setContractText(e.target.value)}
                className="w-full rounded-lg border border-border bg-bg-elevated p-3 text-xs text-text-primary font-mono focus:border-primary focus:outline-none min-h-[380px] leading-relaxed"
                placeholder="Paste contract text here..."
              />
            </div>

            {/* Indian Statutory Compliance Callout */}
            {analysisResult?.indian_law_compliance && (
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 space-y-2">
                <div className="flex items-center gap-2 text-amber-300 font-semibold text-xs">
                  <Scale size={16} />
                  <span>Indian Statutory Compliance Alerts</span>
                </div>
                <ul className="space-y-1.5 text-[11px] text-amber-200/90 list-disc list-inside">
                  {analysisResult.indian_law_compliance.map((item: string, idx: number) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Right: Extracted Clauses & Risk Scoring */}
          <div className="lg:col-span-7 space-y-4">
            {/* Risk Score Summary Banner */}
            {analysisResult && (
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-xl border border-border bg-bg-surface p-4 text-center">
                  <div className="text-[11px] text-text-muted font-medium uppercase">Overall Risk Score</div>
                  <div className={cn("text-3xl font-extrabold mt-1", (analysisResult.risk_assessment?.risk_score || 0) >= 70 ? "text-red-400" : (analysisResult.risk_assessment?.risk_score || 0) >= 40 ? "text-amber-400" : "text-emerald-400")}>
                    {analysisResult.risk_assessment?.risk_score || 0}
                    <span className="text-xs text-text-muted font-normal"> / 100</span>
                  </div>
                  <div className="mt-1">{renderRiskBadge(analysisResult.risk_assessment?.overall_risk)}</div>
                </div>

                <div className="rounded-xl border border-border bg-bg-surface p-4 text-center">
                  <div className="text-[11px] text-text-muted font-medium uppercase">Clauses Extracted</div>
                  <div className="text-3xl font-extrabold text-white mt-1">
                    {analysisResult.clause_count || 0}
                  </div>
                  <div className="text-[11px] text-text-secondary mt-1">29+ standard & Indian types</div>
                </div>

                <div className="rounded-xl border border-border bg-bg-surface p-4 text-center">
                  <div className="text-[11px] text-text-muted font-medium uppercase">Critical Deviations</div>
                  <div className="text-3xl font-extrabold text-red-400 mt-1">
                    {analysisResult.risk_assessment?.critical_issues?.length || 0}
                  </div>
                  <div className="text-[11px] text-text-secondary mt-1">Requires partner redline</div>
                </div>
              </div>
            )}

            {/* Extracted Clause List */}
            <div className="rounded-xl border border-border bg-bg-surface p-4 space-y-3">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                Extracted Clause Taxonomy ({analysisResult?.clauses?.length || 0})
              </h3>

              <div className="space-y-2.5 max-h-[480px] overflow-y-auto pr-1">
                {analysisResult?.clauses?.map((c: any) => (
                  <div
                    key={c.clause_id}
                    className="rounded-lg border border-border bg-bg-elevated/70 p-3 space-y-1.5 hover:border-primary/40 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-white text-xs">{c.title}</span>
                        <span className="text-[10px] text-text-muted uppercase font-mono px-1.5 py-0.5 rounded bg-bg">
                          {c.clause_type}
                        </span>
                      </div>
                      {renderRiskBadge(c.risk_level)}
                    </div>

                    <p className="text-xs text-text-secondary leading-relaxed font-mono">
                      "{c.content}"
                    </p>

                    {c.risk_factors?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1 pt-1 border-t border-border/40">
                        {c.risk_factors.map((f: string, idx: number) => (
                          <span key={idx} className="text-[10px] font-medium text-red-300 bg-red-500/10 px-1.5 py-0.5 rounded border border-red-500/20">
                            {f}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: RISK HEATMAP MATRIX */}
      {activeTab === "heatmap" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {heatmapData?.categories && Object.entries(heatmapData.categories).map(([catName, cat]: [string, any]) => (
              <div
                key={catName}
                className={cn(
                  "rounded-xl border p-4 space-y-3",
                  cat.highest_risk === "critical"
                    ? "border-red-500/40 bg-red-500/10"
                    : cat.highest_risk === "high"
                    ? "border-orange-500/40 bg-orange-500/10"
                    : cat.highest_risk === "medium"
                    ? "border-amber-500/40 bg-amber-500/10"
                    : "border-emerald-500/40 bg-emerald-500/10"
                )}
              >
                <div className="text-xs font-bold text-white truncate">{catName}</div>
                <div className="text-2xl font-extrabold text-white">
                  {cat.score}
                  <span className="text-xs font-normal text-text-muted"> / 100</span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-text-secondary">
                  <span>{cat.clause_count} Clauses</span>
                  {renderRiskBadge(cat.highest_risk)}
                </div>
              </div>
            ))}
          </div>

          {/* Detailed Category Risk Breakdown */}
          <div className="rounded-xl border border-border bg-bg-surface p-6 space-y-6">
            <h3 className="text-sm font-bold text-white">Functional Risk Matrix Breakdown</h3>
            <div className="space-y-4">
              {heatmapData?.categories && Object.entries(heatmapData.categories).map(([catName, cat]: [string, any]) => (
                <div key={catName} className="rounded-lg border border-border bg-bg-elevated p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-white text-xs">{catName}</span>
                    <span className="text-xs font-mono font-bold text-primary">{cat.score} Risk Pts</span>
                  </div>
                  {/* Progress bar */}
                  <div className="h-2 w-full rounded-full bg-bg">
                    <div
                      className={cn("h-full rounded-full transition-all", cat.score >= 70 ? "bg-red-500" : cat.score >= 40 ? "bg-amber-500" : "bg-emerald-500")}
                      style={{ width: `${Math.min(100, cat.score)}%` }}
                    />
                  </div>
                  {cat.clauses?.length > 0 && (
                    <div className="pt-2 text-[11px] text-text-secondary space-y-1">
                      {cat.clauses.map((c: any) => (
                        <div key={c.clause_id} className="flex items-center justify-between">
                          <span>{c.title}</span>
                          {renderRiskBadge(c.risk_level)}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: PLAYBOOK DEVIATION ENGINE */}
      {activeTab === "playbook" && (
        <div className="space-y-6">
          {/* Playbook Selector */}
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border bg-bg-surface p-4">
            <div className="flex items-center gap-3">
              <label className="text-xs font-semibold text-text-muted uppercase">Select Negotiation Playbook:</label>
              <select
                value={selectedPlaybookId}
                onChange={(e) => {
                  setSelectedPlaybookId(e.target.value);
                  handleEvaluatePlaybook(e.target.value);
                }}
                className="rounded-lg border border-border bg-bg-elevated px-3 py-1.5 text-xs text-white focus:border-primary focus:outline-none"
              >
                {playbooks.map((pb) => (
                  <option key={pb.playbook_id} value={pb.playbook_id}>
                    {pb.name}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={() => handleEvaluatePlaybook()}
              disabled={evaluatingPlaybook}
              className="flex items-center gap-1.5 rounded-lg bg-primary px-3.5 py-1.5 text-xs font-semibold text-white hover:opacity-90"
            >
              {evaluatingPlaybook ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
              Re-Evaluate Playbook
            </button>
          </div>

          {/* Evaluation Results */}
          {playbookResult && (
            <div className="space-y-6">
              {/* Score Banner */}
              <div className="rounded-xl border border-border bg-bg-surface p-5 flex flex-wrap items-center justify-between gap-4 shadow-lg">
                <div>
                  <h3 className="text-sm font-bold text-white">{playbookResult.playbook_name}</h3>
                  <p className="text-xs text-text-muted mt-0.5">
                    Evaluated {playbookResult.total_rules_evaluated} rules — {playbookResult.passed_rules} Compliant, {playbookResult.deviations?.length || 0} Deviations Flagged
                  </p>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div className="text-xs text-text-muted">Playbook Compliance</div>
                    <div className={cn("text-2xl font-extrabold", playbookResult.compliance_score >= 80 ? "text-emerald-400" : playbookResult.compliance_score >= 60 ? "text-amber-300" : "text-red-400")}>
                      {playbookResult.compliance_score}%
                    </div>
                  </div>
                  <div className={cn("rounded-lg px-3 py-2 text-xs font-bold uppercase", playbookResult.overall_status === "walkaway_triggered" ? "bg-red-500/20 text-red-300 border border-red-500/40" : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40")}>
                    {playbookResult.overall_status.replace("_", " ")}
                  </div>
                </div>
              </div>

              {/* Deviations List */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                  Identified Deviations & Recommended Redlines ({playbookResult.deviations?.length || 0})
                </h3>

                {playbookResult.deviations?.map((dev: any) => (
                  <div
                    key={dev.deviation_id}
                    className="rounded-xl border border-border bg-bg-surface p-4 space-y-3 shadow-md border-l-4 border-l-red-500"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-xs">{dev.clause_type.toUpperCase()} DEVIATION</span>
                        <span className="text-[10px] text-red-400 font-mono bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">
                          {dev.deviation_type}
                        </span>
                      </div>
                      {renderRiskBadge(dev.severity)}
                    </div>

                    <p className="text-xs text-red-300 font-medium">{dev.issue_description}</p>

                    {dev.statutory_reference && (
                      <div className="text-[11px] text-amber-300 font-mono">
                        Statutory Basis: {dev.statutory_reference}
                      </div>
                    )}

                    {/* Redline Recommendation Box */}
                    <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 space-y-1.5">
                      <div className="flex items-center justify-between text-[11px] font-semibold text-emerald-400">
                        <span>Proposed Automated Redline:</span>
                        <button
                          onClick={() => handleCopy(dev.recommended_redline, dev.deviation_id)}
                          className="flex items-center gap-1 text-[10px] hover:text-white"
                        >
                          {copiedId === dev.deviation_id ? <Check size={12} /> : <Copy size={12} />}
                          {copiedId === dev.deviation_id ? "Copied" : "Copy Redline"}
                        </button>
                      </div>
                      <p className="text-xs text-emerald-200 font-mono leading-relaxed">
                        {dev.recommended_redline}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: VISUAL REDLINE DIFF EDITOR */}
      {activeTab === "redline" && (
        <div className="space-y-6">
          <div className="rounded-xl border border-border bg-bg-surface p-4 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white">Visual Tracked Changes & Redline Diff</h3>
              <p className="text-xs text-text-muted">Compare original draft against playbook recommendations with addition/deletion highlights</p>
            </div>
            <button
              onClick={handleRunRedline}
              disabled={comparingRedline}
              className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:opacity-90"
            >
              {comparingRedline ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
              Refresh Redline Diff
            </button>
          </div>

          {/* Redline Changes Table */}
          <div className="space-y-4">
            {redlineResult?.changes?.map((ch: any) => (
              <div key={ch.change_id} className="rounded-xl border border-border bg-bg-surface p-4 space-y-3">
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <span className="text-xs font-bold text-white uppercase">{ch.clause_id || ch.change_id} — {ch.change_type}</span>
                  <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    Recommended Fix
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  {/* Original Text (Red deletion) */}
                  <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 space-y-1">
                    <span className="text-[10px] font-bold text-red-400 uppercase tracking-wider">Original (To Be Deleted / Replaced)</span>
                    <p className="line-through text-red-200/90 font-mono leading-relaxed">{ch.original_text}</p>
                  </div>

                  {/* Modified Text (Green addition) */}
                  <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 space-y-1">
                    <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">Proposed Substitution (Standard)</span>
                    <p className="text-emerald-200 font-mono leading-relaxed">{ch.modified_text}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 5: ENTERPRISE CLAUSE LIBRARY */}
      {activeTab === "library" && (
        <div className="space-y-6">
          {/* Search & Filter */}
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border bg-bg-surface p-4">
            <div className="flex items-center gap-2 flex-1 max-w-md">
              <Search size={15} className="text-text-muted" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search standard, fallback, or walkaway clauses..."
                className="w-full bg-transparent text-xs text-white placeholder-text-muted focus:outline-none"
              />
            </div>

            <div className="flex items-center gap-2">
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="rounded-lg border border-border bg-bg-elevated px-3 py-1.5 text-xs text-white focus:border-primary focus:outline-none"
              >
                <option value="">All Categories</option>
                <option value="Commercial">Commercial</option>
                <option value="Employment & Services">Employment & Services</option>
                <option value="Dispute Resolution">Dispute Resolution</option>
                <option value="Privacy & Compliance">Privacy & Compliance</option>
                <option value="Real Estate & Conveyancing">Real Estate & Conveyancing</option>
              </select>
            </div>
          </div>

          {/* Clause Cards */}
          <div className="space-y-4">
            {clauseLibraryItems.map((item) => (
              <div
                key={item.clause_id}
                className="rounded-xl border border-border bg-bg-surface p-5 space-y-4 shadow-md"
              >
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <div>
                    <h4 className="text-sm font-bold text-white">{item.title}</h4>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] text-primary font-mono px-1.5 py-0.5 rounded bg-primary/10">
                        {item.clause_type}
                      </span>
                      <span className="text-[10px] text-text-muted">• {item.category}</span>
                      {item.statutory_reference && (
                        <span className="text-[10px] text-amber-300 font-mono">• {item.statutory_reference}</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Standard / Preferred */}
                  <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3.5 space-y-2">
                    <div className="flex items-center justify-between text-[11px] font-bold text-emerald-400">
                      <span>Standard Position (Preferred)</span>
                      <button
                        onClick={() => handleCopy(item.standard_language, `${item.clause_id}-std`)}
                        className="hover:text-white"
                      >
                        {copiedId === `${item.clause_id}-std` ? <Check size={13} /> : <Copy size={13} />}
                      </button>
                    </div>
                    <p className="text-xs text-emerald-200/90 font-mono leading-relaxed">{item.standard_language}</p>
                  </div>

                  {/* Fallback Tier 1 */}
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3.5 space-y-2">
                    <div className="flex items-center justify-between text-[11px] font-bold text-amber-300">
                      <span>Fallback Tier 1</span>
                      <button
                        onClick={() => handleCopy(item.fallback_tier_1, `${item.clause_id}-fb1`)}
                        className="hover:text-white"
                      >
                        {copiedId === `${item.clause_id}-fb1` ? <Check size={13} /> : <Copy size={13} />}
                      </button>
                    </div>
                    <p className="text-xs text-amber-200/90 font-mono leading-relaxed">{item.fallback_tier_1}</p>
                  </div>

                  {/* Walkaway Language */}
                  <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3.5 space-y-2">
                    <div className="text-[11px] font-bold text-red-400">
                      Walkaway Trigger
                    </div>
                    <p className="text-xs text-red-200/90 font-mono leading-relaxed">{item.walkaway_language || "Reject uncapped liabilities or unilateral jurisdiction."}</p>
                  </div>
                </div>

                {item.guidance_notes && (
                  <div className="text-[11px] text-text-muted bg-bg-elevated p-3 rounded-lg border border-border/50">
                    <span className="font-semibold text-text-secondary">Counsel Guidance: </span>
                    {item.guidance_notes}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
