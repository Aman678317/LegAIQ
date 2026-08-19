"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import { GitCompare, Loader2, CheckCircle2, XCircle, HelpCircle, MinusCircle, ChevronRight, ChevronLeft, Code, FileText } from "lucide-react";
import { api } from "@/lib/api";
import { Button, Card, Badge, Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui";
import { VERDICT_STYLES } from "@/lib/utils";

const VERDICT_ICONS: Record<string, any> = {
  MATCH: CheckCircle2, MISMATCH: XCircle, MISSING: MinusCircle, UNCERTAIN: HelpCircle,
};

// Simple diff algorithm for inline comparison
function diffStrings(a: string, b: string): Array<{type: 'equal' | 'add' | 'remove'; value: string}> {
  const result: Array<{type: 'equal' | 'add' | 'remove'; value: string}> = [];
  
  if (a === b) {
    return [{type: 'equal', value: a}];
  }
  
  // Word-level diff
  const wordsA = a.split(/(\s+)/);
  const wordsB = b.split(/(\s+)/);
  
  let i = 0, j = 0;
  while (i < wordsA.length || j < wordsB.length) {
    if (i < wordsA.length && j < wordsB.length && wordsA[i] === wordsB[j]) {
      result.push({type: 'equal', value: wordsA[i]});
      i++; j++;
    } else if (i < wordsA.length && (j >= wordsB.length || !wordsB.slice(j).includes(wordsA[i]))) {
      result.push({type: 'remove', value: wordsA[i]});
      i++;
    } else if (j < wordsB.length) {
      result.push({type: 'add', value: wordsB[j]});
      j++;
    } else {
      i++; j++;
    }
  }
  
  return result;
}

function DiffView({ valueA, valueB, labelA, labelB }: { 
  valueA: string; 
  valueB: string; 
  labelA: string; 
  labelB: string;
}) {
  const diffs = useMemo(() => diffStrings(valueA || "", valueB || ""), [valueA, valueB]);
  
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-xs text-text-muted">
        <span className="rounded border border-red-500/30 bg-red-500/10 px-1.5 py-0.5">{labelA}</span>
        <ChevronRight size={12} />
        <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5">{labelB}</span>
      </div>
      <div className="font-mono text-sm leading-relaxed">
        {diffs.map((d, i) => (
          <span key={i} className={
            d.type === 'equal' ? 'text-text-secondary' :
            d.type === 'add' ? 'bg-emerald-500/20 text-emerald-300 rounded px-0.5' :
            'bg-red-500/20 text-red-300 rounded px-0.5 line-through'
          }>
            {d.value}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function ComparisonPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [documents, setDocuments] = useState<any[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [selectedResult, setSelectedResult] = useState<any>(null);

  useEffect(() => {
    Promise.all([
      api.listDocuments(caseId),
      api.getComparison(caseId).catch(() => []),
    ]).then(([docs, res]) => {
      setDocuments(docs.filter((d: any) => d.status === "COMPLETED"));
      setResults(res);
    }).catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [caseId]);

  function toggle(docId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(docId)) next.delete(docId);
      else if (next.size < 6) next.add(docId);
      return next;
    });
  }

  async function runComparison() {
    if (selected.size < 2) return;
    setComparing(true);
    setError(null);
    try {
      await api.compareDocuments(caseId, Array.from(selected));
      // Poll for results with better UX
      const pollForResults = async (attempts = 0) => {
        if (attempts > 12) { // 60 seconds max
          setComparing(false);
          return;
        }
        await new Promise(r => setTimeout(r, 5000));
        const res = await api.getComparison(caseId);
        if (res.length > 0) {
          setResults(res);
          setComparing(false);
        } else {
          await pollForResults(attempts + 1);
        }
      };
      await pollForResults();
    } catch (e: any) {
      setError(e.message);
      setComparing(false);
    }
  }

  if (loading) {
    return <div className="flex h-96 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  const mismatches = results.filter(r => r.verdict === 'MISMATCH');
  const missing = results.filter(r => r.verdict === 'MISSING');
  const matches = results.filter(r => r.verdict === 'MATCH');

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Document Comparison</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Select two or more processed documents to cross-check key fields. Every mismatch shows its evidence with inline diff.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {/* Document selection */}
      <Card className="p-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">
            Select documents ({selected.size} selected — minimum 2, maximum 6)
          </h2>
          <Button size="sm" onClick={runComparison} disabled={selected.size < 2 || comparing}>
            {comparing ? <Loader2 size={14} className="animate-spin" /> : <GitCompare size={14} />}
            {comparing ? "Comparing…" : "Compare"}
          </Button>
        </div>
        {documents.length === 0 ? (
          <p className="text-sm text-text-secondary">
            No processed documents yet. Upload documents and wait for OCR + extraction to complete.
          </p>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {documents.map((doc) => (
              <button
                key={doc.id}
                onClick={() => toggle(doc.id)}
                className={`flex items-center gap-3 rounded-lg border px-4 py-3 text-left transition-colors ${
                  selected.has(doc.id)
                    ? "border-primary bg-primary/10"
                    : "border-border bg-bg hover:border-border-light"
                }`}
              >
                <div className={`h-4 w-4 shrink-0 rounded border ${
                  selected.has(doc.id) ? "border-primary bg-primary" : "border-border-light"
                }`} />
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-white">{doc.file_name}</div>
                  <div className="text-xs text-text-muted">{doc.page_count || "?"} pages</div>
                </div>
              </button>
            ))}
          </div>
        )}
      </Card>

      {/* Summary stats */}
      {results.length > 0 && (
        <div className="flex flex-wrap gap-3">
          <Badge className={VERDICT_STYLES.MATCH}><CheckCircle2 size={12} className="mr-1" /> {matches.length} Match</Badge>
          <Badge className={VERDICT_STYLES.MISMATCH}><XCircle size={12} className="mr-1" /> {mismatches.length} Mismatch</Badge>
          <Badge className={VERDICT_STYLES.MISSING}><MinusCircle size={12} className="mr-1" /> {missing.length} Missing</Badge>
        </div>
      )}

      {/* Results Tabs */}
      {results.length > 0 && (
        <Card>
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="detail">Detail View</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="p-6">
              <div className="space-y-4">
                {mismatches.length > 0 && (
                  <div>
                    <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-red-400">
                      <XCircle size={14} /> Mismatches ({mismatches.length})
                    </h3>
                    {mismatches.map((r) => (
                      <div key={r.id} className="rounded-lg border border-red-500/20 bg-red-500/5 p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <XCircle size={14} className="text-red-400" />
                            <span className="text-sm font-semibold text-white capitalize">
                              {(r.field_name || "field").replace(/_/g, " ")}
                            </span>
                          </div>
                          <Badge className={VERDICT_STYLES[r.verdict]}>MISMATCH</Badge>
                        </div>
                        {r.explanation && <p className="mt-2 text-xs text-text-secondary">{r.explanation}</p>}
                        <div className="mt-3 grid gap-2 sm:grid-cols-2">
                          {(r.values || []).map((v: any, i: number) => (
                            <div key={i} className="rounded-lg border border-border bg-bg px-3 py-2">
                              <div className="text-[11px] text-text-muted">{v.document_name} · p.{v.page_number}</div>
                              <div className="mt-1 font-mono text-sm text-white">{v.value}</div>
                            </div>
                          ))}
                        </div>
                        <Button 
                          size="sm" 
                          variant="ghost" 
                          className="mt-3"
                          onClick={() => { setSelectedResult(r); setActiveTab('detail'); }}
                        >
                          <Code size={12} className="mr-1" /> View detailed diff
                        </Button>
                      </div>
                    ))}
                  </div>
                )}

                {missing.length > 0 && (
                  <div>
                    <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-amber-400">
                      <MinusCircle size={14} /> Missing Fields ({missing.length})
                    </h3>
                    {missing.map((r) => (
                      <div key={r.id} className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <MinusCircle size={14} className="text-amber-400" />
                            <span className="text-sm font-semibold text-white capitalize">
                              {(r.field_name || "field").replace(/_/g, " ")}
                            </span>
                          </div>
                          <Badge className={VERDICT_STYLES[r.verdict]}>MISSING</Badge>
                        </div>
                        {r.explanation && <p className="mt-2 text-xs text-text-secondary">{r.explanation}</p>}
                        <div className="mt-3 grid gap-2 sm:grid-cols-2">
                          {(r.values || []).map((v: any, i: number) => (
                            <div key={i} className="rounded-lg border border-border bg-bg px-3 py-2">
                              <div className="text-[11px] text-text-muted">{v.document_name} · p.{v.page_number}</div>
                              <div className="mt-1 font-mono text-sm text-white">{v.value}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {matches.length > 0 && (
                  <div>
                    <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-emerald-400">
                      <CheckCircle2 size={14} /> Matches ({matches.length})
                    </h3>
                    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                      {matches.map((r) => (
                        <div key={r.id} className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                          <div className="flex items-center gap-2">
                            <CheckCircle2 size={12} className="text-emerald-400" />
                            <span className="text-sm font-medium text-white capitalize">
                              {(r.field_name || "field").replace(/_/g, " ")}
                            </span>
                          </div>
                          <div className="mt-1 text-xs text-emerald-400/80">
                            {r.values?.[0]?.value || "Consistent across documents"}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="detail" className="p-6">
              {selectedResult ? (
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="sm" onClick={() => { setSelectedResult(null); setActiveTab('overview'); }}>
                        <ChevronLeft size={14} /> Back to overview
                      </Button>
                      <span className="text-sm font-semibold text-white capitalize">
                        {(selectedResult.field_name || "field").replace(/_/g, " ")}
                      </span>
                      <Badge className={VERDICT_STYLES[selectedResult.verdict]}>{selectedResult.verdict}</Badge>
                    </div>
                    {selectedResult.verdict === 'MISMATCH' && selectedResult.values?.length >= 2 && (
                      <Badge className="bg-primary/10 text-primary border-primary/30">
                        <Code size={12} className="mr-1" /> Diff Available
                      </Badge>
                    )}
                  </div>

                  {selectedResult.verdict === 'MISMATCH' && selectedResult.values?.length >= 2 && (
                    <div className="space-y-6">
                      <h4 className="text-sm font-semibold text-primary">Inline Diff (Pairwise)</h4>
                      {selectedResult.values.slice(0, 2).map((v: any, i: number, arr: any[]) => {
                        if (i === arr.length - 1) return null;
                        const next = arr[i + 1];
                        return (
                          <DiffView 
                            key={`${v.document_id}-${next.document_id}`}
                            valueA={v.value || ""}
                            valueB={next.value || ""}
                            labelA={`${v.document_name} (p.${v.page_number})`}
                            labelB={`${next.document_name} (p.${next.page_number})`}
                          />
                        );
                      })}
                    </div>
                  )}

                  <div className="space-y-4">
                    <h4 className="text-sm font-semibold text-white">All Values</h4>
                    {(selectedResult.values || []).map((v: any, i: number) => (
                      <div key={i} className="rounded-lg border border-border bg-bg p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="text-sm font-medium text-white">{v.document_name}</div>
                            <div className="text-xs text-text-muted">Page {v.page_number} · Confidence: {(v.confidence ? (v.confidence * 100).toFixed(0) : '?')}%</div>
                          </div>
                        </div>
                        <div className="mt-3 font-mono text-sm text-white whitespace-pre-wrap">{v.value}</div>
                        {v.source_text && (
                          <div className="mt-3 p-3 rounded border border-border bg-bg-elevated">
                            <div className="text-[11px] text-text-muted mb-1">Source text (verbatim)</div>
                            <div className="font-mono text-[11px] text-emerald-400/80">&ldquo;{v.source_text}&rdquo;</div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {selectedResult.explanation && (
                    <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
                      <h4 className="text-sm font-semibold text-amber-400 mb-2">Analysis</h4>
                      <p className="text-sm text-text-secondary">{selectedResult.explanation}</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <FileText size={32} className="mb-3 text-text-muted" />
                  <p className="text-sm text-text-secondary">Select a field from the Overview tab to see detailed comparison</p>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </Card>
      )}
    </div>
  );
}
