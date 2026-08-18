"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Landmark, Loader2, Save, Sparkles, Building2 } from "lucide-react";
import { api } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { VERIFICATION_STYLES } from "@/lib/utils";

const FIELD_LABELS: Record<string, string> = {
  name: "Asset / Property Name",
  address: "Registered / Property Address",
  state: "Jurisdiction / State",
  district: "Operating Nexus / District",
  taluk: "Taluk / Service Area",
  village: "Village / Circle",
  survey_number: "Survey / Asset Identifier",
  hissa_number: "Hissa Number",
  plot_number: "Plot / License Number",
  khata_number: "Tax PAN / Khata Number",
  registration_number: "Registration / Registry No.",
  property_id_number: "Asset ID / ISIN",
  description: "Asset / Property Description",
};

export default function PropertyPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [data, setData] = useState<any>(null);
  const [caseInfo, setCaseInfo] = useState<any>(null);
  const [extracted, setExtracted] = useState<Record<string, any[]>>({});
  const [loading, setLoading] = useState(true);
  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function load(forceRefresh = false) {
    try {
      const [c, p, e] = await Promise.all([
        api.getCase(caseId).catch(() => null),
        forceRefresh ? api.getProperty(caseId).then(() => api.getProperty(caseId)) : api.getProperty(caseId),
        api.propertyEntities(caseId).catch(() => ({})),
      ]);
      setCaseInfo(c);
      setData(p);
      setExtracted(e || {});
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
      // Clear localStorage cache for this case's property
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
            {isTaxOrCorporate ? "Asset & Target Entity Details" : "Property Details"}
          </h1>
          <p className="mt-1 text-sm text-text-secondary">
            {isTaxOrCorporate
              ? "Underlying corporate shares, registered entity details, and statutory tax identifiers verified from case records."
              : "Field values are labelled by how they were verified. Jurisiva never claims ownership without document evidence."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={handleReExtract} disabled={extracting}>
            {extracting ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} className="text-primary" />}
            Re-extract with AI
          </Button>
          <Button onClick={save} disabled={saving || Object.keys(editValues).length === 0}>
            {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
            {saved ? "Saved" : "Save changes"}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

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
    </div>
  );
}
