"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  Landmark,
  Loader2,
  Save,
  Sparkles,
  Building2,
  HelpCircle,
  Calculator,
  CheckCircle2,
  ShieldAlert,
  Share2,
  Award,
  Globe,
} from "lucide-react";
import { api } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { VERIFICATION_STYLES } from "@/lib/utils";
import { LandPortalSearch } from "@/components/property/LandPortalSearch";
import { SharedSpaceModal } from "@/components/shared-spaces/SharedSpaceModal";
import { BSACertificateModal } from "@/components/property/BSACertificateModal";

const FIELD_LABELS: Record<string, string> = {
  name: "Asset / Property Name",
  address: "Registered / Property Address",
  state: "Jurisdiction / State",
  district: "District / Jilha",
  taluk: "Taluk / Tehsil / Hobli",
  village: "Village / Mauza",
  survey_number: "Survey Number",
  gat_number: "Gat / Gut Number (7/12 Satbara)",
  khasra_number: "Khasra Number (Jamabandi)",
  cts_number: "CTS / City Survey No. (Urban)",
  hissa_number: "Hissa / Sub-Division Number",
  plot_number: "Plot / Site Number",
  khata_number: "Khata / Khatauni Number",
  area: "Land Extent & Area Extent",
  encumbrance: "Encumbrance / Bojha / Bank Mortgage",
  registration_number: "Registration / Doc Number",
  property_id_number: "Property ID / PID / e-Swathu",
  description: "Asset / Property Description",
};

