"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import {
  UploadCloud, FileText, Loader2, Trash2, Download, Languages,
  ChevronLeft, ChevronRight, Sparkles, X, Radio,
} from "lucide-react";
import { api } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { formatBytes, formatDateTime, STATUS_STYLES, LANGUAGES } from "@/lib/utils";
import { useCaseEvents } from "@/lib/useCaseEvents";
import { useDropzone } from "react-dropzone";

export default function DocumentsPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Real-time updates via SSE (falls back to polling automatically)
  const { documentMap, status: streamStatus } = useCaseEvents(caseId);

  // Viewer state
  const [viewing, setViewing] = useState<any>(null);
  const [pages, setPages] = useState<any[]>([]);
  const [pageIndex, setPageIndex] = useState(0);
  const [loadingPages, setLoadingPages] = useState(false);
  const [translation, setTranslation] = useState<string | null>(null);
  const [translating, setTranslating] = useState(false);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [explaining, setExplaining] = useState(false);

  const loadDocs = useCallback(async () => {
    try {
      const docs = await api.listDocuments(caseId);
      setDocuments(docs);
    } catch (e: any) {
      setError(e.message);
    }
  }, [caseId]);

  useEffect(() => {
    loadDocs().finally(() => setLoading(false));
  }, [loadDocs]);

  // Merge live SSE document events into the list
  useEffect(() => {
    if (Object.keys(documentMap).length === 0) return;
    setDocuments((prev) => {
      const knownIds = new Set(prev.map((d) => d.id));
      const additions = Object.values(documentMap)
        .filter((d: any) => !knownIds.has(d.id))
        .map((d: any) => d);

      let hasChanges = additions.length > 0;
      const merged = prev.map((doc) => {
        const live = documentMap[doc.id];
        if (live && (live.status !== doc.status || live.ocr_confidence !== doc.ocr_confidence || live.page_count !== doc.page_count)) {
          hasChanges = true;
          return { ...doc, ...live };
        }
        return doc;
      });

      return hasChanges ? [...additions, ...merged] : prev;
    });
  }, [documentMap]);

  const onDrop = useCallback(async (accepted: File[]) => {
    setError(null);
    setUploading(accepted.map((f) => f.name));
    for (const file of accepted) {
      try {
        await api.uploadDocument(caseId, file);
      } catch (e: any) {
        setError(`${file.name}: ${e.message}`);
      }
    }
    setUploading([]);
    await loadDocs();
  }, [caseId, loadDocs]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "image/tiff": [".tif", ".tiff"],
    },
    maxSize: 50 * 1024 * 1024,
  });

  async function openViewer(doc: any) {
    setViewing(doc);
    setPageIndex(0);
    setTranslation(null);
    setExplanation(null);
    setLoadingPages(true);
    try {
      const p = await api.getPages(caseId, doc.id);
      setPages(p);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoadingPages(false);
    }
  }

  async function requestTranslation(lang: string) {
    if (!viewing) return;
    setTranslating(true);
    try {
      const result = await api.requestTranslation(caseId, viewing.id, pages[pageIndex]?.page_number || 1, lang);
      setTranslation(
        result.status === "QUEUED"
          ? "Translation queued — refresh in a moment."
          : result.text || "No translation available."
      );
    } catch (e: any) {
      setError(e.message);
    } finally {
      setTranslating(false);
    }
  }

  async function explain(lang: string) {
    if (!viewing) return;
    setExplaining(true);
    setExplanation(null);
    try {
      const result = await api.explainDocument(viewing.id, lang);
      setExplanation(result.explanation);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setExplaining(false);
    }
  }

  async function download(doc: any) {
    try {
      const { url } = await api.getDownloadUrl(caseId, doc.id);
      window.open(url, "_blank");
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function remove(doc: any) {
    if (!confirm(`Delete "${doc.file_name}"? This cannot be undone.`)) return;
    try {
      await api.deleteDocument(caseId, doc.id);
      await loadDocs();
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
          <h1 className="text-2xl font-semibold text-white">Documents</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Upload property deeds, records, and photos. Originals are stored privately and never modified.
          </p>
        </div>
        <div
          className={`flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${
            streamStatus === "live"
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
              : streamStatus === "polling"
              ? "border-amber-500/30 bg-amber-500/10 text-amber-400"
              : "border-border bg-bg-elevated text-text-muted"
          }`}
          title={
            streamStatus === "live"
              ? "Receiving real-time updates"
              : "Real-time stream unavailable — checking every 5s"
          }
        >
          <Radio size={11} className={streamStatus === "live" ? "animate-pulse" : ""} />
          {streamStatus === "live" ? "Live" : streamStatus === "polling" ? "Polling" : "Connecting"}
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {/* Upload zone */}
      <div
        {...getRootProps()}
        className={`cursor-pointer rounded-2xl border-2 border-dashed px-8 py-12 text-center transition-colors ${
          isDragActive ? "border-primary bg-primary/5" : "border-border-light hover:border-primary/50"
        }`}
      >
        <input {...getInputProps()} />
        <UploadCloud size={32} className="mx-auto mb-3 text-text-muted" />
        <p className="text-sm font-medium text-white">
          Drop documents here, or click to browse
        </p>
        <p className="mt-1.5 text-xs text-text-muted">
          PDF, JPG, PNG, TIFF · up to 50 MB each · scanned and photographed pages welcome
        </p>
      </div>

      {uploading.length > 0 && (
        <div className="space-y-2">
          {uploading.map((name) => (
            <div key={name} className="flex items-center gap-3 rounded-lg border border-border bg-bg-surface px-4 py-3 text-sm">
              <Loader2 size={14} className="animate-spin text-primary" />
              <span className="text-white">Uploading {name}…</span>
            </div>
          ))}
        </div>
      )}

      {/* Document list */}
      {documents.length === 0 ? (
        <Card className="flex flex-col items-center p-12 text-center">
          <FileText size={32} className="mb-3 text-text-muted" />
          <p className="text-sm text-text-secondary">No documents yet. Upload your first deed above.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {documents.map((doc) => (
            <Card key={doc.id} className="flex items-center gap-4 p-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-bg-elevated">
                <FileText size={18} className="text-primary" />
              </div>
              <div className="min-w-0 flex-1">
                <button onClick={() => openViewer(doc)} className="block w-full truncate text-left text-sm font-medium text-white hover:text-blue-300">
                  {doc.file_name}
                </button>
                <p className="text-xs text-text-muted">
                  {formatBytes(doc.file_size)}
                  {doc.page_count ? ` · ${doc.page_count} pages` : ""}
                  {doc.ocr_confidence !== null ? ` · OCR ${(doc.ocr_confidence * 100).toFixed(0)}%` : ""}
                  {` · ${formatDateTime(doc.created_at)}`}
                </p>
                {doc.error_message && (
                  <p className="mt-1 text-xs text-red-400">{doc.error_message}</p>
                )}
              </div>
              <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[doc.status] || ""}`}>
                {(doc.status || "COMPLETED").replace(/_/g, " ")}
              </span>
              <div className="flex shrink-0 items-center gap-1">
                <button onClick={() => download(doc)} title="Download" className="rounded-lg p-2 text-text-muted transition-colors hover:bg-bg-elevated hover:text-white">
                  <Download size={15} />
                </button>
                <button onClick={() => remove(doc)} title="Delete" className="rounded-lg p-2 text-text-muted transition-colors hover:bg-red-500/10 hover:text-red-400">
                  <Trash2 size={15} />
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Document viewer modal */}
      {viewing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6 backdrop-blur-sm">
          <div className="flex h-full max-h-[90vh] w-full max-w-5xl flex-col rounded-2xl border border-border bg-bg-surface">
            <div className="flex items-center justify-between border-b border-border px-6 py-4">
              <div>
                <h2 className="text-base font-semibold text-white">{viewing.file_name}</h2>
                <p className="text-xs text-text-muted">
                  {loadingPages ? "Loading pages…" : pages.length > 0 ? `Page ${pages[pageIndex]?.page_number} of ${pages.length}` : "No OCR text yet"}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <select
                  onChange={(e) => e.target.value && explain(e.target.value)}
                  defaultValue=""
                  className="rounded-lg border border-border bg-bg px-3 py-1.5 text-xs text-white outline-none"
                >
                  <option value="" disabled>Explain in…</option>
                  {LANGUAGES.map((l) => (
                    <option key={l.code} value={l.code}>{l.label}</option>
                  ))}
                </select>
                <button onClick={() => setViewing(null)} className="rounded-lg p-2 text-text-muted hover:bg-bg-elevated hover:text-white">
                  <X size={18} />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              {explaining && (
                <div className="mb-4 flex items-center gap-2 text-sm text-text-secondary">
                  <Sparkles size={14} className="animate-pulse text-primary" />
                  Explaining document…
                </div>
              )}
              {explanation && (
                <Card className="mb-6 border-primary/30 p-5">
                  <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-primary">
                    <Sparkles size={13} /> Document Explanation
                  </div>
                  <pre className="whitespace-pre-wrap text-sm leading-relaxed text-text-secondary">{explanation}</pre>
                </Card>
              )}

              {loadingPages ? (
                <div className="flex h-40 items-center justify-center">
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                </div>
              ) : pages.length === 0 ? (
                <div className="flex h-40 flex-col items-center justify-center text-center">
                  <FileText size={28} className="mb-2 text-text-muted" />
                  <p className="text-sm text-text-secondary">OCR has not produced text for this document yet.</p>
                  <p className="text-xs text-text-muted">Status: {viewing.status}</p>
                </div>
              ) : (
                <>
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Badge className="border-border bg-bg-elevated text-text-secondary">
                        {LANGUAGES.find((l) => l.code === pages[pageIndex]?.language)?.label || pages[pageIndex]?.language || "Unknown language"}
                        {pages[pageIndex]?.confidence != null && ` · ${(pages[pageIndex].confidence * 100).toFixed(0)}% confidence`}
                      </Badge>
                      <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-[11px]">
                        ✓ Historical OCR Preprocessed (Deskewed · CLAHE Contrast Restored)
                      </Badge>
                    </div>
                    <div className="flex items-center gap-1">
                      <Languages size={14} className="mr-1 text-text-muted" />
                      <select
                        onChange={(e) => e.target.value && requestTranslation(e.target.value)}
                        defaultValue=""
                        className="rounded-lg border border-border bg-bg px-2.5 py-1 text-xs text-white outline-none"
                      >
                        <option value="" disabled>Translate page…</option>
                        {LANGUAGES.map((l) => (
                          <option key={l.code} value={l.code}>{l.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {pages[pageIndex]?.text?.includes("[UNCERTAIN:") && (
                    <div className="mb-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3.5 py-2 text-xs text-amber-400">
                      ⚠️ <strong>Damaged / Faded Text Detected:</strong> Certain tokens have low OCR confidence and are explicitly tagged with <code>[UNCERTAIN: ...]</code>. Verify these critical details directly on the original stamp paper.
                    </div>
                  )}

                  <Card className="p-5">
                    <pre className="whitespace-pre-wrap font-mono text-[13px] leading-relaxed text-text-secondary">
                      {pages[pageIndex]?.text || "[No text extracted on this page]"}
                    </pre>
                  </Card>

                  {translation && (
                    <Card className="mt-4 border-accent/30 p-5">
                      <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-accent">
                        <Languages size={13} /> Translation
                      </div>
                      <pre className="whitespace-pre-wrap text-sm leading-relaxed text-text-secondary">
                        {translating ? "Requesting translation…" : translation}
                      </pre>
                    </Card>
                  )}
                </>
              )}
            </div>

            {pages.length > 0 && (
              <div className="flex items-center justify-between border-t border-border px-6 py-3">
                <Button size="sm" variant="secondary" disabled={pageIndex === 0} onClick={() => { setPageIndex(pageIndex - 1); setTranslation(null); }}>
                  <ChevronLeft size={14} /> Previous
                </Button>
                <span className="text-xs text-text-muted">
                  Page {pages[pageIndex]?.page_number}
                </span>
                <Button size="sm" variant="secondary" disabled={pageIndex >= pages.length - 1} onClick={() => { setPageIndex(pageIndex + 1); setTranslation(null); }}>
                  Next <ChevronRight size={14} />
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
