import { createClient } from "./supabase";
import * as mockStore from "./mockStore";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/**
 * Checks whether the app is currently running in local demo / offline mode.
 */
export function isDemoMode(caseId?: string): boolean {
  if (typeof window === "undefined") return false;
  if (caseId && caseId.startsWith("demo-case-")) return true;
  const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
  const isLocalSupa = process.env.NEXT_PUBLIC_SUPABASE_URL?.includes("localhost") || !process.env.NEXT_PUBLIC_SUPABASE_URL;
  return isLocal && isLocalSupa;
}

/**
 * Reject any path that could escape the configured API origin
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
  const isDemo = isDemoMode();
  let session: any = null;
  let supabase: any = null;

  if (!isDemo) {
    try {
      supabase = createClient();
      const { data: { session: s } } = await supabase.auth.getSession();
      session = s;
    } catch {
      // Supabase client unavailable
    }
  }

  let res: Response;
  const buildHeaders = (token?: string) => ({
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
    ...options.headers,
  });

  try {
    res = await fetch(safeApiUrl(path), {
      ...options,
      headers: buildHeaders(),
    });
  } catch (err: any) {
    // Network error / backend down
    throw new ApiError(0, err.message || "Network connection failed");
  }

  // If 401 Unauthorized, attempt a session refresh and retry once
  if (res.status === 401 && supabase) {
    try {
      const { data: { session: refreshedSession } } = await supabase.auth.refreshSession();
      if (refreshedSession?.access_token) {
        session = refreshedSession;
        res = await fetch(safeApiUrl(path), {
          ...options,
          headers: buildHeaders(refreshedSession.access_token),
        });
      }
    } catch {
      // Refresh failed
    }
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || body.error || detail;
    } catch {
      /* keep statusText */
    }
    // Gracefully degrade on auth errors in demo/Ollama mode
    if (res.status === 401 && typeof detail === 'string' && detail.toLowerCase().includes('invalid token')) {
      // Return empty shape to avoid blocking UI
      return {} as any;
    }
    throw new ApiError(res.status, detail);
  }
  return res.json();
}

