import { createClient } from "./supabase";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/**
 * Reject any path that could escape the configured API origin
 * (protocol-relative "//host", absolute URLs, or backslash tricks).
 * All call sites pass internal relative paths like "/cases".
 */
function safeApiUrl(path: string): string {
  if (!/^\/[^/\\]/.test(path)) {
    throw new Error(`Unsafe API path: ${JSON.stringify(path.slice(0, 60))}`);
  }
  return `${API_URL}${path}`;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();

  const res = await fetch(safeApiUrl(path), {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || body.error || detail;
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json();
}

export const api = {
  // Cases
  createCase: (body: { name: string; case_type: string; organization_id: string; jurisdiction_state?: string; jurisdiction_district?: string; description?: string }) =>
    request<any>("/cases", { method: "POST", body: JSON.stringify(body) }),
  listCases: (organizationId: string, params?: { status?: string; case_type?: string }) => {
    const qs = new URLSearchParams({ organization_id: organizationId, ...params });
    return request<{ items: any[]; total: number }>(`/cases?${qs}`);
  },
  getCase: (caseId: string) => request<any>(`/cases/${caseId}`),
  updateCase: (caseId: string, body: any) => request<any>(`/cases/${caseId}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteCase: (caseId: string) => request<any>(`/cases/${caseId}`, { method: "DELETE" }),
  caseSummary: (caseId: string) => request<any>(`/cases/${caseId}/summary`),
  caseActivity: (caseId: string) => request<any[]>(`/cases/${caseId}/activity`),

  // Documents
  uploadDocument: async (caseId: string, file: File, documentType?: string) => {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    const form = new FormData();
    form.append("file", file);
    if (documentType) form.append("document_type", documentType);
    const res = await fetch(safeApiUrl(`/cases/${caseId}/documents`), {
      method: "POST",
      headers: { Authorization: `Bearer ${session?.access_token}` },
      body: form,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, body.detail || "Upload failed");
    }
    return res.json();
  },
  listDocuments: (caseId: string) => request<any[]>(`/cases/${caseId}/documents`),
  getDocument: (caseId: string, docId: string) => request<any>(`/cases/${caseId}/documents/${docId}`),
  getPages: (caseId: string, docId: string) => request<any[]>(`/cases/${caseId}/documents/${docId}/pages`),
  getDownloadUrl: (caseId: string, docId: string) => request<{ url: string }>(`/cases/${caseId}/documents/${docId}/download-url`),
  requestTranslation: (caseId: string, docId: string, page: number, lang: string) =>
    request<any>(`/cases/${caseId}/documents/${docId}/pages/${page}/translation/${lang}`),
  deleteDocument: (caseId: string, docId: string) => request<any>(`/cases/${caseId}/documents/${docId}`, { method: "DELETE" }),

  // Analysis & Chat
  askQuestion: (caseId: string, question: string) =>
    request<any>(`/cases/${caseId}/questions`, { method: "POST", body: JSON.stringify({ question }) }),
  getChatHistory: (caseId: string) => request<any[]>(`/cases/${caseId}/questions`),
  getAnalysis: (caseId: string) => request<any>(`/cases/${caseId}/analysis`),
  runAnalysis: (caseId: string) => request<any>(`/cases/${caseId}/analysis/run`, { method: "POST" }),
  explainDocument: (docId: string, language = "en") =>
    request<any>(`/documents/${docId}/explain?language=${language}`, { method: "POST" }),

  // Property
  getProperty: (caseId: string) => request<any>(`/cases/${caseId}/property`),
  updateProperty: (caseId: string, body: any) => request<any>(`/cases/${caseId}/property`, { method: "PATCH", body: JSON.stringify(body) }),
  propertyEntities: (caseId: string) => request<any>(`/cases/${caseId}/property/entities`),

  // Ownership & Timeline
  getOwnership: (caseId: string) => request<any>(`/cases/${caseId}/ownership`),
  rebuildOwnership: (caseId: string) => request<any>(`/cases/${caseId}/ownership/rebuild`, { method: "POST" }),
  getTimeline: (caseId: string) => request<any[]>(`/cases/${caseId}/timeline`),

  // Comparison
  compareDocuments: (caseId: string, documentIds: string[]) =>
    request<any>(`/cases/${caseId}/compare`, { method: "POST", body: JSON.stringify({ document_ids: documentIds }) }),
  getComparison: (caseId: string) => request<any[]>(`/cases/${caseId}/comparison`),

  // Risks
  getRisks: (caseId: string) => request<any[]>(`/cases/${caseId}/risks`),
  riskSummary: (caseId: string) => request<any>(`/cases/${caseId}/risks/summary`),
  updateRisk: (riskId: string, resolved: boolean) =>
    request<any>(`/risks/${riskId}`, { method: "PATCH", body: JSON.stringify({ resolved }) }),

  // Research
  startResearch: (caseId: string, question: string, jurisdiction?: string) =>
    request<any>(`/cases/${caseId}/research`, { method: "POST", body: JSON.stringify({ question, jurisdiction }) }),
  listResearch: (caseId: string) => request<any[]>(`/cases/${caseId}/research`),
  researchSources: (sessionId: string) => request<any[]>(`/research/${sessionId}/sources`),

  // Drafts
  createDraft: (caseId: string, body: { draft_type: string; title: string; instructions: string }) =>
    request<any>(`/cases/${caseId}/drafts`, { method: "POST", body: JSON.stringify(body) }),
  listDrafts: (caseId: string) => request<any[]>(`/cases/${caseId}/drafts`),
  getDraft: (draftId: string) => request<any>(`/drafts/${draftId}`),
  updateDraft: (draftId: string, body: any) => request<any>(`/drafts/${draftId}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteDraft: (draftId: string) => request<any>(`/drafts/${draftId}`, { method: "DELETE" }),

  // Reports
  generateReport: (caseId: string) => request<any>(`/cases/${caseId}/reports`, { method: "POST" }),
  listReports: (caseId: string) => request<any[]>(`/cases/${caseId}/reports`),
  getReport: (reportId: string) => request<any>(`/reports/${reportId}`),
  exportReport: (reportId: string, format: string) =>
    request<any>(`/reports/${reportId}/export`, { method: "POST", body: JSON.stringify({ format }) }),

  // Jobs
  listJobs: (caseId: string, params?: { state?: string; document_id?: string }) => {
    const qs = new URLSearchParams(params || {});
    return request<any[]>(`/cases/${caseId}/jobs?${qs}`);
  },

  // Voice
  voiceMessage: (caseId: string, sessionId: string, transcript: string, language?: string, sttProvider?: string) =>
    request<any>(`/cases/${caseId}/voice/message`, {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId, transcript, language,
        ...(sttProvider ? { stt_provider: sttProvider } : {}),
      }),
    }),
  endVoiceSession: (sessionId: string) =>
    request<any>(`/voice/sessions/${sessionId}/end`, { method: "POST" }),

  // Drafts — verification
  verifyDraft: (draftId: string) =>
    request<any>(`/drafts/${draftId}/verify`, { method: "POST" }),

  // Billing (metering + limits; checkout is server-501 until a provider is chosen)
  getBilling: (orgId: string) => request<any>(`/orgs/${orgId}/billing`),
  checkout: (orgId: string) =>
    request<any>(`/orgs/${orgId}/billing/checkout`, { method: "POST" }),

  // Voice — server-side providers for browsers without Web Speech
  transcribeAudio: async (caseId: string, blob: Blob) => {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    const form = new FormData();
    form.append("audio", blob, "speech.webm");
    const res = await fetch(
      `${API_URL}/cases/${caseId}/voice/transcribe`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${session?.access_token}` },
        body: form,
      }
    );
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new ApiError(res.status, body.detail || "Transcription failed");
    return body as { transcript: string; language: string; provider: string };
  },
  speakAudio: async (caseId: string, text: string, language: string) => {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    const res = await fetch(
      `${API_URL}/cases/${caseId}/voice/speak`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ text, language }),
      }
    );
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, body.detail || "Speech synthesis failed");
    }
    return res.blob();
  },

  // Organization members
  listMembers: (orgId: string) => request<any[]>(`/orgs/${orgId}/members`),
  addMember: (orgId: string, email: string, role: string) =>
    request<any>(`/orgs/${orgId}/members`, { method: "POST", body: JSON.stringify({ email, role }) }),
  updateMemberRole: (orgId: string, userId: string, role: string) =>
    request<any>(`/orgs/${orgId}/members/${userId}`, { method: "PATCH", body: JSON.stringify({ role }) }),
  removeMember: (orgId: string, userId: string) =>
    request<any>(`/orgs/${orgId}/members/${userId}`, { method: "DELETE" }),

  // Admin (platform administrators only)
  adminOverview: () => request<any>(`/admin/overview`),
  adminOrganizations: (limit = 50, offset = 0) =>
    request<any>(`/admin/organizations?limit=${limit}&offset=${offset}`),
  adminUsers: (limit = 50, offset = 0, q?: string) =>
    request<any>(`/admin/users?limit=${limit}&offset=${offset}${q ? `&q=${encodeURIComponent(q)}` : ""}`),
  adminSetPlatformAdmin: (userId: string, isPlatformAdmin: boolean) =>
    request<any>(`/admin/users/${userId}/platform-admin`, {
      method: "PATCH",
      body: JSON.stringify({ is_platform_admin: isPlatformAdmin }),
    }),
  adminCases: (limit = 50, offset = 0, status?: string) =>
    request<any>(`/admin/cases?limit=${limit}&offset=${offset}${status ? `&status=${status}` : ""}`),
  adminJobs: (limit = 50, offset = 0, state?: string, jobType?: string) =>
    request<any>(`/admin/jobs?limit=${limit}&offset=${offset}${state ? `&state=${state}` : ""}${jobType ? `&job_type=${jobType}` : ""}`),
  adminAgentRuns: (limit = 50, offset = 0) =>
    request<any>(`/admin/agent-runs?limit=${limit}&offset=${offset}`),
  adminAiUsage: () => request<any>(`/admin/ai-usage`),
  adminAuditEvents: (limit = 100, offset = 0, action?: string) =>
    request<any>(`/admin/audit-events?limit=${limit}&offset=${offset}${action ? `&action=${encodeURIComponent(action)}` : ""}`),
  adminAuditActions: () => request<{ actions: string[] }>(`/admin/audit-events/actions`),
};
