"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AlertTriangle, Loader2, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";
import { Card, Badge } from "@/components/ui";
import { RISK_STYLES } from "@/lib/utils";

export default function RisksPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [risks, setRisks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setRisks(await api.getRisks(caseId));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [caseId]);

  async function toggleResolved(risk: any) {
    try {
      await api.updateRisk(risk.id, !risk.resolved);
      await load();
    } catch (e: any) {
      setError(e.message);
    }
  }

  if (loading) {
    return <div className="flex h-96 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  const counts = risks.reduce((acc: any, r) => {
    acc[r.level.toLowerCase()] = (acc[r.level.toLowerCase()] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Risks & Issues</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Every risk is created from document evidence — never without a source.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {risks.length === 0 ? (
        <Card className="flex flex-col items-center p-12 text-center">
          <CheckCircle2 size={32} className="mb-3 text-emerald-400" />
          <h3 className="text-base font-semibold text-white">No open risks</h3>
          <p className="mt-2 max-w-md text-sm text-text-secondary">
            Either no issues were detected, or documents haven&rsquo;t been compared yet.
            Run a comparison with 2+ documents to detect mismatches.
          </p>
        </Card>
      ) : (
        <>
          {/* Summary strip */}
          <div className="flex gap-3">
            {["critical", "high", "medium", "low"].map((level) => (
              <Card key={level} className="flex-1 p-4 text-center">
                <div className={`text-2xl font-semibold ${
                  level === "critical" ? "text-red-400" :
                  level === "high" ? "text-orange-400" :
                  level === "medium" ? "text-amber-400" : "text-emerald-400"
                }`}>
                  {counts[level] || 0}
                </div>
                <div className="text-xs capitalize text-text-muted">{level}</div>
              </Card>
            ))}
          </div>

          <div className="space-y-3">
            {risks.map((risk) => {
              const style = RISK_STYLES[risk.level] || RISK_STYLES.LOW;
              return (
                <Card key={risk.id} className="p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-400" />
                      <div>
                        <h3 className="text-sm font-semibold text-white">{risk.title}</h3>
                        <p className="mt-1 text-sm leading-relaxed text-text-secondary">{risk.description}</p>
                      </div>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-2">
                      <Badge className={style.className}>{risk.level}</Badge>
                      <Badge className="border-border bg-bg-elevated text-text-muted">
                        {risk.category.replace(/_/g, " ")}
                      </Badge>
                    </div>
                  </div>

                  {risk.recommended_action && (
                    <p className="mt-3 rounded-lg bg-primary/10 px-3 py-2 text-xs text-blue-300">
                      Recommended: {risk.recommended_action}
                    </p>
                  )}

                  <div className="mt-3 space-y-2">
                    {(risk.evidence || []).map((ev: any, i: number) => (
                      <div key={i} className="rounded-lg border border-border bg-bg px-3 py-2 font-mono text-xs">
                        <span className="text-text-muted">{ev.document_name} · p.{ev.page_number}:</span>{" "}
                        <span className="text-emerald-400">&ldquo;{ev.source_text?.slice(0, 160)}&rdquo;</span>
                      </div>
                    ))}
                  </div>

                  <button
                    onClick={() => toggleResolved(risk)}
                    className="mt-3 flex items-center gap-1.5 text-xs text-text-muted transition-colors hover:text-white"
                  >
                    <CheckCircle2 size={13} />
                    {risk.resolved ? "Reopen risk" : "Mark as resolved"}
                  </button>
                </Card>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
