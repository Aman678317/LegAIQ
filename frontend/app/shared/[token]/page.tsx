"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  Lock,
  ShieldCheck,
  Clock,
  FileText,
  Eye,
  AlertCircle,
  Loader2,
  Download,
  KeyRound,
} from "lucide-react";
import { Button, Card } from "@/components/ui";
import { api } from "@/lib/api";
import { WatermarkOverlay } from "@/components/document-viewer/WatermarkOverlay";

export default function PublicSharedSpacePage() {
  const { token } = useParams<{ token: string }>();
  const [meta, setMeta] = useState<any | null>(null);
  const [passcode, setPasscode] = useState("");
  const [authenticatedData, setAuthenticatedData] = useState<any | null>(null);
  const [activeDoc, setActiveDoc] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    api
      .getPublicSharedSpace(token)
      .then((res) => {
        setMeta(res);
        if (!res.has_passcode) {
          // Auto-verify if no passcode needed
          handleVerify("");
        } else {
          setLoading(false);
        }
      })
      .catch((err) => {
        setError(err.message || "Failed to load shared space. Link may have expired or been revoked.");
        setLoading(false);
      });
  }, [token]);

  const handleVerify = async (codeToVerify?: string) => {
    const code = typeof codeToVerify === "string" ? codeToVerify : passcode;
    setVerifying(true);
    setError(null);
    try {
      const res = await api.verifySharedSpacePasscode(token, code);
      setAuthenticatedData(res);
      if (res.documents?.length > 0) {
        setActiveDoc(res.documents[0]);
      }
    } catch (err: any) {
      setError(err.message || "Invalid passcode. Please check and retry.");
    } finally {
      setVerifying(false);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0a0d14] text-white">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="text-xs text-text-muted">Opening Secure Shared Space...</span>
        </div>
      </div>
    );
  }

  if (error && !meta) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0a0d14] p-4 text-white">
        <Card className="max-w-md p-8 text-center border-red-500/30 bg-red-500/10">
          <AlertCircle className="mx-auto h-12 w-12 text-red-400 mb-3" />
          <h2 className="text-lg font-bold">Access Expired or Revoked</h2>
          <p className="mt-2 text-xs text-text-secondary">{error}</p>
        </Card>
      </div>
    );
  }

  // Passcode Challenge Screen
  if (!authenticatedData) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0a0d14] p-4 text-white">
        <Card className="w-full max-w-md p-8 border-border bg-[#111622] shadow-2xl">
          <div className="flex items-center gap-3 border-b border-border pb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/20 text-primary">
              <Lock size={20} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">{meta?.name || "Matter Shared Space"}</h2>
              <p className="text-xs text-text-muted">Protected Legal Collaboration Portal</p>
            </div>
          </div>

          <div className="mt-6 space-y-4">
            <p className="text-xs text-text-secondary leading-relaxed">
              This shared space for <strong>{meta?.recipient_email}</strong> is passcode protected. Please enter
              the access passcode provided by your counsel.
            </p>

            {error && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-400">
                {error}
              </div>
            )}

            <div>
              <label className="text-xs font-medium text-text-secondary">Enter Passcode</label>
              <div className="relative mt-1">
                <KeyRound className="absolute left-3 top-2.5 h-4 w-4 text-text-muted" />
                <input
                  type="password"
                  placeholder="••••••••"
                  value={passcode}
                  onChange={(e) => setPasscode(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleVerify()}
                  className="w-full rounded-lg border border-border bg-bg pl-9 pr-3 py-2 text-xs text-white focus:border-primary focus:outline-none"
                />
              </div>
            </div>

            <Button
              className="w-full mt-2"
              onClick={() => handleVerify()}
              disabled={verifying || !passcode}
            >
              {verifying ? <Loader2 size={14} className="animate-spin" /> : "Unlock Shared Space"}
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  // Authenticated Document Viewer Portal
  const docs = authenticatedData.documents || [];

  return (
    <div className="flex min-h-screen flex-col bg-[#0b0e17] text-white">
      {/* Top Banner */}
      <header className="flex items-center justify-between border-b border-border bg-[#111622] px-8 py-3.5">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/20 text-primary font-bold">
            LQ
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-semibold text-white">{meta?.name || "Matter Shared Space"}</h1>
              <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                SECURE CLIENT PORTAL
              </span>
            </div>
            <p className="text-[11px] text-text-muted">
              Access Role: <strong>{authenticatedData.role}</strong> · Logged in as:{" "}
              <strong>{authenticatedData.recipient_email}</strong>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs text-text-secondary">
          <div className="flex items-center gap-1.5 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-amber-300">
            <Clock size={14} />
            <span>Expires: {new Date(authenticatedData.expires_at).toLocaleString()}</span>
          </div>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Document List */}
        <div className="w-80 border-r border-border bg-[#0e121c] p-4 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-text-muted">
              <FileText size={14} className="text-primary" />
              <span>Available Documents ({docs.length})</span>
            </div>

            <div className="space-y-1.5">
              {docs.map((doc: any) => (
                <button
                  key={doc.id}
                  onClick={() => setActiveDoc(doc)}
                  className={`w-full rounded-xl p-3 text-left transition-all ${
                    activeDoc?.id === doc.id
                      ? "border border-primary/50 bg-primary/15 text-white"
                      : "border border-transparent bg-surface/50 text-text-secondary hover:bg-surface hover:text-white"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <FileText size={16} className="text-primary shrink-0" />
                    <span className="truncate text-xs font-medium">{doc.file_name}</span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-[10px] text-text-muted">
                    <span>{doc.file_type?.toUpperCase() || "PDF"}</span>
                    <span>{doc.page_count || 1} Page(s)</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-border/80 bg-surface/40 p-3 text-[11px] text-text-muted space-y-1">
            <div className="flex items-center gap-1.5 text-text-secondary font-medium">
              <ShieldCheck size={14} className="text-emerald-400" />
              <span>Dynamic Watermark Active</span>
            </div>
            <p className="text-[10px]">
              Every page viewed or exported is stamped with your identity for audit compliance.
            </p>
          </div>
        </div>

        {/* Right: Document Viewer with Dynamic Watermark */}
        <div className="relative flex flex-1 flex-col overflow-hidden bg-[#07090e]">
          {activeDoc ? (
            <div className="relative flex flex-1 flex-col overflow-y-auto p-8">
              {/* Watermark Overlay Component */}
              <WatermarkOverlay
                viewerEmail={authenticatedData.recipient_email}
                viewerIp="127.0.0.1"
                enabled={true}
              />

              {/* Document Content View */}
              <div className="relative z-10 mx-auto w-full max-w-3xl rounded-2xl border border-border bg-[#10141e] p-8 shadow-2xl">
                <div className="flex items-center justify-between border-b border-border pb-4 mb-6">
                  <div>
                    <h3 className="font-semibold text-white text-base">{activeDoc.file_name}</h3>
                    <p className="text-xs text-text-muted">Page 1 of {activeDoc.page_count || 1}</p>
                  </div>
                </div>

                <div className="font-mono text-xs leading-relaxed text-slate-300 whitespace-pre-wrap">
                  {activeDoc.content || "Document content available for review."}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-1 items-center justify-center text-xs text-text-muted">
              Select a document to preview
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
