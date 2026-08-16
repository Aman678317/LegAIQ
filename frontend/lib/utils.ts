import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export const CASE_TYPES = [
  { value: "PROPERTY", label: "Property" },
  { value: "CIVIL", label: "Civil" },
  { value: "CRIMINAL", label: "Criminal" },
  { value: "COMMERCIAL", label: "Commercial" },
  { value: "CORPORATE", label: "Corporate" },
  { value: "FAMILY", label: "Family" },
  { value: "LABOUR", label: "Labour" },
  { value: "TAX", label: "Tax" },
  { value: "OTHER", label: "Other" },
] as const;

export const INDIAN_STATES = [
  "Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh", "Delhi", "Goa", "Gujarat",
  "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
  "Madhya Pradesh", "Maharashtra", "Odisha", "Punjab", "Rajasthan", "Tamil Nadu",
  "Telangana", "Uttar Pradesh", "Uttarakhand", "West Bengal",
] as const;

export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी (Hindi)" },
  { code: "kn", label: "ಕನ್ನಡ (Kannada)" },
  { code: "ta", label: "தமிழ் (Tamil)" },
  { code: "te", label: "తెలుగు (Telugu)" },
  { code: "ml", label: "മലയാളം (Malayalam)" },
  { code: "mr", label: "मराठी (Marathi)" },
  { code: "bn", label: "বাংলা (Bengali)" },
  { code: "gu", label: "ગુજરાતી (Gujarati)" },
  { code: "pa", label: "ਪੰਜਾਬੀ (Punjabi)" },
  { code: "ur", label: "اردو (Urdu)" },
] as const;

export const VERIFICATION_STYLES: Record<string, { label: string; className: string }> = {
  DOCUMENT_VERIFIED: { label: "Document Verified", className: "bg-blue-500/15 text-blue-400 border-blue-500/30" },
  EXTERNAL_SOURCE_VERIFIED: { label: "External Verified", className: "bg-violet-500/15 text-violet-400 border-violet-500/30" },
  USER_PROVIDED: { label: "User Provided", className: "bg-amber-500/15 text-amber-400 border-amber-500/30" },
  UNVERIFIED: { label: "Unverified", className: "bg-slate-500/15 text-slate-400 border-slate-500/30" },
};

export const RISK_STYLES: Record<string, { label: string; className: string }> = {
  CRITICAL: { label: "Critical", className: "bg-red-500/15 text-red-400 border-red-500/30" },
  HIGH: { label: "High", className: "bg-orange-500/15 text-orange-400 border-orange-500/30" },
  MEDIUM: { label: "Medium", className: "bg-amber-500/15 text-amber-400 border-amber-500/30" },
  LOW: { label: "Low", className: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
};

export const VERDICT_STYLES: Record<string, string> = {
  MATCH: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  MISMATCH: "bg-red-500/15 text-red-400 border-red-500/30",
  MISSING: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  UNCERTAIN: "bg-slate-500/15 text-slate-400 border-slate-500/30",
};

export const STATUS_STYLES: Record<string, string> = {
  UPLOADED: "bg-slate-500/15 text-slate-400",
  VALIDATING: "bg-slate-500/15 text-slate-400",
  PROCESSING: "bg-blue-500/15 text-blue-400",
  OCR_RUNNING: "bg-blue-500/15 text-blue-400",
  EXTRACTING: "bg-violet-500/15 text-violet-400",
  ANALYZING: "bg-violet-500/15 text-violet-400",
  COMPLETED: "bg-emerald-500/15 text-emerald-400",
  FAILED: "bg-red-500/15 text-red-400",
};

export const DRAFT_TYPES = [
  { value: "petition", label: "Petition" },
  { value: "legal_notice", label: "Legal Notice" },
  { value: "representation", label: "Representation" },
  { value: "application", label: "Application" },
  { value: "reply", label: "Reply" },
  { value: "affidavit", label: "Affidavit" },
  { value: "declaration", label: "Declaration" },
  { value: "property_letter", label: "Property Letter" },
  { value: "mutation_application", label: "Mutation Application" },
  { value: "registration_application", label: "Registration Application" },
  { value: "information_request", label: "Information Request" },
  { value: "due_diligence_report", label: "Due Diligence Report" },
] as const;
