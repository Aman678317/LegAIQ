import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { PenLine, Loader2, Plus, Trash2, Save, Download, Printer, Cpu } from "lucide-react";
import { api } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { formatDateTime, DRAFT_TYPES } from "@/lib/utils";
import { downloadDraftFile } from "@/lib/reportExporter";
import { checkOllamaStatus, OllamaStatus } from "@/lib/ollama";

export default function DraftingPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [drafts, setDrafts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus>({
    online: false,
    models: [],
    activeModel: null,
  });

  // Create form
  const [showCreate, setShowCreate] = useState(false);
  const [draftType, setDraftType] = useState("legal_notice");
  const [title, setTitle] = useState("");
  const [instructions, setInstructions] = useState("");
  const [creating, setCreating] = useState(false);

  // Editor
  const [editing, setEditing] = useState<any>(null);
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      setDrafts(await api.listDrafts(caseId));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    checkOllamaStatus().then(setOllamaStatus);
  }, [caseId]);

  async function createDraft(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const draft = await api.createDraft(caseId, { draft_type: draftType, title, instructions });
      setShowCreate(false);
      setTitle("");
      setInstructions("");
      setEditing(draft);
      setContent(draft.content);
      await load();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  }

  async function saveDraft() {
    if (!editing) return;
    setSaving(true);
    try {
      const updated = await api.updateDraft(editing.id, { content });
      setEditing(updated);
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function removeDraft(id: string) {
    if (!confirm("Delete this draft?")) return;
    try {
      await api.deleteDraft(id);
      if (editing?.id === id) setEditing(null);
      await load();
    } catch (e: any) {
      setError(e.message);
    }
  }

  if (loading) {
    return <div className="flex h-96 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Drafting Studio</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Drafts are grounded in verified case facts. Missing facts appear as [VERIFY: …] placeholders.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {ollamaStatus.online ? (
            <div className="flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs text-emerald-400">
              <Cpu size={13} className="animate-pulse text-emerald-400" />
              <span className="font-mono text-xs">Ollama: {ollamaStatus.activeModel || "Online"}</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 rounded-lg border border-border bg-bg-elevated px-2.5 py-1 text-xs text-text-muted">
              <Cpu size={13} className="text-primary" />
              <span>Local Legal AI Engine</span>
            </div>
          )}
          <Button onClick={() => setShowCreate(!showCreate)}>
            <Plus size={15} />
            New Draft
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {showCreate && (
        <Card className="p-6">
          <h2 className="text-base font-semibold text-white">Create a draft</h2>
          <form onSubmit={createDraft} className="mt-4 space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-sm text-text-secondary">Draft type</label>
                <select
                  value={draftType}
                  onChange={(e) => setDraftType(e.target.value)}
                  className="w-full rounded-lg border border-border bg-bg px-3.5 py-2.5 text-sm text-white outline-none focus:border-primary"
                >
                  {DRAFT_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-sm text-text-secondary">Title *</label>
                <input
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g., Legal Notice to Vendor — Whitefield property"
                  className="w-full rounded-lg border border-border bg-bg px-3.5 py-2.5 text-sm text-white placeholder-text-muted outline-none focus:border-primary"
                />
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-sm text-text-secondary">Instructions *</label>
              <textarea
                required
                rows={3}
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="Describe what the draft should cover, whom it addresses, and any specific relief or timeline."
                className="w-full rounded-lg border border-border bg-bg px-3.5 py-2.5 text-sm text-white placeholder-text-muted outline-none focus:border-primary"
              />
            </div>
            <Button type="submit" disabled={creating}>
              {creating ? <Loader2 size={15} className="animate-spin" /> : <PenLine size={15} />}
              Generate draft
            </Button>
          </form>
        </Card>
      )}

      {editing ? (
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-white">{editing.title}</h2>
              <p className="text-xs text-text-muted">
                {(editing.draft_type || "legal_draft").replace(/_/g, " ")} · v{editing.version || 1} · {formatDateTime(editing.updated_at || editing.created_at)}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge className={
                editing.status === "FINAL"
                  ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-400"
                  : editing.status === "REVIEW"
                  ? "border-amber-500/30 bg-amber-500/15 text-amber-400"
                  : "border-slate-500/30 bg-slate-500/15 text-slate-400"
              }>
                {editing.status || "DRAFT"}
              </Badge>
              <Button size="sm" variant="secondary" onClick={() => downloadDraftFile({ title: editing.title, content }, "pdf")} title="Print / Save as PDF">
                <Printer size={13} className="text-primary" /> PDF
              </Button>
              <Button size="sm" variant="secondary" onClick={() => downloadDraftFile({ title: editing.title, content }, "doc")} title="Download Word Document">
                <Download size={13} className="text-blue-400" /> Word (.doc)
              </Button>
              <Button size="sm" onClick={saveDraft} disabled={saving}>
                {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
                Save
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setEditing(null)}>
                Close
              </Button>
            </div>
          </div>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={20}
            className="mt-4 w-full rounded-xl border border-border bg-bg px-4 py-4 font-mono text-[13px] leading-relaxed text-white outline-none focus:border-primary"
          />
          <p className="mt-3 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-2.5 text-xs text-amber-400/90">
            AI-generated draft. Review and verify before filing or sending.
          </p>
        </Card>
      ) : drafts.length === 0 && !showCreate ? (
        <Card className="flex flex-col items-center p-12 text-center">
          <PenLine size={32} className="mb-3 text-text-muted" />
          <h3 className="text-base font-semibold text-white">No drafts yet</h3>
          <p className="mt-2 max-w-md text-sm text-text-secondary">
            Create a legal notice, petition, affidavit, or application. Facts come from
            your case&rsquo;s verified extraction.
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {drafts.map((draft, idx) => (
            <Card key={draft.id ? `${draft.id}-${idx}` : `draft-${idx}`} className="flex items-center gap-4 p-5">
              <div className="min-w-0 flex-1">
                <h3 className="truncate text-sm font-semibold text-white">{draft.title}</h3>
                <p className="text-xs text-text-muted">
                  {(draft.draft_type || "legal_draft").replace(/_/g, " ")} · v{draft.version || 1} · {formatDateTime(draft.updated_at || draft.created_at)}
                </p>
              </div>
              <Badge className={
                draft.status === "FINAL"
                  ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-400"
                  : draft.status === "REVIEW"
                  ? "border-amber-500/30 bg-amber-500/15 text-amber-400"
                  : "border-slate-500/30 bg-slate-500/15 text-slate-400"
              }>
                {draft.status}
              </Badge>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => { setEditing(draft); setContent(draft.content); }}
              >
                Open
              </Button>
              <button
                onClick={() => removeDraft(draft.id)}
                className="rounded-lg p-2 text-text-muted transition-colors hover:bg-red-500/10 hover:text-red-400"
              >
                <Trash2 size={15} />
              </button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
