"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { GitCompare, Loader2, CheckCircle2, XCircle, HelpCircle, MinusCircle } from "lucide-react";
import { api } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { VERDICT_STYLES } from "@/lib/utils";

const VERDICT_ICONS: Record<string, any> = {
  MATCH: CheckCircle2, MISMATCH: XCircle, MISSING: MinusCircle, UNCERTAIN: HelpCircle,
};

export default function ComparisonPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [documents, setDocuments] = useState<any[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      // Poll for results
      setTimeout(async () => {
        const res = await api.getComparison(caseId);
        setResults(res);
        setComparing(false);
      }, 5000);
    } catch (e: any) {
      setError(e.message);
      setComparing(false);
    }
  }

  if (loading) {
    return <div className="flex h-96 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Document Comparison</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Select two or more processed documents to cross-check key fields. Every mismatch shows its evidence.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {/* Document selection */}
      <Card className="p-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">
            Select documents ({selected.size} selected — minimum 2)
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

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-base font-semibold text-white">Comparison results</h2>
          {results.map((r) => {
            const Icon = VERDICT_ICONS[r.verdict] || HelpCircle;
            return (
              <Card key={r.id} className="p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <Icon size={16} className={
                      r.verdict === "MATCH" ? "text-emerald-400" :
                      r.verdict === "MISMATCH" ? "text-red-400" :
                      r.verdict === "MISSING" ? "text-amber-400" : "text-slate-400"
                    } />
                    <span className="text-sm font-semibold capitalize text-white">
                      {(r.field_name || "field").replace(/_/g, " ")}
                    </span>
                  </div>
                  <Badge className={VERDICT_STYLES[r.verdict]}>{r.verdict}</Badge>
                </div>

                {r.explanation && (
                  <p className="mt-2 text-xs text-text-secondary">{r.explanation}</p>
                )}

                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  {(r.values || []).map((v: any, i: number) => (
                    <div key={i} className="rounded-lg border border-border bg-bg px-3 py-2.5">
                      <div className="text-[11px] text-text-muted">{v.document_name} · p.{v.page_number}</div>
                      <div className="mt-1 font-mono text-sm text-white">{v.value}</div>
                      {v.source_text && (
                        <div className="mt-1 font-mono text-[11px] text-emerald-400/80">
                          &ldquo;{v.source_text.slice(0, 110)}…&rdquo;
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
