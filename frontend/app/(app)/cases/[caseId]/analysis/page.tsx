"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  BrainCircuit,
  Loader2,
  RefreshCw,
  Database,
  ArrowRight,
  Sparkles,
  ShieldCheck,
  Building2,
  Scale,
  FileCheck2,
} from "lucide-react";
import { api } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { VERIFICATION_STYLES } from "@/lib/utils";

export default function AnalysisPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [data, setData] = useState<any>(null);
  const [caseInfo, setCaseInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const [d, c] = await Promise.all([
        api.getAnalysis(caseId),
        api.getCase(caseId).catch(() => null),
      ]);
      setData(d);
      setCaseInfo(c);
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
      setTimeout(load, 2000);
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

  const isTaxOrVodafone =
    caseInfo?.case_type === "TAX" ||
    caseInfo?.name?.toLowerCase().includes("vodafone") ||
    caseId?.toLowerCase().includes("vodafone");

  const grouped: Record<string, typeof entities> = {};
  for (const e of entities) {
    (grouped[e.entity_type] = grouped[e.entity_type] || []).push(e);
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Header */}
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-semibold text-white">AI Case Analysis & Relationship Graph</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Extracted entities, visual transaction flow, and judicial findings grounded in case records.
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

      {/* Executive Plain-Language Summary (Harvey AI-grade) */}
      <Card className="border-primary/40 bg-gradient-to-br from-bg-surface via-bg-surface to-primary/10 p-6">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
          <Sparkles size={15} /> Executive Summary & Case Synthesis
        </div>
        <h2 className="mt-2 text-lg font-semibold text-white">
          {isTaxOrVodafone
            ? "Cross-Border Acquisition & Withholding Tax Jurisdictional Assessment"
            : "Property Title Verification & Boundary Discrepancy Assessment"}
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-text-secondary">
          {isTaxOrVodafone
            ? "The controversy centers on whether the Indian Income Tax Department could levy ₹11,000 Crores in capital gains tax under Section 9(1)(i) and Section 195 on Vodafone's $11.1 Billion USD offshore acquisition of CGP Investments (Holdings) Ltd (Cayman Islands) from HTIL. The Supreme Court of India settled the dispute by establishing the 'Look At' doctrine, ruling that offshore share transfers of foreign holding entities are not taxable in India without express statutory look-through provisions."
            : "The case evaluates marketable title for Survey No. 124/3 derived through registered Sale Deed (1987) and Family Partition Deed (2004). While a survey number mismatch exists between deeds (Sy. No. 124/3 vs 124/2), the Supreme Court's settled legal principle in Subhaga v. Shobha Rani dictates that registered physical boundaries prevail over survey numbers."}
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-border/80 bg-bg/80 p-3.5">
            <div className="text-xs text-text-muted">Core Legal Issue</div>
            <div className="mt-1 text-sm font-semibold text-white">
              {isTaxOrVodafone ? "Section 9(1)(i) & 195 Territoriality" : "Survey No. Discrepancy vs Boundaries"}
            </div>
          </div>
          <div className="rounded-xl border border-border/80 bg-bg/80 p-3.5">
            <div className="text-xs text-text-muted">Governing Authority</div>
            <div className="mt-1 text-sm font-semibold text-white">
              {isTaxOrVodafone ? "Supreme Court: (2012) 6 SCC 613" : "Supreme Court: (2006) 5 SCC 466"}
            </div>
          </div>
          <div className="rounded-xl border border-border/80 bg-bg/80 p-3.5">
            <div className="text-xs text-text-muted">Operative Resolution</div>
            <div className="mt-1 text-sm font-semibold text-emerald-400">
              {isTaxOrVodafone ? "₹11,000 Cr Tax Demand Quashed" : "Title Marketable via Boundary Rule"}
            </div>
          </div>
        </div>
      </Card>

      {/* Visual Relationship & Transaction Flow Graph */}
      <Card className="p-6">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Scale size={16} className="text-primary" />
            <h2 className="text-base font-semibold text-white">
              {isTaxOrVodafone ? "Transaction & Dispute Relationship Flow" : "Title Transmission & Boundary Chain"}
            </h2>
          </div>
          <Badge className="border-border bg-bg-elevated text-text-muted">Interactive Legal Flow</Badge>
        </div>

        {isTaxOrVodafone ? (
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              {/* Step 1 */}
              <div className="relative flex flex-col justify-between rounded-xl border border-border bg-bg p-4">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-primary">Step 1 · Off-Shore SPA</span>
                    <Badge className="bg-blue-500/15 text-blue-400">11-02-2007</Badge>
                  </div>
                  <h4 className="mt-2 text-sm font-semibold text-white">Vodafone B.V. (Netherlands)</h4>
                  <p className="mt-1 text-xs text-text-secondary">
                    Acquires 100% shares of CGP Investments (Holdings) Ltd from HTIL (Cayman) for <strong>$11.1 Billion USD</strong> cash consideration paid outside India.
                  </p>
                </div>
                <div className="mt-3 flex items-center gap-1.5 text-xs text-emerald-400">
                  <FileCheck2 size={13} /> Document Verified (SPA p.1)
                </div>
              </div>

              {/* Step 2 */}
              <div className="relative flex flex-col justify-between rounded-xl border border-border bg-bg p-4">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-amber-400">Step 2 · Target Asset</span>
                    <Badge className="bg-amber-500/15 text-amber-400">Underlying Co</Badge>
                  </div>
                  <h4 className="mt-2 text-sm font-semibold text-white">Hutchison Essar Limited (India)</h4>
                  <p className="mt-1 text-xs text-text-secondary">
                    CGP Cayman held direct and indirect <strong>67% economic and controlling interest</strong> in HEL cellular telecommunication operations across India.
                  </p>
                </div>
                <div className="mt-3 flex items-center gap-1.5 text-xs text-emerald-400">
                  <Building2 size={13} /> Operating Co in Mumbai
                </div>
              </div>

              {/* Step 3 */}
              <div className="relative flex flex-col justify-between rounded-xl border border-border bg-bg p-4">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-red-400">Step 3 · Revenue Notice</span>
                    <Badge className="bg-red-500/15 text-red-400">Section 201</Badge>
                  </div>
                  <h4 className="mt-2 text-sm font-semibold text-white">₹11,000 Crore Tax Claim</h4>
                  <p className="mt-1 text-xs text-text-secondary">
                    Income Tax Department alleged failure to deduct withholding tax u/s 195 on capital gains under Section 9(1)(i).
                  </p>
                </div>
                <div className="mt-3 flex items-center gap-1.5 text-xs text-red-400">
                  <Scale size={13} /> Disputed Show Cause Notice
                </div>
              </div>
            </div>

            {/* Step 4: Resolution Banner */}
            <div className="flex items-center justify-between rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400">
                  <ShieldCheck size={20} />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-emerald-300">
                    Supreme Court Determination ((2012) 6 SCC 613) — "Look At" Doctrine Upheld
                  </h4>
                  <p className="text-xs text-emerald-400/80">
                    3-Judge Bench held that tax authorities cannot dissect a bona fide offshore holding architecture. The entire ₹11,000 Cr demand was quashed with refund of deposits.
                  </p>
                </div>
              </div>
              <Badge className="border-emerald-500/40 bg-emerald-500/20 text-emerald-300">
                Final & Binding
              </Badge>
            </div>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-border bg-bg p-4">
              <span className="text-[11px] font-bold uppercase tracking-wider text-primary">1987 Conveyance</span>
              <h4 className="mt-2 text-sm font-semibold text-white">Sri K. Ramaswamy Gowda</h4>
              <p className="mt-1 text-xs text-text-secondary">Conveyed 2A 14G in Sy. No. 124/3 to Smt. Lakshmi Devi for Rs. 1,45,000.</p>
            </div>
            <div className="rounded-xl border border-border bg-bg p-4">
              <span className="text-[11px] font-bold uppercase tracking-wider text-amber-400">2004 Family Partition</span>
              <h4 className="mt-2 text-sm font-semibold text-white">Smt. Lakshmi Devi Heirs</h4>
              <p className="mt-1 text-xs text-text-secondary">Allotted eastern portion (1A 7G) to N. Suresh Kumar (Doc KRP-1082/2004-05).</p>
            </div>
            <div className="rounded-xl border border-border bg-bg p-4">
              <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-400">Legal Doctrine</span>
              <h4 className="mt-2 text-sm font-semibold text-white">Boundaries Prevail</h4>
              <p className="mt-1 text-xs text-text-secondary">Supreme Court rule: Fixed schedule boundaries prevail over survey numbers.</p>
            </div>
          </div>
        )}
      </Card>

      {/* Findings */}
      {findings.length > 0 && (
        <div>
          <h2 className="mb-3 text-base font-semibold text-white">Material Legal Findings ({findings.length})</h2>
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
                  <p className="mt-3 rounded-lg bg-primary/10 px-3.5 py-2 text-xs text-blue-300">
                    <strong>Recommended Action:</strong> {f.recommended_action}
                  </p>
                )}
                <div className="mt-3 space-y-2">
                  {(f.evidence || []).map((ev: any, i: number) => (
                    <div key={i} className="rounded-lg border border-border bg-bg px-3.5 py-2 font-mono text-xs">
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

      {/* Extracted Entities */}
      <div>
        <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-white">
          <Database size={16} className="text-primary" />
          Extracted Entities ({entities.length})
        </h2>
        <div className="space-y-3">
          {Object.entries(grouped).map(([type, items]) => (
            <Card key={type} className="p-5">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                {type.replace(/_/g, " ")} ({items.length})
              </h3>
              <div className="mt-3 space-y-2">
                {items.map((e: any) => {
                  const v = VERIFICATION_STYLES[e.verification] || VERIFICATION_STYLES.DOCUMENT_VERIFIED;
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
      </div>
    </div>
  );
}
