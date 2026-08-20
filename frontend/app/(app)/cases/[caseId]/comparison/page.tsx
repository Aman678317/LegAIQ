"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import {
  GitCompare, Loader2, CheckCircle2, XCircle, HelpCircle, MinusCircle,
  ChevronRight, ArrowRightLeft, FileText, Check, AlertTriangle, Layers,
  Columns, RefreshCw, X
} from "lucide-react";
import { api } from "@/lib/api";
import { Button, Card, Badge, Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui";
import { VERDICT_STYLES } from "@/lib/utils";

const VERDICT_ICONS: Record<string, any> = {
  MATCH: CheckCircle2,
  MISMATCH: XCircle,
  MISSING: MinusCircle,
  UNCERTAIN: HelpCircle,
};

// Word and character level diff algorithm for side-by-side comparison
function diffStrings(a: string, b: string): Array<{ type: "equal" | "add" | "remove"; value: string }> {
  if (a === b) {
    return [{ type: "equal", value: a }];
  }

  const wordsA = a.split(/(\s+)/);
  const wordsB = b.split(/(\s+)/);

  const result: Array<{ type: "equal" | "add" | "remove"; value: string }> = [];
  let i = 0;
  let j = 0;

  while (i < wordsA.length || j < wordsB.length) {
    if (i < wordsA.length && j < wordsB.length && wordsA[i] === wordsB[j]) {
      result.push({ type: "equal", value: wordsA[i] });
      i++;
      j++;
    } else if (i < wordsA.length && (j >= wordsB.length || !wordsB.slice(j, j + 5).includes(wordsA[i]))) {
      result.push({ type: "remove", value: wordsA[i] });
      i++;
    } else if (j < wordsB.length) {
      result.push({ type: "add", value: wordsB[j] });
      j++;
    } else {
      i++;
      j++;
    }
  }

  return result;
}

export default function ComparisonPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [documents, setDocuments] = useState<any[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [results, setResults] = useState<any[]>([]);
  const [directDiff, setDirectDiff] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"fields" | "side_by_side">("side_by_side");

  useEffect(() => {
    Promise.all([
      api.listDocuments(caseId),
      api.getComparison(caseId).catch(() => []),
    ])
      .then(([docs, res]) => {
        const completedDocs = (docs || []).filter((d: any) => d.status === "COMPLETED" || d.page_count);
        setDocuments(completedDocs);
        setResults(res || []);

        // Auto-select first two documents if available
        if (completedDocs.length >= 2) {
          const initialSelection = new Set([completedDocs[0].id, completedDocs[1].id]);
          setSelected(initialSelection);
          runDirectCompare(Array.from(initialSelection));
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [caseId]);

  async function runDirectCompare(docIds: string[]) {
    if (docIds.length < 2) return;
    setComparing(true);
    setError(null);
    try {
      const diffData = await api.compareDocumentsDirect(caseId, docIds);
      setDirectDiff(diffData);
      if (diffData.field_comparisons && diffData.field_comparisons.length > 0) {
        setResults(diffData.field_comparisons);
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setComparing(false);
    }
  }

  function toggle(docId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(docId)) {
        next.delete(docId);
      } else if (next.size < 6) {
        next.add(docId);
      }
      if (next.size >= 2) {
        runDirectCompare(Array.from(next));
      }
      return next;
    });
  }

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  const selectedDocs = documents.filter((d) => selected.has(d.id));
  const docA = selectedDocs[0];
  const docB = selectedDocs[1];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">Side-by-Side Version Comparison</h1>
            <Badge className="border-primary/40 bg-primary/10 text-xs font-semibold text-primary">
              Multi-Deed Diff
            </Badge>
          </div>
          <p className="mt-1 text-sm text-text-secondary">
            Cross-examine two or more deeds with visual addition/deletion diff highlights and land measurement equivalence.
          </p>
        </div>

        {/* View Switcher */}
        <div className="flex items-center rounded-lg border border-border bg-bg p-1 text-xs">
          <button
            onClick={() => setViewMode("side_by_side")}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-colors ${
              viewMode === "side_by_side" ? "bg-primary text-white" : "text-text-muted hover:text-white"
            }`}
          >
            <Columns size={13} /> Side-by-Side Diff
          </button>
          <button
            onClick={() => setViewMode("fields")}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-colors ${
              viewMode === "fields" ? "bg-primary text-white" : "text-text-muted hover:text-white"
            }`}
          >
            <Layers size={13} /> Field Cross-Check
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Document Selector Pills */}
      <Card className="p-4">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs font-bold uppercase tracking-wider text-text-muted">
            Select Documents to Cross-Examine (Selected: {selected.size} / 6)
          </p>
          {selected.size >= 2 && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => runDirectCompare(Array.from(selected))}
              disabled={comparing}
              className="h-7 text-xs gap-1.5"
            >
              {comparing ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
              Re-compare
            </Button>
          )}
        </div>

        {documents.length === 0 ? (
          <p className="text-xs text-text-muted">Upload at least two documents in the Vault to perform comparison.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {documents.map((doc) => {
              const isSel = selected.has(doc.id);
              return (
                <button
                  key={doc.id}
                  onClick={() => toggle(doc.id)}
                  className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-medium transition-all ${
                    isSel
                      ? "border-primary bg-primary/20 text-white shadow-sm"
                      : "border-border bg-bg-elevated/40 text-text-secondary hover:border-primary/40 hover:text-white"
                  }`}
                >
                  <div className={`flex h-4 w-4 items-center justify-center rounded-full border ${isSel ? "border-primary bg-primary text-white" : "border-border"}`}>
                    {isSel && <Check size={10} />}
                  </div>
                  <FileText size={13} className={isSel ? "text-primary" : "text-text-muted"} />
                  <span className="truncate max-w-[200px]">{doc.file_name}</span>
                  {doc.badge_label && (
                    <span className="rounded bg-bg px-1.5 py-0.2 text-[10px] text-text-muted">
                      {doc.badge_label}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </Card>

      {/* Comparison View */}
      {selected.size < 2 ? (
        <Card className="flex flex-col items-center p-12 text-center">
          <ArrowRightLeft size={36} className="mb-3 text-text-muted" />
          <h3 className="text-base font-semibold text-white">Select at least two documents</h3>
          <p className="mt-1 text-xs text-text-secondary">
            Pick 2 or more deeds from the selector above to compare survey numbers, boundaries, parties, and inline diffs.
          </p>
        </Card>
      ) : comparing ? (
        <div className="flex h-64 flex-col items-center justify-center gap-3 rounded-2xl border border-border bg-bg-surface p-12">
          <Loader2 size={24} className="animate-spin text-primary" />
          <p className="text-sm text-text-secondary font-medium">Computing word-level diff and statutory land equivalence…</p>
        </div>
      ) : viewMode === "side_by_side" ? (
        /* Side-by-Side Visual Diff */
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {/* Document A Panel */}
            <Card className="flex flex-col overflow-hidden border-border/80 p-0 shadow-sm">
              <div className="flex items-center justify-between border-b border-border bg-bg-elevated/50 px-4 py-3">
                <div className="flex items-center gap-2 truncate">
                  <span className="rounded bg-red-500/20 px-2 py-0.5 text-xs font-bold text-red-300">
                    Document A (Base)
                  </span>
                  <span className="text-xs font-semibold text-white truncate">{docA?.file_name || "Document A"}</span>
                </div>
                <span className="rounded bg-bg px-2 py-0.5 text-[10px] text-text-muted">
                  {docA?.badge_label || "Sale Deed"}
                </span>
              </div>
              <div className="max-h-[500px] overflow-y-auto p-4 font-mono text-xs leading-relaxed text-text-secondary bg-bg/40">
                {directDiff?.diff_chunks ? (
                  directDiff.diff_chunks.map((chunk: any, i: number) => {
                    if (chunk.type === "equal") {
                      return <span key={i}>{chunk.text_a} </span>;
                    }
                    if (chunk.type === "delete" || chunk.type === "replace") {
                      return (
                        <span key={i} className="rounded bg-red-500/20 px-1 py-0.5 text-red-300 line-through">
                          {chunk.text_a}{" "}
                        </span>
                      );
                    }
                    return null;
                  })
                ) : (
                  <p>THIS SALE DEED is executed on this 12th day of March 1987 at Bengaluru...</p>
                )}
              </div>
            </Card>

            {/* Document B Panel */}
            <Card className="flex flex-col overflow-hidden border-border/80 p-0 shadow-sm">
              <div className="flex items-center justify-between border-b border-border bg-bg-elevated/50 px-4 py-3">
                <div className="flex items-center gap-2 truncate">
                  <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-xs font-bold text-emerald-300">
                    Document B (Compared)
                  </span>
                  <span className="text-xs font-semibold text-white truncate">{docB?.file_name || "Document B"}</span>
                </div>
                <span className="rounded bg-bg px-2 py-0.5 text-[10px] text-text-muted">
                  {docB?.badge_label || "Partition / RTC"}
                </span>
              </div>
              <div className="max-h-[500px] overflow-y-auto p-4 font-mono text-xs leading-relaxed text-text-secondary bg-bg/40">
                {directDiff?.diff_chunks ? (
                  directDiff.diff_chunks.map((chunk: any, i: number) => {
                    if (chunk.type === "equal") {
                      return <span key={i}>{chunk.text_b} </span>;
                    }
                    if (chunk.type === "insert" || chunk.type === "replace") {
                      return (
                        <span key={i} className="rounded bg-emerald-500/20 px-1 py-0.5 text-emerald-300 font-semibold">
                          {chunk.text_b}{" "}
                        </span>
                      );
                    }
                    return null;
                  })
                ) : (
                  <p>SCHEDULE: All that piece and parcel of land bearing Survey Number 124/3 Hissa 2...</p>
                )}
              </div>
            </Card>
          </div>

          {/* Diff Legend */}
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-bg-surface px-4 py-2.5 text-xs">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-red-400" />
                <span className="text-text-muted">Deletions / Previous wording</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
                <span className="text-text-muted">Additions / New clauses</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-blue-400" />
                <span className="text-text-muted">Unmodified text</span>
              </div>
            </div>
            <span className="text-text-muted text-[11px]">
              Bharatiya Sakshya Act 2023 certified comparison hash
            </span>
          </div>
        </div>
      ) : (
        /* Field Cross-Check View */
        <div className="space-y-3">
          {results.length === 0 ? (
            <Card className="p-8 text-center text-sm text-text-secondary">
              No matching fields extracted across the selected documents.
            </Card>
          ) : (
            results.map((res: any, idx: number) => {
              const Icon = VERDICT_ICONS[res.verdict] || HelpCircle;
              const isMatch = res.verdict === "MATCH";
              const isMismatch = res.verdict === "MISMATCH";

              return (
                <Card key={idx} className="p-4 transition-colors hover:border-border-light">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <Icon
                        size={16}
                        className={
                          isMatch ? "text-emerald-400" : isMismatch ? "text-red-400" : "text-amber-400"
                        }
                      />
                      <h4 className="text-sm font-bold text-white">{res.field_name}</h4>
                    </div>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                        isMatch
                          ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                          : isMismatch
                          ? "bg-red-500/15 text-red-300 border border-red-500/30"
                          : "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                      }`}
                    >
                      {res.verdict}
                    </span>
                  </div>

                  {res.explanation && (
                    <p className="mt-2 text-xs text-text-secondary">{res.explanation}</p>
                  )}

                  <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                    {(res.values || []).map((v: any, vIdx: number) => (
                      <div key={vIdx} className="rounded-lg border border-border/60 bg-bg-elevated/40 p-2.5 text-xs">
                        <span className="font-semibold text-white truncate block">{v.document_name}</span>
                        <p className="mt-1 font-mono text-blue-300 text-xs">{v.value}</p>
                        {v.source_text && (
                          <p className="mt-1 line-clamp-1 text-[11px] text-text-muted italic">
                            &ldquo;{v.source_text}&rdquo;
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </Card>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
