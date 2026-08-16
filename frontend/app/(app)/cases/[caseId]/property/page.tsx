"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Landmark, Loader2, Save, FileSearch } from "lucide-react";
import { api } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { VERIFICATION_STYLES } from "@/lib/utils";

const FIELD_LABELS: Record<string, string> = {
  name: "Property name", address: "Address", state: "State", district: "District",
  taluk: "Taluk", village: "Village", survey_number: "Survey number",
  hissa_number: "Hissa number", plot_number: "Plot number", khata_number: "Khata number",
  registration_number: "Registration number", property_id_number: "Property ID",
  description: "Description",
};

export default function PropertyPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [data, setData] = useState<any>(null);
  const [extracted, setExtracted] = useState<Record<string, any[]>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function load() {
    try {
      const [p, e] = await Promise.all([
        api.getProperty(caseId),
        api.propertyEntities(caseId).catch(() => ({})),
      ]);
      setData(p);
      setExtracted(e || {});
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [caseId]);

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

  const fields: any[] = data?.fields || [];

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Property</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Field values are labelled by how they were verified. Jurisiva never
            claims ownership without document evidence.
          </p>
        </div>
        <Button onClick={save} disabled={saving || Object.keys(editValues).length === 0}>
          {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
          {saved ? "Saved" : "Save changes"}
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      <Card className="p-6">
        <div className="mb-4 flex items-center gap-2">
          <Landmark size={16} className="text-primary" />
          <h2 className="text-base font-semibold text-white">Property details</h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {fields.map((f) => {
            const v = VERIFICATION_STYLES[f.verification] || VERIFICATION_STYLES.UNVERIFIED;
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
                  className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-white placeholder-text-muted outline-none focus:border-primary"
                />
                {f.source_document_id && (
                  <p className="mt-1 text-[11px] text-text-muted">
                    Verified from document · page {f.source_page}
                  </p>
                )}
                {docEvidence && docEvidence.length > 0 && (
                  <div className="mt-1.5 space-y-1">
                    {docEvidence.slice(0, 2).map((e: any, i: number) => (
                      <p key={i} className="font-mono text-[11px] text-emerald-400/80">
                        From {e.document} p.{e.page}: &ldquo;{e.source_text?.slice(0, 90)}…&rdquo;
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