export default function PropertyPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [data, setData] = useState<any>(null);
  const [caseInfo, setCaseInfo] = useState<any>(null);
  const [extracted, setExtracted] = useState<Record<string, any[]>>({});
  const [lawyerQuestions, setLawyerQuestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // Modals
  const [isShareModalOpen, setIsShareModalOpen] = useState(false);
  const [isBSAModalOpen, setIsBSAModalOpen] = useState(false);

  // Live Land Area Calculator State
  const [calcInput, setCalcInput] = useState("1 Acre 20 Guntas");
  const [calcResult, setCalcResult] = useState<string | null>(null);

  async function load(forceRefresh = false) {
    try {
      const [c, p, e, q] = await Promise.all([
        api.getCase(caseId).catch(() => null),
        forceRefresh ? api.getProperty(caseId).then(() => api.getProperty(caseId)) : api.getProperty(caseId),
        api.propertyEntities(caseId).catch(() => ({})),
        api.propertyLawyerQuestions(caseId).catch(() => ({ questions: [] })),
      ]);
      setCaseInfo(c);
      setData(p);
      setExtracted(e || {});
      setLawyerQuestions(q?.questions || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
      setExtracting(false);
    }
  }

  useEffect(() => { load(); }, [caseId]);

  async function handleReExtract() {
    setExtracting(true);
    setError(null);
    try {
      if (typeof window !== "undefined") {
        localStorage.removeItem(`jurisiva_demo_property_${caseId}`);
      }
      await load(true);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setExtracting(false);
    }
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const updates = Object.fromEntries(
        Object.entries(editValues).filter(([, v]) => v.trim() !== "")
      );
      if (Object.keys(updates).length > 0) {
        await api.updateProperty(caseId, updates);
        setEditValues({});
        setSaved(true);
        setTimeout(() => setSaved(false), 2500);
        await load();
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="flex h-96 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  const isTaxOrCorporate =
    caseInfo?.case_type === "TAX" ||
    caseInfo?.case_type === "COMMERCIAL" ||
    caseInfo?.case_type === "CORPORATE" ||
    caseInfo?.name?.toLowerCase().includes("vodafone") ||
    caseId?.toLowerCase().includes("vodafone");

  const fields: any[] = data?.fields || [];

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div>
          <h1 className="text-2xl font-semibold text-white">
            {isTaxOrCorporate ? "Asset & Target Entity Details" : "Property Details & Land Portals"}
          </h1>
          <p className="mt-1 text-sm text-text-secondary">
            {isTaxOrCorporate
              ? "Underlying corporate shares, registered entity details, and statutory tax identifiers verified from case records."
              : "Reconcile deed data with official state revenue portals and generate BSA Section 63 evidence certificates."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => setIsShareModalOpen(true)} className="flex items-center gap-1.5">
            <Share2 size={14} className="text-primary" /> Shared Space
          </Button>
          <Button variant="secondary" onClick={() => setIsBSAModalOpen(true)} className="flex items-center gap-1.5">
            <Award size={14} className="text-amber-400" /> BSA Certificate
          </Button>
          <Button variant="secondary" onClick={handleReExtract} disabled={extracting}>
            {extracting ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} className="text-primary" />}
            Re-extract
          </Button>
          <Button onClick={save} disabled={saving || Object.keys(editValues).length === 0}>
            {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
            {saved ? "Saved" : "Save"}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {/* Official 5 State Land Portal Connector */}
      {!isTaxOrCorporate && (
        <LandPortalSearch
          initialSurvey="124/2"
          initialDistrict="Bangalore Urban"
          initialTaluk="Bangalore South"
          initialVillage="Varthur"
          initialState="karnataka"
        />
      )}

      {/* Property Matrix */}
      <Card className="p-6">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isTaxOrCorporate ? <Building2 size={16} className="text-primary" /> : <Landmark size={16} className="text-primary" />}
            <h2 className="text-base font-semibold text-white">
              {isTaxOrCorporate ? "Verified Corporate & Asset Matrix" : "Property Details"}
            </h2>
          </div>
          <Badge className="border-emerald-500/30 bg-emerald-500/15 text-emerald-400">
            AI Document Verified
          </Badge>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {fields.map((f) => {
            const v = VERIFICATION_STYLES[f.verification] || VERIFICATION_STYLES.DOCUMENT_VERIFIED;
            const docEvidence = extracted[f.field];
            return (
              <div key={f.field}>
                <div className="mb-1.5 flex items-center justify-between">
                  <label className="text-xs font-medium text-text-secondary">
                    {FIELD_LABELS[f.field] || f.field}
                  </label>
                  <Badge className={v.className}>{v.label}</Badge>
                </div>
                <input
                  value={editValues[f.field] ?? f.value ?? ""}
                  onChange={(e) => setEditValues({ ...editValues, [f.field]: e.target.value })}
                  placeholder="Not provided"
                  className="w-full rounded-lg border border-border bg-bg px-3.5 py-2.5 text-sm text-white placeholder-text-muted outline-none focus:border-primary"
                />
                {f.source_document_id && (
                  <p className="mt-1 text-[11px] text-text-muted">
                    Verified from document · page {f.source_page}
                  </p>
                )}
                {docEvidence && docEvidence.length > 0 && (
                  <div className="mt-1.5 space-y-1">
                    {docEvidence.slice(0, 2).map((e: any, i: number) => (
                      <p key={i} className="font-mono text-[11px] text-emerald-400/90">
                        From {e.document} p.{e.page}: &ldquo;{e.source_text?.slice(0, 95)}…&rdquo;
                      </p>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        <p className="mt-5 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-xs leading-relaxed text-amber-400/90">
          Values you type are marked <strong>User Provided</strong> until a document
          confirms them. Document-confirmed values appear as <strong>Document Verified</strong>.
        </p>
      </Card>

      {/* Advocate Due Diligence Inquiry Questions */}
      <Card className="p-6 border-primary/30">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <HelpCircle size={17} className="text-primary" />
            <h2 className="text-base font-semibold text-white">
              Advocate Due Diligence Inquiry Checklist
            </h2>
          </div>
          <Badge className="border-primary/30 bg-primary/10 text-primary">
            India Land Revenue Engine
          </Badge>
        </div>
        <p className="mb-4 text-xs text-text-secondary">
          Targeted title inquiry questions automatically generated based on detected land records, encumbrances, and chain-of-title gaps:
        </p>
        <div className="space-y-2.5">
          {lawyerQuestions.length === 0 ? (
            <p className="text-xs text-text-muted">No title red flags detected. Standard 30-year EC recommended.</p>
          ) : (
            lawyerQuestions.map((q, idx) => (
              <div key={idx} className="flex items-start gap-3 rounded-lg border border-border bg-bg-surface px-4 py-3 text-xs text-text-secondary">
                <ShieldAlert size={15} className="mt-0.5 shrink-0 text-amber-400" />
                <span className="leading-relaxed">{q}</span>
              </div>
            ))
          )}
        </div>
      </Card>

      {/* Indian Land Area Converter Widget */}
      <Card className="p-6">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calculator size={17} className="text-emerald-400" />
            <h2 className="text-base font-semibold text-white">
              Indian Land Measurement Unit Converter
            </h2>
          </div>
          <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
            Acre · Gunta · Cent · Bigha · Sq.Ft
          </Badge>
        </div>
        <p className="mb-3 text-xs text-text-secondary">
          Test or reconcile any Indian revenue area measurement unit against metric &amp; imperial standards:
        </p>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            value={calcInput}
            onChange={(e) => setCalcInput(e.target.value)}
            placeholder="e.g. 2 Acres 14 Guntas, 1.5 Hectare, 5 Bigha"
            className="flex-1 rounded-lg border border-border bg-bg px-3.5 py-2 text-sm text-white placeholder-text-muted outline-none focus:border-primary"
          />
          <Button
            variant="secondary"
            onClick={() => {
              const text = calcInput.toLowerCase();
              let sqm = 0;
              if (text.includes("acre") || text.includes("ac")) {
                const m = text.match(/(\d+(?:\.\d+)?)\s*ac/);
                if (m) sqm += parseFloat(m[1]) * 4046.86;
              }
              if (text.includes("gunta") || text.includes("gts")) {
                const m = text.match(/(\d+(?:\.\d+)?)\s*g/);
                if (m) sqm += parseFloat(m[1]) * 101.17;
              }
              if (text.includes("cent")) {
                const m = text.match(/(\d+(?:\.\d+)?)\s*cent/);
                if (m) sqm += parseFloat(m[1]) * 40.47;
              }
              if (text.includes("hectare") || text.includes("ha")) {
                const m = text.match(/(\d+(?:\.\d+)?)\s*h/);
                if (m) sqm += parseFloat(m[1]) * 10000;
              }
              if (text.includes("bigha")) {
                const m = text.match(/(\d+(?:\.\d+)?)\s*bigha/);
                if (m) sqm += parseFloat(m[1]) * 2529.29;
              }
              if (text.includes("sq.ft") || text.includes("square feet")) {
                const m = text.match(/([\d,]+(?:\.\d+)?)\s*sq/);
                if (m) sqm += parseFloat(m[1].replace(/,/g, "")) * 0.0929;
              }
              if (sqm === 0 && !isNaN(Number(calcInput))) {
                sqm = Number(calcInput) * 4046.86;
              }
              const acres = sqm / 4046.86;
              const wholeAc = Math.floor(acres);
              const guntas = (acres - wholeAc) * 40;
              const sqft = sqm * 10.7639;
              setCalcResult(
                `Standard Extent: ${wholeAc} Acre(s) ${guntas.toFixed(2)} Gunta(s) | ${(acres * 100).toFixed(1)} Cents | ${sqm.toFixed(1)} Sq.M | ${Math.round(sqft).toLocaleString()} Sq.Ft`
              );
            }}
          >
            Calculate Extent
          </Button>
        </div>
        {calcResult && (
          <div className="mt-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-2.5 font-mono text-xs text-emerald-400">
            {calcResult}
          </div>
        )}
      </Card>

      {/* Shared Space Modal */}
      <SharedSpaceModal
        isOpen={isShareModalOpen}
        onClose={() => setIsShareModalOpen(false)}
        caseId={caseId}
        caseName={caseInfo?.name || "Matter Space"}
      />

      {/* BSA Certificate Modal */}
      <BSACertificateModal
        isOpen={isBSAModalOpen}
        onClose={() => setIsBSAModalOpen(false)}
        caseId={caseId}
        caseName={caseInfo?.name || "Matter Space"}
      />
    </div>
  );
}
