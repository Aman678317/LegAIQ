"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  FileText, AlertTriangle, Activity, Loader2, Upload, ArrowRight,
  BrainCircuit, Network, Search, Radio, Trash2,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, Badge, Button } from "@/components/ui";
import { formatDateTime, STATUS_STYLES } from "@/lib/utils";
import { useCaseEvents } from "@/lib/useCaseEvents";

export default function CaseHomePage() {
  const { caseId } = useParams<{ caseId: string }>();
  const router = useRouter();
  const [summary, setSummary] = useState<any>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [activity, setActivity] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Real-time job/document updates (SSE with polling fallback)
  const { documents: liveDocs, status: streamStatus } = useCaseEvents(caseId);

  async function loadSummary() {
    try {
      const s = await api.caseSummary(caseId);
      setSummary(s);
      setDocuments((await api.listDocuments(caseId)).slice(0, 5));
      setActivity((await api.caseActivity(caseId)).slice(0, 8));
    } catch (e: any) {
      setError(e.message || "Failed to load case");
    }
  }

  async function handleDeleteCase() {
    setDeleting(true);
    try {
      await api.deleteCase(caseId);
      router.push("/dashboard");
    } catch {
      setError("Failed to delete case");
      setDeleting(false);
    }
  }

  useEffect(() => {
    loadSummary().finally(() => setLoading(false));
  }, [caseId]);

  // Merge live document statuses into the visible list
  useEffect(() => {
    if (liveDocs.length === 0) return;
    setDocuments((prev) => {
      const map = Object.fromEntries(liveDocs.map((d: any) => [d.id, d]));
      let hasChanges = false;
      const merged = prev.map((doc) => {
        const live = map[doc.id];
        if (live && (live.status !== doc.status || live.ocr_confidence !== doc.ocr_confidence || live.page_count !== doc.page_count)) {
          hasChanges = true;
          return { ...doc, ...live };
        }
        return doc;
      });
      return hasChanges ? merged : prev;
    });
  }, [liveDocs]);

  if (loading) {
    return <div className="flex h-96 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  if (error || !summary) {
    return (
      <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
        {error || "Case not found"}
      </div>
    );
  }

  const { case: caseData, document_count, processing_count, risk_summary } = summary;

  const QUICK_ACTIONS = [
    { href: `/cases/${caseId}/documents`, label: "Upload documents", desc: "Add deeds, records, photos", icon: Upload },
    { href: `/cases/${caseId}/questions`, label: "Ask the AI", desc: "Case-grounded Q&A with citations", icon: BrainCircuit },
    { href: `/cases/${caseId}/ownership`, label: "Ownership chain", desc: "Reconstructed with evidence", icon: Network },
    { href: `/cases/${caseId}/research`, label: "Legal research", desc: "Authoritative Indian sources", icon: Search },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-white">{caseData.name}</h1>
            <Badge className={
              caseData.status === "ACTIVE"
                ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-400"
                : "border-slate-500/30 bg-slate-500/15 text-slate-400"
            }>
              {caseData.status}
            </Badge>
          </div>
          <p className="mt-1 text-sm text-text-secondary">
            {caseData.jurisdiction_state || "Jurisdiction not set"}
            {caseData.jurisdiction_district ? ` · ${caseData.jurisdiction_district}` : ""}
            {` · Created ${formatDateTime(caseData.created_at)}`}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            onClick={() => setShowDeleteModal(true)}
            className="flex items-center gap-1.5 border border-red-500/20 bg-red-500/5 text-xs text-red-400 hover:border-red-500/40 hover:bg-red-500/15 hover:text-red-300"
          >
            <Trash2 size={14} />
            Delete Case
          </Button>
        </div>
      </div>

      <div
        className={`flex w-fit items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${
          streamStatus === "live"
            ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
            : "border-border bg-bg-elevated text-text-muted"
        }`}
        title={streamStatus === "live" ? "Receiving real-time updates" : "Updates on refresh"}
      >
        <Radio size={11} className={streamStatus === "live" ? "animate-pulse" : ""} />
        {streamStatus === "live" ? "Live" : "Synced"}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-xs">
          <Card className="w-full max-w-md border-red-500/30 bg-bg p-6 shadow-2xl">
            <div className="flex items-center gap-3 text-red-400">
              <div className="rounded-full bg-red-500/15 p-2.5">
                <AlertTriangle size={22} />
              </div>
              <div>
                <h3 className="text-base font-semibold text-white">Delete Case Workspace</h3>
                <p className="text-xs text-text-muted">This action cannot be undone.</p>
              </div>
            </div>
            <p className="mt-4 text-sm text-text-secondary">
              Are you sure you want to delete <strong className="text-white">&ldquo;{caseData.name}&rdquo;</strong>? All associated deeds, ownership graphs, and risk audits will be permanently removed.
            </p>
            <div className="mt-6 flex items-center justify-end gap-3">
              <Button
                variant="ghost"
                onClick={() => setShowDeleteModal(false)}
                disabled={deleting}
                className="text-xs text-text-secondary hover:text-white"
              >
                Cancel
              </Button>
              <Button
                onClick={handleDeleteCase}
                disabled={deleting}
                className="border border-red-500/40 bg-red-600 text-xs text-white hover:bg-red-700"
              >
                {deleting ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Trash2 size={14} />
                )}
                Delete Case
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/15 p-2.5"><FileText size={18} className="text-primary" /></div>
            <div>
              <div className="text-2xl font-semibold text-white">{document_count}</div>
              <div className="text-xs text-text-muted">Documents</div>
            </div>
          </div>
        </Card>
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-500/15 p-2.5">
              <Loader2 size={18} className={`text-blue-400 ${processing_count > 0 ? "animate-spin" : ""}`} />
            </div>
            <div>
              <div className="text-2xl font-semibold text-white">{processing_count}</div>
              <div className="text-xs text-text-muted">Processing</div>
            </div>
          </div>
        </Card>
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-red-500/15 p-2.5"><AlertTriangle size={18} className="text-red-400" /></div>
            <div>
              <div className="text-2xl font-semibold text-white">{risk_summary.total}</div>
              <div className="text-xs text-text-muted">Open risks</div>
            </div>
          </div>
        </Card>
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-amber-500/15 p-2.5"><AlertTriangle size={18} className="text-amber-400" /></div>
            <div>
              <div className="text-2xl font-semibold text-white">
                {risk_summary.critical + risk_summary.high}
              </div>
              <div className="text-xs text-text-muted">High + critical</div>
            </div>
          </div>
        </Card>
      </div>

      {/* Quick actions */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {QUICK_ACTIONS.map((action) => {
          const Icon = action.icon;
          return (
            <Link key={action.label} href={action.href}>
              <Card className="group h-full p-5 transition-colors hover:border-primary/40">
                <Icon size={20} className="text-primary" />
                <h3 className="mt-3 text-sm font-semibold text-white group-hover:text-blue-300">{action.label}</h3>
                <p className="mt-1 text-xs text-text-muted">{action.desc}</p>
              </Card>
            </Link>
          );
        })}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent documents */}
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-white">Recent documents</h2>
            <Link href={`/cases/${caseId}/documents`} className="flex items-center gap-1 text-xs text-primary hover:text-blue-300">
              View all <ArrowRight size={12} />
            </Link>
          </div>
          {documents.length === 0 ? (
            <div className="mt-6 rounded-lg border border-dashed border-border-light px-4 py-10 text-center">
              <FileText size={24} className="mx-auto mb-2 text-text-muted" />
              <p className="text-sm text-text-secondary">No documents uploaded yet</p>
              <Button size="sm" variant="secondary" href={`/cases/${caseId}/documents`} className="mt-4">
                <Upload size={14} /> Upload
              </Button>
            </div>
          ) : (
            <div className="mt-4 space-y-2">
              {documents.map((doc) => (
                <div key={doc.id} className="flex items-center justify-between rounded-lg border border-border bg-bg px-4 py-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-white">{doc.file_name}</div>
                    <div className="text-xs text-text-muted">
                      {doc.page_count ? `${doc.page_count} pages` : "Processing…"}
                      {doc.ocr_confidence ? ` · ${(doc.ocr_confidence * 100).toFixed(0)}% confidence` : ""}
                    </div>
                  </div>
                  <span className={`ml-3 shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[doc.status] || ""}`}>
                    {(doc.status || "COMPLETED").replace(/_/g, " ")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Activity feed */}
        <Card className="p-6">
          <h2 className="text-base font-semibold text-white">Recent activity</h2>
          {activity.length === 0 ? (
            <div className="mt-6 rounded-lg border border-dashed border-border-light px-4 py-10 text-center">
              <Activity size={24} className="mx-auto mb-2 text-text-muted" />
              <p className="text-sm text-text-secondary">Activity will appear here as work happens</p>
            </div>
          ) : (
            <div className="mt-4 space-y-3">
              {activity.map((event) => (
                <div key={event.id} className="flex gap-3">
                  <div className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-primary/60" />
                  <div>
                    <p className="text-sm text-white">{event.description}</p>
                    <p className="text-xs text-text-muted">{formatDateTime(event.created_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
