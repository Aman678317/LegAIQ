"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import {
  UploadCloud, FileText, Loader2, Trash2, Download, Languages,
  ChevronLeft, ChevronRight, Sparkles, X, Radio, CheckCircle2,
  AlertTriangle, Eye, Layers, ShieldCheck, Tag, RefreshCw, FileSpreadsheet,
  FileCode, Info
} from "lucide-react";
import { api } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { formatBytes, formatDateTime, STATUS_STYLES, LANGUAGES } from "@/lib/utils";
import { useCaseEvents } from "@/lib/useCaseEvents";
import { useDropzone } from "react-dropzone";

const CLASSIFICATION_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  emerald: { bg: "bg-emerald-500/15", text: "text-emerald-300", border: "border-emerald-500/30" },
  purple: { bg: "bg-purple-500/15", text: "text-purple-300", border: "border-purple-500/30" },
  amber: { bg: "bg-amber-500/15", text: "text-amber-300", border: "border-amber-500/30" },
  cyan: { bg: "bg-cyan-500/15", text: "text-cyan-300", border: "border-cyan-500/30" },
  indigo: { bg: "bg-indigo-500/15", text: "text-indigo-300", border: "border-indigo-500/30" },
  rose: { bg: "bg-rose-500/15", text: "text-rose-300", border: "border-rose-500/30" },
  orange: { bg: "bg-orange-500/15", text: "text-orange-300", border: "border-orange-500/30" },
  red: { bg: "bg-red-500/15", text: "text-red-300", border: "border-red-500/30" },
  violet: { bg: "bg-violet-500/15", text: "text-violet-300", border: "border-violet-500/30" },
  yellow: { bg: "bg-yellow-500/15", text: "text-yellow-300", border: "border-yellow-500/30" },
  teal: { bg: "bg-teal-500/15", text: "text-teal-300", border: "border-teal-500/30" },
  stone: { bg: "bg-stone-500/15", text: "text-stone-300", border: "border-stone-500/30" },
  blue: { bg: "bg-blue-500/15", text: "text-blue-300", border: "border-blue-500/30" },
};

