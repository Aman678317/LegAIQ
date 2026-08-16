"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { BrainCircuit, Loader2, RefreshCw, Database } from "lucide-react";
import { api } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { VERIFICATION_STYLES } from "@/lib/utils";

export default function AnalysisPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const d = await api.getAnalysis(caseId);
      setData(d);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [caseId]);

  async function runAnalysis() {
    setRunning(true);
    try {
      await api.runAnalysis(caseId);
      setTimeout(load, 3000);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  }

  if (loading) {
    return <div className="flex h-96 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  const entities = data?.entities || [];
  const findings = data?.findings || [];

  const grouped: Record<string, typeof entities> = {};
  for (const e of entities) {
    (grouped[e.entity_type] = grouped[e.entity_type] || []).push(e);
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">AI Analysis</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Extracted entities and findings — every value traceable to its source page.
          </p>
        </div>
        <Button onClick={runAnalysis} disabled={running} variant="secondary">
          {running ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
          Re-run analysis
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {entities.length === 0 && findings.length === 0 ? (
        <Card className="flex flex-col items-center p-12 text-center">
          <BrainCircuit size={32} className="mb-3 text-text-muted" />
          <h3 className="text-base font-semibold text-white">No analysis yet</h3>
          <p className="mt-2 max-w-md text-sm text-text-secondary">
            Upload documents and let processing complete. Extraction runs automatically
            after OCR — entities and findings will appear here.
          </p>
        </Card>
      ) : (
        <>
          {findings.length > 0 && (
            <div>
              <h2 className="mb-3 text-base font-semibold text-white">Findings</h2>
              <div className="space-y-3">
                {findings.map((f: any) => (
                  <Card key={f.id} className="p-5">
                    <div className="flex items-start justify-between gap-4">
                      <h3 className="text-sm font-semibold text-white">{f.finding}</h3>
                      {f.risk_level && (
                        <Badge className={`shrink-0 ${
                          f.risk_level === "HIGH" || f.risk_level === "CRITICAL"
                            ? "border-red-500/30 bg-red-500/15 text-red-400"
                            : "border-amber-500/30 bg-amber-500/15 text-amber-400"
                        }`}>
                          {f.risk_level}
                        </Badge>
                      )}
                    </div>
                    {f.explanation && <p className="mt-2 text-sm text-text-secondary">{f.explanation}</p>}
                    {f.recommended_action && (
                      <p className="mt-3 rounded-lg bg-primary/10 px-3 py-2 text-xs text-blue-300">
                        Action: {f.recommended_action}
                      </p>
                    )}
                    <div className="mt-3 space-y-2">
                      {(f.evidence || []).map((ev: any, i: number) => (
                        <div key={i} className="rounded-lg border border-border bg-bg px-3 py-2 font-mono text-xs">
                          <span className="text-text-muted">{ev.document_name} · p.{ev.page_number}:</span>{" "}
                          <span className="text-emerald-400">&ldquo;{ev.source_text?.slice(0, 160)}&rdquo;</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}

          <div>
            <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-white">
              <Database size={16} className="text-primary" />
              Extracted entities ({entities.length})
            </h2>
            {Object.entries(grouped).map(([type, items]) => (
              <Card key={type} className="mb-3 p-5">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                  {type.replace(/_/g, " ")} ({items.length})
                </h3>
                <div className="mt-3 space-y-2">
                  {items.map((e: any) => {
                    const v = VERIFICATION_STYLES[e.verification] || VERIFICATION_STYLES.UNVERIFIED;
                    return (
                      <div key={e.id} className="flex items-start justify-between gap-4 rounded-lg border border-border bg-bg px-4 py-3">
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-white">{e.value}</div>
                          <div className="mt-1 font-mono text-[11px] text-text-muted">
                            Source: &ldquo;{e.source_text?.slice(0, 140)}&rdquo;
                          </div>
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          <span className="text-xs text-text-muted">{(e.confidence * 100).toFixed(0)}%</span>
                          <Badge className={v.className}>{v.label}</Badge>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
