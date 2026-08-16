# =========== Jurisiva AI — Shared Types ===========
# Canonical TypeScript types shared between frontend and API layer.
# Keep in sync with backend/app/models and supabase/migrations.

# ---- Enums ----

export type Role = "OWNER" | "ADMIN" | "LAWYER" | "REVIEWER" | "STAFF" | "CLIENT";

export type CaseType =
  | "PROPERTY"
  | "CIVIL"
  | "CRIMINAL"
  | "COMMERCIAL"
  | "CORPORATE"
  | "FAMILY"
  | "LABOUR"
  | "TAX"
  | "OTHER";

export type CaseStatus = "ACTIVE" | "ARCHIVED" | "CLOSED";

export type DocumentStatus =
  | "UPLOADED"
  | "VALIDATING"
  | "PROCESSING"
  | "OCR_RUNNING"
  | "EXTRACTING"
  | "ANALYZING"
  | "COMPLETED"
  | "FAILED";

export type VerificationStatus =
  | "USER_PROVIDED"
  | "DOCUMENT_VERIFIED"
  | "EXTERNAL_SOURCE_VERIFIED"
  | "UNVERIFIED";

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type RiskCategory =
  | "OWNERSHIP"
  | "TITLE"
  | "DOCUMENT"
  | "IDENTITY"
  | "BOUNDARY"
  | "REGISTRATION"
  | "ENCUMBRANCE"
  | "LITIGATION"
  | "MISSING_EVIDENCE";

export type ComparisonVerdict = "MATCH" | "MISMATCH" | "MISSING" | "UNCERTAIN";

export type JobState =
  | "QUEUED"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "RETRYING"
  | "CANCELLED";

export type LanguageCode =
  | "en" | "hi" | "kn" | "ta" | "te" | "ml"
  | "mr" | "bn" | "gu" | "pa" | "ur";

export type OwnershipNodeType = "PERSON" | "PROPERTY" | "DOCUMENT" | "TRANSACTION";

export type OwnershipEdgeType =
  | "OWNED"
  | "TRANSFERRED"
  | "INHERITED"
  | "GIFTED"
  | "MORTGAGED"
  | "RELEASED"
  | "PARTITIONED";

// ---- Auth & Organizations ----

export interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
}

export interface Membership {
  id: string;
  organization_id: string;
  user_id: string;
  role: Role;
  created_at: string;
}

// ---- Cases ----

export interface LegalCase {
  id: string;
  organization_id: string;
  created_by: string;
  name: string;
  case_type: CaseType;
  status: CaseStatus;
  jurisdiction_state: string | null;
  jurisdiction_district: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
  document_count?: number;
  risk_summary?: RiskSummary;
}

// ---- Property ----

export interface Property {
  id: string;
  case_id: string;
  name: string | null;
  address: string | null;
  state: string | null;
  district: string | null;
  taluk: string | null;
  village: string | null;
  survey_number: string | null;
  hissa_number: string | null;
  plot_number: string | null;
  khata_number: string | null;
  registration_number: string | null;
  property_id_number: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface PropertyField {
  field: keyof Property;
  value: string | null;
  verification: VerificationStatus;
  source_document_id: string | null;
  source_page: number | null;
}

// ---- Documents ----

export interface DocumentRecord {
  id: string;
  case_id: string;
  uploaded_by: string;
  file_name: string;
  file_type: string;
  file_size: number;
  storage_path: string;
  document_type: string | null;
  status: DocumentStatus;
  page_count: number | null;
  language: LanguageCode | null;
  ocr_confidence: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentPage {
  id: string;
  document_id: string;
  page_number: number;
  text: string | null;
  language: LanguageCode | null;
  confidence: number | null;
  created_at: string;
}

// ---- Extraction & Evidence ----

export interface ExtractedEntity {
  id: string;
  case_id: string;
  document_id: string;
  page_number: number;
  entity_type: string;
  value: string;
  source_text: string;
  confidence: number;
  verification: VerificationStatus;
  created_at: string;
}

export interface Evidence {
  document_id: string;
  document_name: string;
  page_number: number;
  source_text: string;
  confidence: number | null;
}

export interface Finding {
  id: string;
  case_id: string;
  finding: string;
  explanation: string | null;
  evidence: Evidence[];
  compare_with?: Evidence[];
  risk_level: RiskLevel | null;
  recommended_action: string | null;
  created_at: string;
}

// ---- Ownership Graph ----

export interface OwnershipNode {
  id: string;
  case_id: string;
  node_type: OwnershipNodeType;
  label: string;
  metadata: Record<string, unknown>;
}

export interface OwnershipEdge {
  id: string;
  case_id: string;
  source_id: string;
  target_id: string;
  edge_type: OwnershipEdgeType;
  date: string | null;
  evidence: Evidence[];
  confidence: number;
}

export interface TimelineEvent {
  id: string;
  case_id: string;
  event_date: string | null;
  party: string | null;
  transaction_type: OwnershipEdgeType | string;
  description: string;
  document_id: string | null;
  document_name: string | null;
  page_number: number | null;
  evidence_text: string | null;
  confidence: number | null;
}

// ---- Comparison ----

export interface ComparisonResult {
  id: string;
  case_id: string;
  field_name: string;
  verdict: ComparisonVerdict;
  values: Array<{
    document_id: string;
    document_name: string;
    value: string | null;
    page_number: number | null;
    source_text: string | null;
  }>;
  explanation: string | null;
}

// ---- Risks ----

export interface Risk {
  id: string;
  case_id: string;
  category: RiskCategory;
  level: RiskLevel;
  title: string;
  description: string;
  evidence: Evidence[];
  recommended_action: string | null;
  resolved: boolean;
  created_at: string;
}

export interface RiskSummary {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

// ---- Research ----

export interface ResearchSession {
  id: string;
  case_id: string;
  question: string;
  status: JobState;
  answer: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface ResearchSource {
  id: string;
  session_id: string;
  title: string;
  url: string;
  source_type: string;
  retrieved_at: string;
  snippet: string | null;
}

// ---- AI Chat ----

export interface ChatMessage {
  id: string;
  case_id: string;
  role: "user" | "assistant";
  content: string;
  citations: Evidence[];
  created_at: string;
}

// ---- Drafting ----

export interface Draft {
  id: string;
  case_id: string;
  draft_type: string;
  title: string;
  content: string;
  status: "DRAFT" | "REVIEW" | "FINAL";
  created_at: string;
  updated_at: string;
}

// ---- Reports ----

export interface Report {
  id: string;
  case_id: string;
  report_type: string;
  title: string;
  status: JobState;
  storage_path: string | null;
  created_at: string;
}

// ---- Jobs ----

export interface Job {
  id: string;
  case_id: string | null;
  document_id: string | null;
  job_type: string;
  state: JobState;
  progress: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

// ---- API helpers ----

export interface ApiError {
  error: string;
  detail?: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}