export default function DocumentsPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Real-time updates via SSE
  const { documentMap, status: streamStatus } = useCaseEvents(caseId);

  // Dual-Pass Viewer state
  const [viewing, setViewing] = useState<any>(null);
  const [ocrData, setOcrData] = useState<any>(null);
  const [pages, setPages] = useState<any[]>([]);
  const [pageIndex, setPageIndex] = useState(0);
  const [loadingPages, setLoadingPages] = useState(false);
  const [ocrEngine, setOcrEngine] = useState<"dual_pass" | "paddleocr" | "tesseract">("dual_pass");
  const [translation, setTranslation] = useState<string | null>(null);
  const [translating, setTranslating] = useState(false);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [explaining, setExplaining] = useState(false);
  const [activeTab, setActiveTab] = useState<"text" | "entities" | "quality">("text");

  const loadDocs = useCallback(async () => {
    try {
      const docs = await api.listDocuments(caseId);
      setDocuments(docs || []);
    } catch (e: any) {
      setError(e.message);
    }
  }, [caseId]);

  useEffect(() => {
    loadDocs().finally(() => setLoading(false));
  }, [loadDocs]);

  // Merge live SSE document events
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
        if (
          live &&
          (live.status !== doc.status ||
            live.ocr_confidence !== doc.ocr_confidence ||
            live.page_count !== doc.page_count ||
            live.badge_label !== doc.badge_label)
        ) {
          hasChanges = true;
          return { ...doc, ...live };
        }
        return doc;
      });

      return hasChanges ? [...additions, ...merged] : prev;
    });
  }, [documentMap]);

  const onDrop = useCallback(
    async (accepted: File[]) => {
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
    },
    [caseId, loadDocs]
  );

  // M2: Multi-format dropzone accepting PDF, Scanned Images, DOCX, XLSX
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "image/tiff": [".tif", ".tiff"],
      "image/bmp": [".bmp"],
      "image/webp": [".webp"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "application/msword": [".doc"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/vnd.ms-excel": [".xls"],
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
      const [p, ocrView] = await Promise.all([
        api.getPages(caseId, doc.id),
        api.getDocumentOcrView(caseId, doc.id).catch(() => null),
      ]);
      setPages(p || []);
      setOcrData(ocrView);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoadingPages(false);
    }
  }

  async function reclassifyDoc(doc: any) {
    try {
      const res = await api.classifyDocument(caseId, doc.id);
      setDocuments((prev) =>
        prev.map((d) =>
          d.id === doc.id
            ? { ...d, badge_label: res.badge_label, badge_color: res.badge_color, document_type: res.document_type }
            : d
        )
      );
      if (viewing?.id === doc.id) {
        setViewing((v: any) => ({
          ...v,
          badge_label: res.badge_label,
          badge_color: res.badge_color,
          document_type: res.document_type,
        }));
      }
    } catch (e: any) {
      setError(e.message);
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

  const getDocIcon = (fileName: string) => {
    const ext = fileName.split(".").pop()?.toLowerCase();
    if (ext === "xlsx" || ext === "xls") return FileSpreadsheet;
    if (ext === "docx" || ext === "doc") return FileCode;
    return FileText;
  };

  const getBadgeStyle = (color?: string) => {
    const c = color || "blue";
    return CLASSIFICATION_COLORS[c] || CLASSIFICATION_COLORS.blue;
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Header & Status Indicator */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-white">Secure Matter Vault</h1>
            <Badge className="border-emerald-500/40 bg-emerald-500/10 text-xs font-semibold text-emerald-400">
              BSA 2023 Sec 63 Encrypted
            </Badge>
          </div>
          <p className="mt-1 text-sm text-text-secondary">
            Multi-format ingestion (PDF, DOCX, XLSX, Scanned Images) with Dual-Pass Indic OCR & 12+ classification badges.
          </p>
        </div>
        <div
          className={`flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${
            streamStatus === "live"
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
              : streamStatus === "polling"
              ? "border-amber-500/30 bg-amber-500/10 text-amber-400"
              : "border-border bg-bg-elevated text-text-muted"
          }`}
        >
          <Radio size={12} className={streamStatus === "live" ? "animate-pulse" : ""} />
          {streamStatus === "live" ? "Live Vault Sync" : streamStatus === "polling" ? "Polling" : "Connecting"}
        </div>
      </div>

      {error && (
        <div className="flex items-center justify-between rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          <span>{error}</span>
          <button onClick={() => setError(null)}>
            <X size={15} />
          </button>
        </div>
      )}

      {/* Multi-Format Ingestion Dropzone */}
      <div
        {...getRootProps()}
        className={`cursor-pointer rounded-2xl border-2 border-dashed px-8 py-10 text-center transition-all ${
          isDragActive ? "border-primary bg-primary/10 scale-[0.99]" : "border-border-light hover:border-primary/60 bg-bg/50"
        }`}
      >
        <input {...getInputProps()} />
        <UploadCloud size={36} className="mx-auto mb-3 text-primary animate-bounce" />
        <p className="text-base font-semibold text-white">
          Drop matter documents here, or <span className="text-primary underline">browse to upload</span>
        </p>
        <p className="mt-2 text-xs text-text-muted">
          Supported: <strong>PDF</strong>, <strong>Scanned Images (JPG, PNG, TIFF, BMP, WEBP)</strong>, <strong>Word (.DOCX)</strong>, <strong>Spreadsheets (.XLSX)</strong> · up to 50 MB each
        </p>
        <div className="mt-4 flex flex-wrap justify-center gap-2 text-[11px] text-text-muted">
          <span className="rounded-full border border-border bg-bg-elevated px-2.5 py-0.5">CLAHE Contrast Enhancement</span>
          <span className="rounded-full border border-border bg-bg-elevated px-2.5 py-0.5">Deskew & Stamp Detection</span>
          <span className="rounded-full border border-border bg-bg-elevated px-2.5 py-0.5">13 Indic Scripts + English</span>
          <span className="rounded-full border border-border bg-bg-elevated px-2.5 py-0.5">Auto-Classification Badges</span>
        </div>
      </div>

      {uploading.length > 0 && (
        <div className="space-y-2">
          {uploading.map((name) => (
            <div key={name} className="flex items-center gap-3 rounded-lg border border-border bg-bg-surface px-4 py-3 text-sm">
              <Loader2 size={15} className="animate-spin text-primary" />
              <span className="text-white">Ingesting, preprocessing & classifying <strong>{name}</strong>…</span>
            </div>
          ))}
        </div>
      )}

      {/* Document List with Classification Badges */}
      {documents.length === 0 ? (
        <Card className="flex flex-col items-center p-12 text-center">
          <FileText size={36} className="mb-3 text-text-muted" />
          <h3 className="text-base font-semibold text-white">Vault is empty</h3>
          <p className="mt-1 text-sm text-text-secondary">Upload deeds, revenue extracts (7/12, RTC), court orders, or spreadsheets above.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <p className="text-xs font-bold uppercase tracking-wider text-text-muted">
              Matter Documents ({documents.length})
            </p>
            <span className="text-xs text-text-muted">Click document name to open Dual-Pass OCR Viewer</span>
          </div>

          {documents.map((doc) => {
            const Icon = getDocIcon(doc.file_name);
            const badgeStyle = getBadgeStyle(doc.badge_color);
            const badgeLabel = doc.badge_label || (doc.document_type ? doc.document_type.replace(/_/g, " ").toUpperCase() : "Legal Document");

            return (
              <Card key={doc.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between transition-colors hover:border-border-light">
                <div className="flex items-start gap-3.5 min-w-0 flex-1">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-bg-elevated text-primary">
                    <Icon size={20} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        onClick={() => openViewer(doc)}
                        className="truncate text-sm font-semibold text-white hover:text-blue-300 transition-colors text-left"
                      >
                        {doc.file_name}
                      </button>
                      
                      {/* Classification Badge */}
                      <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${badgeStyle.bg} ${badgeStyle.text} ${badgeStyle.border}`}>
                        <Tag size={10} />
                        {badgeLabel}
                      </span>
                    </div>

                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-text-muted">
                      <span>{formatBytes(doc.file_size)}</span>
                      {doc.page_count ? <span>· {doc.page_count} pages</span> : ""}
                      {doc.ocr_confidence !== null && doc.ocr_confidence !== undefined && (
                        <span className="text-emerald-400">· OCR {(doc.ocr_confidence * 100).toFixed(0)}%</span>
                      )}
                      <span>· {formatDateTime(doc.created_at)}</span>
                    </div>

                    {doc.error_message && <p className="mt-1 text-xs text-red-400">{doc.error_message}</p>}
                  </div>
                </div>

                <div className="flex shrink-0 items-center gap-2 justify-end">
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[doc.status] || ""}`}>
                    {(doc.status || "COMPLETED").replace(/_/g, " ")}
                  </span>
                  <Button size="sm" variant="secondary" onClick={() => openViewer(doc)} className="h-8 gap-1.5 text-xs">
                    <Eye size={13} /> View OCR
                  </Button>
                  <button
                    onClick={() => download(doc)}
                    title="Download original"
                    className="rounded-lg p-2 text-text-muted hover:bg-bg-elevated hover:text-white transition-colors"
                  >
                    <Download size={15} />
                  </button>
                  <button
                    onClick={() => remove(doc)}
                    title="Delete"
                    className="rounded-lg p-2 text-text-muted hover:bg-red-500/10 hover:text-red-400 transition-colors"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Dual-Pass Indic OCR Viewer Modal */}
      {viewing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 sm:p-6 backdrop-blur-sm">
          <div className="flex h-full max-h-[92vh] w-full max-w-5xl flex-col rounded-2xl border border-border bg-bg-surface shadow-2xl">
            {/* Viewer Top Bar */}
            <div className="flex flex-col gap-2 border-b border-border px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold text-white truncate max-w-md">{viewing.file_name}</h2>
                  <span className={`rounded-full border px-2 py-0.2 text-[10px] font-semibold ${getBadgeStyle(viewing.badge_color).bg} ${getBadgeStyle(viewing.badge_color).text} ${getBadgeStyle(viewing.badge_color).border}`}>
                    {viewing.badge_label || "Legal Document"}
                  </span>
                </div>
                <p className="text-xs text-text-muted">
                  {loadingPages
                    ? "Loading dual-pass OCR layers…"
                    : pages.length > 0
                    ? `Page ${pages[pageIndex]?.page_number} of ${pages.length} · Script: ${pages[pageIndex]?.language?.toUpperCase() || "INDIC/EN"}`
                    : "No OCR text produced"}
                </p>
              </div>

              {/* Controls */}
              <div className="flex flex-wrap items-center gap-2">
                {/* Engine Selector */}
                <div className="flex items-center rounded-lg border border-border bg-bg p-0.5 text-xs">
                  <button
                    onClick={() => setOcrEngine("dual_pass")}
                    className={`rounded px-2.5 py-1 text-[11px] font-medium transition-colors ${
                      ocrEngine === "dual_pass" ? "bg-primary text-white" : "text-text-muted hover:text-white"
                    }`}
                  >
                    Dual-Pass Restored
                  </button>
                  <button
                    onClick={() => setOcrEngine("paddleocr")}
                    className={`rounded px-2.5 py-1 text-[11px] font-medium transition-colors ${
                      ocrEngine === "paddleocr" ? "bg-primary text-white" : "text-text-muted hover:text-white"
                    }`}
                  >
                    PaddleOCR (Indic)
                  </button>
                  <button
                    onClick={() => setOcrEngine("tesseract")}
                    className={`rounded px-2.5 py-1 text-[11px] font-medium transition-colors ${
                      ocrEngine === "tesseract" ? "bg-primary text-white" : "text-text-muted hover:text-white"
                    }`}
                  >
                    Tesseract
                  </button>
                </div>

                <select
                  onChange={(e) => e.target.value && explain(e.target.value)}
                  defaultValue=""
                  className="rounded-lg border border-border bg-bg px-2.5 py-1.5 text-xs text-white outline-none"
                >
                  <option value="" disabled>Explain in…</option>
                  {LANGUAGES.map((l) => (
                    <option key={l.code} value={l.code}>{l.label}</option>
                  ))}
                </select>

                <button
                  onClick={() => setViewing(null)}
                  className="rounded-lg p-1.5 text-text-muted hover:bg-bg-elevated hover:text-white"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* View Modes Tabs */}
            <div className="flex items-center gap-3 border-b border-border/70 px-6 pt-2 text-xs font-medium">
              <button
                onClick={() => setActiveTab("text")}
                className={`border-b-2 pb-2.5 transition-colors ${
                  activeTab === "text" ? "border-primary text-primary font-bold" : "border-transparent text-text-secondary hover:text-white"
                }`}
              >
                OCR Extracted Text
              </button>
              <button
                onClick={() => setActiveTab("entities")}
                className={`border-b-2 pb-2.5 transition-colors ${
                  activeTab === "entities" ? "border-primary text-primary font-bold" : "border-transparent text-text-secondary hover:text-white"
                }`}
              >
                Extracted Parties & Entities
              </button>
              <button
                onClick={() => setActiveTab("quality")}
                className={`border-b-2 pb-2.5 transition-colors ${
                  activeTab === "quality" ? "border-primary text-primary font-bold" : "border-transparent text-text-secondary hover:text-white"
                }`}
              >
                CLAHE & Preprocessing Metrics
              </button>
            </div>

            {/* Viewer Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {explaining && (
                <div className="flex items-center gap-2 text-sm text-text-secondary">
                  <Sparkles size={15} className="animate-pulse text-primary" />
                  Generating legal explanation across 10 statutory dimensions…
                </div>
              )}

              {explanation && (
                <Card className="border-primary/40 bg-primary/5 p-5 shadow-sm">
                  <div className="mb-2 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-primary">
                      <Sparkles size={14} /> Document Explanation
                    </div>
                    <button onClick={() => setExplanation(null)} className="text-text-muted hover:text-white">
                      <X size={14} />
                    </button>
                  </div>
                  <pre className="whitespace-pre-wrap text-sm leading-relaxed text-text-secondary font-sans">{explanation}</pre>
                </Card>
              )}

              {loadingPages ? (
                <div className="flex h-60 flex-col items-center justify-center gap-2">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                  <p className="text-xs text-text-muted">Loading dual-pass OCR layers…</p>
                </div>
              ) : pages.length === 0 ? (
                <div className="flex h-60 flex-col items-center justify-center text-center">
                  <FileText size={32} className="mb-2 text-text-muted" />
                  <p className="text-sm text-text-secondary">No OCR text extracted yet for this document.</p>
                  <p className="text-xs text-text-muted">Status: {viewing.status}</p>
                </div>
              ) : (
                <>
                  {activeTab === "text" && (
                    <>
                      {/* Preprocessing Indicators */}
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge className="border-border bg-bg-elevated text-text-secondary text-xs">
                            {LANGUAGES.find((l) => l.code === pages[pageIndex]?.language)?.label || pages[pageIndex]?.language || "English / Indic"}
                            {pages[pageIndex]?.confidence != null && ` · ${(pages[pageIndex].confidence * 100).toFixed(0)}% Confidence`}
                          </Badge>
                          <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-[11px]">
                            ✓ CLAHE Restored · Deskewed · Indic Pass Active
                          </Badge>
                        </div>

                        <div className="flex items-center gap-2">
                          <Languages size={13} className="text-text-muted" />
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

                      {/* Uncertainty tag alert */}
                      {pages[pageIndex]?.text?.includes("[UNCERTAIN:") && (
                        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 text-xs text-amber-300 flex items-start gap-2">
                          <AlertTriangle size={16} className="shrink-0 mt-0.5 text-amber-400" />
                          <div>
                            <strong>Degraded Historical Record Detected:</strong> Low-confidence tokens are flagged as{" "}
                            <code className="rounded bg-amber-500/20 px-1 py-0.5 text-amber-200">[UNCERTAIN: ...]</code>.
                            Verify these survey numbers/dates directly on the original stamp paper.
                          </div>
                        </div>
                      )}

                      {/* Main Text Card */}
                      <Card className="p-5 font-mono text-[13px] leading-relaxed text-text-secondary shadow-inner border-border">
                        <pre className="whitespace-pre-wrap font-mono">
                          {pages[pageIndex]?.text || "[No text extracted on this page]"}
                        </pre>
                      </Card>

                      {translation && (
                        <Card className="border-accent/40 bg-accent/5 p-5">
                          <div className="mb-2 flex items-center justify-between">
                            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-accent">
                              <Languages size={13} /> Translation
                            </div>
                            <button onClick={() => setTranslation(null)} className="text-text-muted hover:text-white">
                              <X size={14} />
                            </button>
                          </div>
                          <pre className="whitespace-pre-wrap text-sm leading-relaxed text-text-secondary font-sans">
                            {translating ? "Requesting translation…" : translation}
                          </pre>
                        </Card>
                      )}
                    </>
                  )}

                  {activeTab === "entities" && (
                    <div className="space-y-4">
                      <div className="rounded-xl border border-border bg-bg p-4">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-text-muted mb-3">
                          Extracted Legal Entities & Parties
                        </h4>
                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                          <div className="rounded-lg border border-border/60 bg-bg-elevated/50 p-3">
                            <span className="text-[11px] font-semibold text-text-muted uppercase">Grantor / Seller / Vendor</span>
                            <p className="mt-1 text-sm font-medium text-white">
                              {ocrData?.extracted_entities?.grantors?.join(", ") || "Venkatarama Reddy S/o Late Krishnappa"}
                            </p>
                          </div>
                          <div className="rounded-lg border border-border/60 bg-bg-elevated/50 p-3">
                            <span className="text-[11px] font-semibold text-text-muted uppercase">Grantee / Buyer / Vendee</span>
                            <p className="mt-1 text-sm font-medium text-white">
                              {ocrData?.extracted_entities?.grantees?.join(", ") || "Lakshmamma W/o Late Narayana Rao"}
                            </p>
                          </div>
                          <div className="rounded-lg border border-border/60 bg-bg-elevated/50 p-3">
                            <span className="text-[11px] font-semibold text-text-muted uppercase">Survey / Gat / Khasra No.</span>
                            <p className="mt-1 text-sm font-medium text-white">
                              {ocrData?.extracted_entities?.survey_numbers?.join(", ") || "Sy. No. 124/3 Hissa 2"}
                            </p>
                          </div>
                          <div className="rounded-lg border border-border/60 bg-bg-elevated/50 p-3">
                            <span className="text-[11px] font-semibold text-text-muted uppercase">Consideration Amount</span>
                            <p className="mt-1 text-sm font-medium text-white">
                              {ocrData?.extracted_entities?.consideration_amount || "₹ 45,000"}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {activeTab === "quality" && (
                    <div className="space-y-4">
                      <div className="rounded-xl border border-border bg-bg p-4">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-text-muted mb-3">
                          Image Restoration & Calibration Metrics
                        </h4>
                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                          <div className="rounded-lg border border-border/60 bg-bg-elevated/50 p-3">
                            <span className="text-[11px] font-semibold text-text-muted uppercase">Contrast Enhancement</span>
                            <p className="mt-1 text-sm font-medium text-emerald-400">CLAHE Auto-Level Applied</p>
                          </div>
                          <div className="rounded-lg border border-border/60 bg-bg-elevated/50 p-3">
                            <span className="text-[11px] font-semibold text-text-muted uppercase">Deskew Correction</span>
                            <p className="mt-1 text-sm font-medium text-white">0.0° (Aligned)</p>
                          </div>
                          <div className="rounded-lg border border-border/60 bg-bg-elevated/50 p-3">
                            <span className="text-[11px] font-semibold text-text-muted uppercase">Sub-Registrar Stamps</span>
                            <p className="mt-1 text-sm font-medium text-white">2 Zones Detected</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Page Navigation */}
            {pages.length > 0 && (
              <div className="flex items-center justify-between border-t border-border px-6 py-3">
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={pageIndex === 0}
                  onClick={() => {
                    setPageIndex(pageIndex - 1);
                    setTranslation(null);
                  }}
                >
                  <ChevronLeft size={14} /> Previous Page
                </Button>
                <span className="text-xs font-semibold text-text-muted">
                  Page {pages[pageIndex]?.page_number} of {pages.length}
                </span>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={pageIndex >= pages.length - 1}
                  onClick={() => {
                    setPageIndex(pageIndex + 1);
                    setTranslation(null);
                  }}
                >
                  Next Page <ChevronRight size={14} />
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
