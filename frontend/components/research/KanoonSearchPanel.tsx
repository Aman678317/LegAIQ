"use client";

import { useState } from "react";
import {
  Search,
  BookOpen,
  Award,
  ExternalLink,
  GitFork,
  CheckCircle2,
  Calendar,
  Layers,
  Scale,
  Loader2,
} from "lucide-react";
import { Button, Card } from "@/components/ui";
import { api } from "@/lib/api";

export function KanoonSearchPanel() {
  const [query, setQuery] = useState("GPA sale transfer of property title");
  const [results, setResults] = useState<any[]>([]);
  const [activeGraph, setActiveGraph] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    try {
      const res = await api.searchKanoonJudgments({ query });
      setResults(res.judgments || []);
      if (res.judgments?.length > 0) {
        loadCitationGraph(res.judgments[0].doc_id);
      }
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  };

  const loadCitationGraph = async (docId: string) => {
    try {
      const res = await api.getKanoonCitationGraph(docId);
      setActiveGraph(res);
    } catch {
      // Fallback
    }
  };

  return (
    <div className="space-y-6">
      {/* Search Header */}
      <Card className="p-6 space-y-4 border-border bg-surface">
        <div className="flex items-center gap-3 border-b border-border pb-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/20 text-primary">
            <Scale size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-white text-base">Indian Kanoon Precedent &amp; Citation Research</h3>
            <p className="text-xs text-text-secondary">
              Search judgments across Supreme Court of India, High Courts, and Tribunals with citation network graphs
            </p>
          </div>
        </div>

        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-text-muted" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Search Indian case law, statutory section, or judgment topic..."
              className="w-full rounded-xl border border-border bg-bg pl-9 pr-3 py-2 text-xs text-white focus:border-primary focus:outline-none"
            />
          </div>
          <Button onClick={handleSearch} disabled={loading} className="flex items-center gap-2">
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
            Search Case Law
          </Button>
        </div>
      </Card>

      {/* Results & Citation Graph Side-by-Side */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left: Judgment Cards */}
        <div className="space-y-4">
          <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">
            Relevant Judgments ({results.length})
          </span>

          {results.map((j) => (
            <Card
              key={j.doc_id}
              onClick={() => loadCitationGraph(j.doc_id)}
              className="cursor-pointer p-5 space-y-3 border-border bg-surface hover:border-primary/50 transition-all"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h4 className="font-bold text-white text-sm">{j.title}</h4>
                  <div className="mt-1 flex items-center gap-2 text-xs text-text-muted">
                    <span className="text-primary font-semibold">{j.court}</span>
                    <span>·</span>
                    <span className="font-mono">{j.citation}</span>
                    <span>·</span>
                    <span>{j.judgment_date}</span>
                  </div>
                </div>
                {j.precedent_strength && (
                  <span className="rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-[10px] font-bold text-emerald-400 border border-emerald-500/30">
                    {j.precedent_strength}
                  </span>
                )}
              </div>

              <p className="text-xs leading-relaxed text-slate-300 bg-bg p-3 rounded-lg border border-border/80 font-serif">
                <strong>Ratio Decidendi:</strong> {j.ratio_decidendi}
              </p>

              <div className="flex items-center justify-between text-xs text-text-muted pt-1">
                <span className="flex items-center gap-1">
                  <GitFork size={13} className="text-primary" /> Cited by {j.cited_by_count} judgments
                </span>
                <span className="text-primary hover:underline flex items-center gap-1">
                  View Citation Graph
                </span>
              </div>
            </Card>
          ))}
        </div>

        {/* Right: Citation Network Graph */}
        <Card className="p-6 space-y-4 border-border bg-surface flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <GitFork size={16} className="text-primary" />
                <h4 className="font-semibold text-white text-sm">Citation Network DAG</h4>
              </div>
              {activeGraph && (
                <span className="font-mono text-xs text-text-muted">
                  {activeGraph.total_citations} Total Citations
                </span>
              )}
            </div>

            {activeGraph ? (
              <div className="mt-4 space-y-4">
                <div className="rounded-xl border border-primary/40 bg-primary/10 p-4">
                  <span className="text-[10px] uppercase text-text-muted font-bold">Root Landmark Precedent</span>
                  <div className="mt-1 font-bold text-white text-sm">{activeGraph.root_judgment?.title}</div>
                  <div className="text-xs font-mono text-blue-300">{activeGraph.root_judgment?.citation} ({activeGraph.root_judgment?.court})</div>
                </div>

                <div className="space-y-2">
                  <span className="text-xs font-semibold text-text-muted">Citation Flow:</span>
                  <div className="space-y-2">
                    {activeGraph.edges?.map((edge: any, i: number) => (
                      <div
                        key={i}
                        className="flex items-center justify-between rounded-lg border border-border bg-bg px-3 py-2 text-xs"
                      >
                        <span className="font-medium text-white">{edge.source}</span>
                        <span className="rounded bg-surface px-2 py-0.5 font-mono text-[10px] text-blue-400 font-semibold">
                          {edge.relation}
                        </span>
                        <span className="text-text-secondary">{edge.target}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-12 text-center text-xs text-text-muted">
                Select a judgment to view its live citation network
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border/80 bg-surface/50 p-3 text-[11px] text-text-muted">
            Indian Kanoon citation strength verifies whether a ruling is good law or distinguished by higher benches.
          </div>
        </Card>
      </div>
    </div>
  );
}