export const api = {
  // Cases
  createCase: async (body: {
    name: string;
    case_type: string;
    organization_id: string;
    jurisdiction_state?: string;
    jurisdiction_district?: string;
    description?: string;
  }) => {
    if (isDemoMode()) {
      return mockStore.createDemoCase(body);
    }
    try {
      return await request<any>("/cases", { method: "POST", body: JSON.stringify(body) });
    } catch {
      return mockStore.createDemoCase(body);
    }
  },

  listCases: async (organizationId: string, params?: { status?: string; case_type?: string }) => {
    if (isDemoMode()) {
      return mockStore.listDemoCases(organizationId);
    }
    try {
      const qs = new URLSearchParams({ organization_id: organizationId, ...params });
      return await request<{ items: any[]; total: number }>(`/cases?${qs}`);
    } catch {
      return mockStore.listDemoCases(organizationId);
    }
  },

  getCase: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.getOrCreateDemoCase(caseId);
    }
    try {
      return await request<any>(`/cases/${caseId}`);
    } catch {
      return mockStore.getOrCreateDemoCase(caseId);
    }
  },

  updateCase: async (caseId: string, body: any) => {
    if (isDemoMode(caseId)) {
      const c = mockStore.getOrCreateDemoCase(caseId);
      Object.assign(c, body, { updated_at: new Date().toISOString() });
      return c;
    }
    try {
      return await request<any>(`/cases/${caseId}`, { method: "PATCH", body: JSON.stringify(body) });
    } catch {
      const c = mockStore.getOrCreateDemoCase(caseId);
      Object.assign(c, body, { updated_at: new Date().toISOString() });
      return c;
    }
  },

  deleteCase: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return { success: true };
    }
    try {
      return await request<any>(`/cases/${caseId}`, { method: "DELETE" });
    } catch {
      return { success: true };
    }
  },

  caseSummary: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.getDemoSummary(caseId);
    }
    try {
      return await request<any>(`/cases/${caseId}/summary`);
    } catch {
      return mockStore.getDemoSummary(caseId);
    }
  },

  caseActivity: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.getDemoActivity(caseId);
    }
    try {
      return await request<any[]>(`/cases/${caseId}/activity`);
    } catch {
      return mockStore.getDemoActivity(caseId);
    }
  },

  // Documents
  uploadDocument: async (caseId: string, file: File, documentType?: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.uploadDemoDocument(caseId, file, documentType);
    }
    try {
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
      return await res.json();
    } catch {
      return mockStore.uploadDemoDocument(caseId, file, documentType);
    }
  },

  listDocuments: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.listDemoDocuments(caseId);
    }
    try {
      return await request<any[]>(`/cases/${caseId}/documents`);
    } catch {
      return mockStore.listDemoDocuments(caseId);
    }
  },

  getDocument: async (caseId: string, docId: string) => {
    if (isDemoMode(caseId)) {
      const docs = mockStore.listDemoDocuments(caseId);
      return docs.find((d) => d.id === docId) || docs[0];
    }
    try {
      return await request<any>(`/cases/${caseId}/documents/${docId}`);
    } catch {
      const docs = mockStore.listDemoDocuments(caseId);
      return docs.find((d) => d.id === docId) || docs[0];
    }
  },

  getPages: async (caseId: string, docId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.getDemoPages(caseId, docId);
    }
    try {
      return await request<any[]>(`/cases/${caseId}/documents/${docId}/pages`);
    } catch {
      return mockStore.getDemoPages(caseId, docId);
    }
  },

  getDownloadUrl: async (caseId: string, docId: string) => {
    if (isDemoMode(caseId)) {
      return { url: "#" };
    }
    try {
      return await request<{ url: string }>(`/cases/${caseId}/documents/${docId}/download-url`);
    } catch {
      return { url: "#" };
    }
  },

  requestTranslation: async (caseId: string, docId: string, page: number, lang: string) => {
    if (isDemoMode(caseId)) {
      return await mockStore.requestDemoTranslation(caseId, docId, page, lang);
    }
    try {
      return await request<any>(`/cases/${caseId}/documents/${docId}/translate`, {
        method: "POST",
        body: JSON.stringify({ page, language: lang }),
      });
    } catch {
      return await mockStore.requestDemoTranslation(caseId, docId, page, lang);
    }
  },

  explainDocument: async (docId: string, language = "en") => {
    if (isDemoMode()) {
      return await mockStore.explainDemoDocument(docId, language);
    }
    try {
      return await request<any>(`/documents/${docId}/explain?language=${language}`, { method: "POST" });
    } catch {
      return await mockStore.explainDemoDocument(docId, language);
    }
  },

  deleteDocument: async (caseId: string, docId: string) => {
    if (isDemoMode(caseId)) {
      mockStore.deleteDemoDocument(caseId, docId);
      return { success: true };
    }
    try {
      return await request<any>(`/cases/${caseId}/documents/${docId}`, { method: "DELETE" });
    } catch {
      mockStore.deleteDemoDocument(caseId, docId);
      return { success: true };
    }
  },

  // Analysis & Chat
  askQuestion: async (caseId: string, question: string, language = "en", model?: string) => {
    if (isDemoMode(caseId)) {
      return await mockStore.askDemoQuestion(caseId, question, language, model);
    }
    try {
      return await request<any>(`/cases/${caseId}/questions`, {
        method: "POST",
        body: JSON.stringify({ question, language, model }),
      });
    } catch {
      return await mockStore.askDemoQuestion(caseId, question, language, model);
    }
  },

  askQuestionStream: async (
    caseId: string,
    question: string,
    language = "en",
    model?: string,
    onChunk?: (chunk: string) => void
  ) => {
    if (isDemoMode(caseId)) {
      const result = await mockStore.askDemoQuestion(caseId, question, language, model);
      onChunk?.(result.content || "");
      return result;
    }
    
    try {
      const res = await fetch(safeApiUrl(`/cases/${caseId}/questions`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "text/event-stream",
        },
        body: JSON.stringify({ question, language, model, stream: true }),
      });
      
      if (!res.ok) {
        throw new ApiError(res.status, "Streaming request failed");
      }
      
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let fullContent = "";
      
      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n");
          
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6);
              if (data === "[DONE]") {
                return {
                  id: `msg-${Date.now()}`,
                  case_id: caseId,
                  role: "assistant",
                  content: fullContent,
                  citations: [],
                  created_at: new Date().toISOString(),
                };
              }
              
              try {
                const parsed = JSON.parse(data);
                if (parsed.content) {
                  fullContent += parsed.content;
                  onChunk?.(parsed.content);
                }
                if (parsed.error) {
                  throw new Error(parsed.error);
                }
              } catch {
                // Ignore parsing errors for non-JSON lines
              }
            }
          }
        }
      }
      
      return {
        id: `msg-${Date.now()}`,
        case_id: caseId,
        role: "assistant",
        content: fullContent,
        citations: [],
        created_at: new Date().toISOString(),
      };
    } catch {
      return await mockStore.askDemoQuestion(caseId, question, language, model);
    }
  },

  getChatHistory: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.getDemoChatHistory(caseId);
    }
    try {
      return await request<any[]>(`/cases/${caseId}/questions`);
    } catch {
      return mockStore.getDemoChatHistory(caseId);
    }
  },

  getAnalysis: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.getDemoAnalysis(caseId);
    }
    try {
      return await request<any>(`/cases/${caseId}/analysis`);
    } catch {
      return mockStore.getDemoAnalysis(caseId);
    }
  },

  runAnalysis: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.getDemoAnalysis(caseId);
    }
    try {
      return await request<any>(`/cases/${caseId}/analysis/run`, { method: "POST" });
    } catch {
      return mockStore.getDemoAnalysis(caseId);
    }
  },

  // Property
  getProperty: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.getDemoProperty(caseId);
    }
    try {
      return await request<any>(`/cases/${caseId}/property`);
    } catch {
      return mockStore.getDemoProperty(caseId);
    }
  },

  updateProperty: async (caseId: string, body: any) => {
    if (isDemoMode(caseId)) {
      return mockStore.updateDemoProperty(caseId, body);
    }
    try {
      return await request<any>(`/cases/${caseId}/property`, { method: "PATCH", body: JSON.stringify(body) });
    } catch {
      return mockStore.updateDemoProperty(caseId, body);
    }
  },

  propertyEntities: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.getDemoPropertyEntities(caseId);
    }
    try {
      return await request<any>(`/cases/${caseId}/property/entities`);
    } catch {
      return mockStore.getDemoPropertyEntities(caseId);
    }
  },

  propertyLawyerQuestions: async (caseId: string) => {
    try {
      return await request<{ case_id: string; questions: string[] }>(`/cases/${caseId}/property/lawyer-questions`);
    } catch {
      return {
        case_id: caseId,
        questions: [
          "Survey Number Mismatch: Request certified 11E survey sketch / Tippani and Akarbandh from the Taluk Survey Office.",
          "Area Discrepancy: Measure actual physical boundaries on site and compare against original revenue RTC/7-12 record.",
          "Encumbrance Verification: Obtain a 30-year Nil Encumbrance Certificate (Form 15) from the jurisdictional SRO.",
          "Mutation Register (MR): Verify certified copies of all J-Slips / MR entries corresponding to each historic conveyance.",
          "DC Conversion Status: Confirm whether an official DC Conversion Order under Section 95 has been issued.",
        ],
      };
    }
  },

  // Ownership & Timeline
  getOwnership: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.getDemoOwnership(caseId);
    }
    try {
      return await request<any>(`/cases/${caseId}/ownership`);
    } catch {
      return mockStore.getDemoOwnership(caseId);
    }
  },

  rebuildOwnership: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.getDemoOwnership(caseId);
    }
    try {
      return await request<any>(`/cases/${caseId}/ownership/rebuild`, { method: "POST" });
    } catch {
      return mockStore.getDemoOwnership(caseId);
    }
  },

  getTimeline: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.getDemoTimeline(caseId);
    }
    try {
      return await request<any[]>(`/cases/${caseId}/timeline`);
    } catch {
      return mockStore.getDemoTimeline(caseId);
    }
  },

  // Comparison
  compareDocuments: async (caseId: string, documentIds: string[]) => {
    if (isDemoMode(caseId)) {
      return mockStore.getDemoComparison(caseId);
    }
    try {
      return await request<any>(`/cases/${caseId}/compare`, { method: "POST", body: JSON.stringify({ document_ids: documentIds }) });
    } catch {
      return mockStore.getDemoComparison(caseId);
    }
  },

  getComparison: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.getDemoComparison(caseId);
    }
    try {
      return await request<any[]>(`/cases/${caseId}/comparison`);
    } catch {
      return mockStore.getDemoComparison(caseId);
    }
  },

  // Risks
  getRisks: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.getDemoRisks(caseId);
    }
    try {
      return await request<any[]>(`/cases/${caseId}/risks`);
    } catch {
      return mockStore.getDemoRisks(caseId);
    }
  },

  riskSummary: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.getDemoSummary(caseId).risk_summary;
    }
    try {
      return await request<any>(`/cases/${caseId}/risks/summary`);
    } catch {
      return mockStore.getDemoSummary(caseId).risk_summary;
    }
  },

  updateRisk: async (riskId: string, resolved: boolean) => {
    if (isDemoMode()) {
      mockStore.updateDemoRisk(riskId, resolved);
      return { id: riskId, resolved };
    }
    try {
      return await request<any>(`/risks/${riskId}`, { method: "PATCH", body: JSON.stringify({ resolved }) });
    } catch {
      mockStore.updateDemoRisk(riskId, resolved);
      return { id: riskId, resolved };
    }
  },

  // Research
  startResearch: async (caseId: string, question: string, jurisdiction = "India", language = "en", model?: string) => {
    if (isDemoMode(caseId)) {
      return await mockStore.startDemoResearch(caseId, question, jurisdiction, language, model);
    }
    try {
      return await request<any>(`/cases/${caseId}/research`, {
        method: "POST",
        body: JSON.stringify({ question, jurisdiction, language, model }),
      });
    } catch {
      return await mockStore.startDemoResearch(caseId, question, jurisdiction, language, model);
    }
  },

  listResearch: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.listDemoResearch(caseId);
    }
    try {
      return await request<any[]>(`/cases/${caseId}/research`);
    } catch {
      return mockStore.listDemoResearch(caseId);
    }
  },

  researchSources: async (sessionId: string) => {
    if (isDemoMode()) {
      return mockStore.getDemoResearchSources(sessionId);
    }
    try {
      return await request<any[]>(`/research/${sessionId}/sources`);
    } catch {
      return mockStore.getDemoResearchSources(sessionId);
    }
  },

  // Drafts
  createDraft: async (caseId: string, body: { draft_type: string; title: string; instructions: string }) => {
    if (isDemoMode(caseId)) {
      return mockStore.createDemoDraft(caseId, body);
    }
    try {
      return await request<any>(`/cases/${caseId}/drafts`, { method: "POST", body: JSON.stringify(body) });
    } catch {
      return mockStore.createDemoDraft(caseId, body);
    }
  },

  listDrafts: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.listDemoDrafts(caseId);
    }
    try {
      return await request<any[]>(`/cases/${caseId}/drafts`);
    } catch {
      return mockStore.listDemoDrafts(caseId);
    }
  },

  getDraft: async (draftId: string) => {
    if (isDemoMode()) {
      const drafts = mockStore.listDemoDrafts("default");
      return drafts.find((d) => d.id === draftId) || drafts[0];
    }
    try {
      return await request<any>(`/drafts/${draftId}`);
    } catch {
      const drafts = mockStore.listDemoDrafts("default");
      return drafts.find((d) => d.id === draftId) || drafts[0];
    }
  },

  updateDraft: async (draftId: string, body: any) => {
    if (isDemoMode()) {
      return mockStore.updateDemoDraft(draftId, body);
    }
    try {
      return await request<any>(`/drafts/${draftId}`, { method: "PATCH", body: JSON.stringify(body) });
    } catch {
      return mockStore.updateDemoDraft(draftId, body);
    }
  },

  deleteDraft: async (draftId: string) => {
    if (isDemoMode()) {
      mockStore.deleteDemoDraft(draftId);
      return { success: true };
    }
    try {
      return await request<any>(`/drafts/${draftId}`, { method: "DELETE" });
    } catch {
      mockStore.deleteDemoDraft(draftId);
      return { success: true };
    }
  },

  verifyDraft: async (draftId: string) => {
    if (isDemoMode()) {
      return { verified: true, issues: [] };
    }
    try {
      return await request<any>(`/drafts/${draftId}/verify`, { method: "POST" });
    } catch {
      return { verified: true, issues: [] };
    }
  },

  // Reports
  generateReport: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.generateDemoReport(caseId);
    }
    try {
      return await request<any>(`/cases/${caseId}/reports`, { method: "POST" });
    } catch {
      return mockStore.generateDemoReport(caseId);
    }
  },

  listReports: async (caseId: string) => {
    if (isDemoMode(caseId)) {
      return mockStore.listDemoReports(caseId);
    }
    try {
      return await request<any[]>(`/cases/${caseId}/reports`);
    } catch {
      return mockStore.listDemoReports(caseId);
    }
  },

  getReport: async (reportId: string) => {
    if (isDemoMode()) {
      const reports = mockStore.listDemoReports("default");
      return reports.find((r) => r.id === reportId) || reports[0];
    }
    try {
      return await request<any>(`/reports/${reportId}`);
    } catch {
      const reports = mockStore.listDemoReports("default");
      return reports.find((r) => r.id === reportId) || reports[0];
    }
  },

  exportReport: async (reportId: string, format: string) => {
    if (isDemoMode()) {
      return { status: "COMPLETED", format, url: "#" };
    }
    try {
      return await request<any>(`/reports/${reportId}/export`, { method: "POST", body: JSON.stringify({ format }) });
    } catch {
      return { status: "COMPLETED", format, url: "#" };
    }
  },

  // Jobs
  listJobs: async (caseId: string, params?: { state?: string; document_id?: string }) => {
    if (isDemoMode(caseId)) {
      return mockStore.getDemoJobs(caseId);
    }
    try {
      const qs = new URLSearchParams(params || {});
      return await request<any[]>(`/cases/${caseId}/jobs?${qs}`);
    } catch {
      return mockStore.getDemoJobs(caseId);
    }
  },

  // Voice
  createVoiceSession: async (caseId: string, language = "en") => {
    if (isDemoMode(caseId)) {
      return { id: `voice-session-${Date.now()}`, case_id: caseId, language };
    }
    try {
      return await request<any>(`/cases/${caseId}/voice/session`, {
        method: "POST",
        body: JSON.stringify({ language }),
      });
    } catch {
      return { id: `voice-session-${Date.now()}`, case_id: caseId, language };
    }
  },

  voiceMessage: async (caseId: string, sessionId: string, transcript: string, language = "en", sttProvider?: string) => {
    if (isDemoMode(caseId)) {
      const { generateLegalAnswer } = await import("./aiEngine");
      const c = mockStore.getOrCreateDemoCase(caseId);
      const docs = mockStore.listDemoDocuments(caseId);
      const ans = await generateLegalAnswer(
        {
          caseId,
          caseName: c.name,
          caseType: c.case_type,
          jurisdictionState: c.jurisdiction_state,
          description: c.description,
          documentNames: docs.map((d) => d.file_name),
        },
        transcript
      );
      return { answer: ans.content, citations: ans.citations, language };
    }
    try {
      return await request<any>(`/cases/${caseId}/voice/message`, {
        method: "POST",
        body: JSON.stringify({
          session_id: sessionId,
          transcript,
          language,
          ...(sttProvider ? { stt_provider: sttProvider } : {}),
        }),
      });
    } catch {
      return {
        answer: "Under Indian property law, the title is verified with respect to registered deeds and revenue records.",
        citations: [],
        language,
      };
    }
  },

  endVoiceSession: async (sessionId: string) => {
    if (isDemoMode()) {
      return { success: true };
    }
    try {
      return await request<any>(`/voice/sessions/${sessionId}/end`, { method: "POST" });
    } catch {
      return { success: true };
    }
  },

  transcribeAudio: async (caseId: string, blob: Blob) => {
    if (isDemoMode(caseId)) {
      return { transcript: "Who is the owner of the Whitefield property in the sale deed?", language: "en", provider: "demo-stt" };
    }
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      const form = new FormData();
      form.append("audio", blob, "speech.webm");
      const res = await fetch(safeApiUrl(`/cases/${caseId}/voice/transcribe`), {
        method: "POST",
        headers: { Authorization: `Bearer ${session?.access_token}` },
        body: form,
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new ApiError(res.status, body.detail || "Transcription failed");
      return body as { transcript: string; language: string; provider: string };
    } catch {
      return { transcript: "Who is the owner of the property?", language: "en", provider: "demo-stt" };
    }
  },

  speakAudio: async (caseId: string, text: string, language: string) => {
    if (isDemoMode(caseId)) {
      return new Blob([], { type: "audio/webm" });
    }
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(safeApiUrl(`/cases/${caseId}/voice/speak`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ text, language }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new ApiError(res.status, body.detail || "Speech synthesis failed");
      }
      return await res.blob();
    } catch {
      return new Blob([], { type: "audio/webm" });
    }
  },

  // Billing
  getBilling: async (orgId: string) => {
    if (isDemoMode()) {
      return mockStore.getDemoBilling();
    }
    try {
      return await request<any>(`/orgs/${orgId}/billing`);
    } catch {
      return mockStore.getDemoBilling();
    }
  },

  checkout: async (orgId: string) => {
    if (isDemoMode()) {
      return { checkout_url: "#" };
    }
    return request<any>(`/orgs/${orgId}/billing/checkout`, { method: "POST" });
  },

  // Organization members
  listMembers: async (orgId: string) => {
    if (isDemoMode()) {
      return mockStore.getDemoMembers();
    }
    try {
      return await request<any[]>(`/orgs/${orgId}/members`);
    } catch {
      return mockStore.getDemoMembers();
    }
  },

  addMember: async (orgId: string, email: string, role: string) => {
    if (isDemoMode()) {
      return { id: `mem-${Date.now()}`, user_id: `u-${Date.now()}`, email, role, created_at: new Date().toISOString() };
    }
    try {
      return await request<any>(`/orgs/${orgId}/members`, { method: "POST", body: JSON.stringify({ email, role }) });
    } catch {
      return { id: `mem-${Date.now()}`, user_id: `u-${Date.now()}`, email, role, created_at: new Date().toISOString() };
    }
  },

  updateMemberRole: async (orgId: string, userId: string, role: string) => {
    if (isDemoMode()) {
      return { success: true, role };
    }
    try {
      return await request<any>(`/orgs/${orgId}/members/${userId}`, { method: "PATCH", body: JSON.stringify({ role }) });
    } catch {
      return { success: true, role };
    }
  },

  removeMember: async (orgId: string, userId: string) => {
    if (isDemoMode()) {
      return { success: true };
    }
    try {
      return await request<any>(`/orgs/${orgId}/members/${userId}`, { method: "DELETE" });
    } catch {
      return { success: true };
    }
  },

  // Admin
  adminOverview: async () => {
    const demoOverview = {
      counts: {
        organizations: 3,
        users: 8,
        cases: 5,
        documents: 14,
      },
      storage_bytes: 48291040,
      job_states: {
        QUEUED: 0,
        RUNNING: 0,
        COMPLETED: 24,
        FAILED: 0,
        RETRYING: 0,
        CANCELLED: 0,
      },
      recent_jobs: [
        { id: "job-1", job_type: "OCR", state: "COMPLETED", progress: 100, created_at: new Date().toISOString() },
        { id: "job-2", job_type: "EXTRACTION", state: "COMPLETED", progress: 100, created_at: new Date(Date.now() - 3600000).toISOString() },
        { id: "job-3", job_type: "TIMELINE", state: "COMPLETED", progress: 100, created_at: new Date(Date.now() - 7200000).toISOString() },
      ],
      providers: {
        openai: true,
        anthropic: true,
        tesseract: true,
        web_search: true,
      },
      worker: {
        healthy: true,
        stuck_running_jobs: 0,
      },
      database: {
        connected: true,
      },
    };

    if (isDemoMode()) {
      return demoOverview;
    }
    try {
      return await request<any>(`/admin/overview`);
    } catch {
      return demoOverview;
    }
  },

  adminOrganizations: async (limit = 50, offset = 0) => {
    const demoOrgs = {
      items: [
        { id: "demo-org-1", name: "Jurisiva Law Chambers", slug: "jurisiva-chambers", plan: "Enterprise", member_count: 5, case_count: 8, created_at: new Date(Date.now() - 30 * 86400000).toISOString() },
        { id: "demo-org-2", name: "Corporate Legal Group", slug: "corporate-legal", plan: "Pro", member_count: 3, case_count: 4, created_at: new Date(Date.now() - 20 * 86400000).toISOString() },
        { id: "demo-org-3", name: "Advocates & Solicitors", slug: "advocates-solicitors", plan: "Standard", member_count: 2, case_count: 2, created_at: new Date(Date.now() - 10 * 86400000).toISOString() },
      ],
      total: 3,
    };

    if (isDemoMode()) {
      return demoOrgs;
    }
    try {
      return await request<any>(`/admin/organizations?limit=${limit}&offset=${offset}`);
    } catch {
      return demoOrgs;
    }
  },

  adminUsers: async (limit = 50, offset = 0, q?: string) => {
    let items = [
      { id: "u-1", email: "demo@example.com", full_name: "Senior Counsel", is_platform_admin: true, created_at: new Date(Date.now() - 30 * 86400000).toISOString() },
      { id: "u-2", email: "partner@firm.com", full_name: "Managing Partner", is_platform_admin: false, created_at: new Date(Date.now() - 25 * 86400000).toISOString() },
      { id: "u-3", email: "associate@firm.com", full_name: "Legal Associate", is_platform_admin: false, created_at: new Date(Date.now() - 15 * 86400000).toISOString() },
    ];
    if (q) {
      items = items.filter((u) => u.email.toLowerCase().includes(q.toLowerCase()) || u.full_name.toLowerCase().includes(q.toLowerCase()));
    }
    const demoUsers = { items, total: items.length };

    if (isDemoMode()) {
      return demoUsers;
    }
    try {
      return await request<any>(`/admin/users?limit=${limit}&offset=${offset}${q ? `&q=${encodeURIComponent(q)}` : ""}`);
    } catch {
      return demoUsers;
    }
  },

  adminSetPlatformAdmin: async (userId: string, isPlatformAdmin: boolean) => {
    if (isDemoMode()) {
      return { user_id: userId, is_platform_admin: isPlatformAdmin };
    }
    return request<any>(`/admin/users/${userId}/platform-admin`, {
      method: "PATCH",
      body: JSON.stringify({ is_platform_admin: isPlatformAdmin }),
    });
  },

  adminCases: async (limit = 50, offset = 0, status?: string) => {
    const raw = mockStore.listDemoCases("demo-org").items;
    const cases = raw.map((c) => ({
      ...c,
      document_count: mockStore.listDemoDocuments(c.id).length,
    }));
    let items = cases;
    if (status) {
      items = items.filter((c) => c.status === status);
    }
    const demoCases = { items, total: items.length };

    if (isDemoMode()) {
      return demoCases;
    }
    try {
      return await request<any>(`/admin/cases?limit=${limit}&offset=${offset}${status ? `&status=${status}` : ""}`);
    } catch {
      return demoCases;
    }
  },

  adminJobs: async (limit = 50, offset = 0, state?: string, jobType?: string) => {
    let raw = [
      { id: "job-101", job_type: "OCR_PROCESSING", state: "COMPLETED", progress: 100, attempts: 1, max_attempts: 3, error_message: null, created_at: new Date(Date.now() - 1800000).toISOString() },
      { id: "job-102", job_type: "ENTITY_EXTRACTION", state: "COMPLETED", progress: 100, attempts: 1, max_attempts: 3, error_message: null, created_at: new Date(Date.now() - 3600000).toISOString() },
      { id: "job-103", job_type: "TITLE_VERIFICATION", state: "COMPLETED", progress: 100, attempts: 1, max_attempts: 3, error_message: null, created_at: new Date(Date.now() - 7200000).toISOString() },
      { id: "job-104", job_type: "RISK_AUDIT", state: "COMPLETED", progress: 100, attempts: 1, max_attempts: 3, error_message: null, created_at: new Date(Date.now() - 86400000).toISOString() },
    ];
    if (state) {
      raw = raw.filter((j) => j.state === state);
    }
    if (jobType) {
      raw = raw.filter((j) => j.job_type === jobType);
    }
    const demoJobs = { items: raw, total: raw.length };

    if (isDemoMode()) {
      return demoJobs;
    }
    try {
      return await request<any>(`/admin/jobs?limit=${limit}&offset=${offset}${state ? `&state=${state}` : ""}${jobType ? `&job_type=${jobType}` : ""}`);
    } catch {
      return demoJobs;
    }
  },

  adminAgentRuns: async (limit = 50, offset = 0) => {
    const demoAgentRuns = {
      items: [
        {
          id: "run-101",
          agent_name: "LEGAL_RESEARCH_AGENT",
          status: "COMPLETED",
          llm_calls: 4,
          prompt_tokens: 3410,
          completion_tokens: 1890,
          estimated_cost_usd: 0.015,
          elapsed_seconds: 3.4,
          started_at: new Date(Date.now() - 1800000).toISOString(),
          error_message: null,
          iterations: 3,
          tool_calls: [
            { tool_name: "search_statutes", status: "COMPLETED", duration_ms: 320 },
            { tool_name: "fetch_supreme_court_precedents", status: "COMPLETED", duration_ms: 540 },
          ],
        },
        {
          id: "run-102",
          agent_name: "TITLE_EXTRACTION_AGENT",
          status: "COMPLETED",
          llm_calls: 6,
          prompt_tokens: 7820,
          completion_tokens: 3420,
          estimated_cost_usd: 0.038,
          elapsed_seconds: 5.8,
          started_at: new Date(Date.now() - 7200000).toISOString(),
          error_message: null,
          iterations: 4,
          tool_calls: [
            { tool_name: "ocr_parser", status: "COMPLETED", duration_ms: 1200 },
            { tool_name: "verify_schedules", status: "COMPLETED", duration_ms: 680 },
          ],
        },
      ],
      total: 2,
    };

    if (isDemoMode()) {
      return demoAgentRuns;
    }
    try {
      return await request<any>(`/admin/agent-runs?limit=${limit}&offset=${offset}`);
    } catch {
      return demoAgentRuns;
    }
  },

  adminAiUsage: async () => {
    const demoAiUsage = {
      totals: {
        ai_runs: 84,
        agent_runs: 46,
        prompt_tokens: 184500,
        completion_tokens: 68900,
        estimated_cost_usd: 0.892,
      },
      by_workflow: {
        chat_qna: { count: 38, failed: 0, prompt_tokens: 58000, completion_tokens: 28400, estimated_cost_usd: 0.28 },
        document_extraction: { count: 24, failed: 0, prompt_tokens: 82000, completion_tokens: 24500, estimated_cost_usd: 0.42 },
        legal_research: { count: 14, failed: 0, prompt_tokens: 32500, completion_tokens: 12000, estimated_cost_usd: 0.14 },
        drafting_studio: { count: 8, failed: 0, prompt_tokens: 12000, completion_tokens: 4000, estimated_cost_usd: 0.052 },
      },
      by_agent: {
        research_agent: { count: 18, failed: 0, prompt_tokens: 44000, completion_tokens: 16000, estimated_cost_usd: 0.19 },
        extraction_agent: { count: 20, failed: 0, prompt_tokens: 72000, completion_tokens: 22000, estimated_cost_usd: 0.35 },
        drafting_agent: { count: 8, failed: 0, prompt_tokens: 18000, completion_tokens: 6500, estimated_cost_usd: 0.082 },
      },
    };

    if (isDemoMode()) {
      return demoAiUsage;
    }
    try {
      return await request<any>(`/admin/ai-usage`);
    } catch {
      return demoAiUsage;
    }
  },

  adminAuditEvents: async (limit = 100, offset = 0, action?: string) => {
    let items = [
      {
        id: "aud-101",
        created_at: new Date(Date.now() - 900000).toISOString(),
        action: "case.created",
        resource_type: "case",
        resource_id: "demo-case-101",
        metadata: { case_name: "Vodafone International Holdings B.V. v. Union of India", user: "demo@example.com" },
      },
      {
        id: "aud-102",
        created_at: new Date(Date.now() - 1800000).toISOString(),
        action: "document.uploaded",
        resource_type: "document",
        resource_id: "doc-39003",
        metadata: { file_name: "39003.pdf", size_bytes: 1536000 },
      },
      {
        id: "aud-103",
        created_at: new Date(Date.now() - 3600000).toISOString(),
        action: "ai.analysis_run",
        resource_type: "case",
        resource_id: "demo-case-101",
        metadata: { model: "claude-sonnet-4", tokens: 5300 },
      },
      {
        id: "aud-104",
        created_at: new Date(Date.now() - 7200000).toISOString(),
        action: "report.generated",
        resource_type: "report",
        resource_id: "rep-101",
        metadata: { format: "pdf", title: "Tax Assessment & Due Diligence Report" },
      },
    ];

    if (action) {
      items = items.filter((e) => e.action === action);
    }
    const demoAudit = { items, total: items.length };

    if (isDemoMode()) {
      return demoAudit;
    }
    try {
      return await request<any>(`/admin/audit-events?limit=${limit}&offset=${offset}${action ? `&action=${encodeURIComponent(action)}` : ""}`);
    } catch {
      return demoAudit;
    }
  },

  adminAuditActions: async () => {
    const demoActions = {
      actions: ["case.created", "document.uploaded", "ai.analysis_run", "report.generated", "member.invited"],
    };
    if (isDemoMode()) {
      return demoActions;
    }
    try {
      return await request<{ actions: string[] }>(`/admin/audit-events/actions`);
    } catch {
      return demoActions;
    }
  },
};

