"use client";

import { useState } from "react";
import {
  X,
  Share2,
  Clock,
  Lock,
  Eye,
  Copy,
  Check,
  ShieldCheck,
  FileText,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { Button, Card } from "@/components/ui";
import { api } from "@/lib/api";

interface SharedSpaceModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  caseName: string;
  documents?: any[];
}

export function SharedSpaceModal({
  isOpen,
  onClose,
  caseId,
  caseName,
  documents = [],
}: SharedSpaceModalProps) {
  const [recipientEmail, setRecipientEmail] = useState("");
  const [recipientName, setRecipientName] = useState("");
  const [duration, setDuration] = useState("24h");
  const [role, setRole] = useState("VIEWER");
  const [passcode, setPasscode] = useState("");
  const [watermarkEnabled, setWatermarkEnabled] = useState(true);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>(documents.map((d) => d.id));
  const [createdShare, setCreatedShare] = useState<any | null>(null);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleCreate = async () => {
    if (!recipientEmail || !recipientEmail.includes("@")) {
      setError("Please provide a valid recipient email address.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await api.createSharedSpace(caseId, {
        name: `${caseName} — Client Portal`,
        recipient_email: recipientEmail,
        recipient_name: recipientName,
        duration,
        role,
        passcode: passcode || undefined,
        document_ids: selectedDocIds,
        watermark_enabled: watermarkEnabled,
      });
      setCreatedShare(res);
    } catch (err: any) {
      setError(err.message || "Failed to create shared space.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopyLink = () => {
    if (!createdShare?.token) return;
    const fullUrl = `${window.location.origin}/shared/${createdShare.token}`;
    navigator.clipboard.writeText(fullUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col rounded-2xl border border-border-light bg-[#111622] shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/20 text-primary">
              <Share2 size={18} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Create Matter Shared Space</h2>
              <p className="text-xs text-text-secondary">Expiring external collaboration room with dynamic watermarking</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-text-muted hover:bg-white/10 hover:text-white"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto p-6 space-y-5">
          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-400">
              <AlertCircle size={15} />
              <span>{error}</span>
            </div>
          )}

          {createdShare ? (
            /* Success View */
            <div className="space-y-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-5">
              <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
                <Check size={18} />
                <span>Shared Space Created Successfully!</span>
              </div>
              <p className="text-xs text-text-secondary">
                Share this secure link with <strong>{createdShare.recipient_email}</strong>. It will expire on{" "}
                {new Date(createdShare.expires_at).toLocaleString()}.
              </p>

              <div className="flex items-center gap-2 rounded-lg border border-border bg-bg p-2 font-mono text-xs text-white">
                <span className="flex-1 truncate">
                  {typeof window !== "undefined" ? `${window.location.origin}/shared/${createdShare.token}` : `/shared/${createdShare.token}`}
                </span>
                <Button size="sm" onClick={handleCopyLink} className="shrink-0 flex items-center gap-1">
                  {copied ? <Check size={13} /> : <Copy size={13} />}
                  {copied ? "Copied" : "Copy Link"}
                </Button>
              </div>

              {createdShare.has_passcode && passcode && (
                <div className="rounded-lg border border-border/80 bg-surface p-3 text-xs">
                  <span className="text-text-muted">Passcode required for client: </span>
                  <span className="font-mono font-bold text-white">{passcode}</span>
                </div>
              )}
            </div>
          ) : (
            /* Creation Form */
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-text-secondary">Recipient Email *</label>
                  <input
                    type="email"
                    placeholder="client@lawfirm.com"
                    value={recipientEmail}
                    onChange={(e) => setRecipientEmail(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-text-secondary">Recipient Name (Optional)</label>
                  <input
                    type="text"
                    placeholder="John Doe"
                    value={recipientName}
                    onChange={(e) => setRecipientName(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-text-secondary flex items-center gap-1.5">
                    <Clock size={13} className="text-primary" /> Expiration Duration
                  </label>
                  <select
                    value={duration}
                    onChange={(e) => setDuration(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-xs text-white focus:border-primary focus:outline-none"
                  >
                    <option value="1h">1 Hour (Quick Sign-off)</option>
                    <option value="24h">24 Hours (Standard Review)</option>
                    <option value="7d">7 Days (Due Diligence Room)</option>
                    <option value="30d">30 Days (Extended Deal Room)</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-text-secondary flex items-center gap-1.5">
                    <Eye size={13} className="text-primary" /> Access Role
                  </label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-xs text-white focus:border-primary focus:outline-none"
                  >
                    <option value="VIEWER">Viewer (Read watermarked docs only)</option>
                    <option value="REVIEWER">Reviewer (Can annotate &amp; comment)</option>
                    <option value="COLLABORATOR">Collaborator (Can upload responses)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-text-secondary flex items-center gap-1.5">
                  <Lock size={13} className="text-primary" /> Security Passcode (Optional)
                </label>
                <input
                  type="password"
                  placeholder="Set 4+ character passcode for client challenge"
                  value={passcode}
                  onChange={(e) => setPasscode(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-xs text-white focus:border-primary focus:outline-none"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="watermark-toggle"
                  checked={watermarkEnabled}
                  onChange={(e) => setWatermarkEnabled(e.target.checked)}
                  className="h-4 w-4 rounded border-border bg-bg text-primary"
                />
                <label htmlFor="watermark-toggle" className="text-xs text-text-secondary cursor-pointer">
                  Enable dynamic watermarking (stamps viewer email, IP, and UTC timestamp on all pages)
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border px-6 py-4 bg-surface/40">
          <span className="text-xs text-text-muted">DPDP Act 2023 Compliant · Encrypted in Transit</span>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={onClose}>
              {createdShare ? "Close" : "Cancel"}
            </Button>
            {!createdShare && (
              <Button size="sm" onClick={handleCreate} disabled={loading}>
                {loading ? <Loader2 size={14} className="animate-spin" /> : "Generate Secure Link"}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
