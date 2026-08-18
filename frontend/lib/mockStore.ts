// Client-side mock store providing seamless demo mode and offline fallback
// integrated with the intelligent domain-aware Indian Legal AI Engine.

import {
  LegalContext,
  generateLegalAnswer,
  generateDocumentPages,
  generateAnalysisData,
  generateRisks,
  generateOwnershipGraph,
  generatePropertyData,
  generateTimeline,
  generateLegalResearch,
  generateLegalDraft,
  generateLegalReport,
  detectDomain,
} from "./aiEngine";
import { explainLegalDocument, translateLegalText } from "./legalTranslator";

const STORAGE_PREFIX = "jurisiva_demo_";

function getStorage<T>(key: string, defaultVal: T): T {
  if (typeof window === "undefined") return defaultVal;
  try {
    const item = localStorage.getItem(STORAGE_PREFIX + key);
    return item ? JSON.parse(item) : defaultVal;
  } catch {
    return defaultVal;
  }
}

function setStorage<T>(key: string, val: T): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(val));
  } catch {
    // ignore
  }
}

export interface DemoCase {
  id: string;
  name: string;
  case_type: string;
  status: string;
  organization_id: string;
  jurisdiction_state?: string;
  jurisdiction_district?: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface DemoDocument {
  id: string;
  case_id: string;
  file_name: string;
  file_type: string;
  file_size: number;
  page_count: number;
  ocr_confidence: number;
  status: string;
  language: string;
  created_at: string;
  updated_at: string;
}

export interface DemoPage {
  id: string;
  document_id: string;
  page_number: number;
  text: string;
  language: string;
  confidence: number;
}

export interface DemoRisk {
  id: string;
  case_id: string;
  title: string;
  description: string;
  level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  category: string;
  recommended_action: string;
  evidence: Array<{
    document_id?: string;
    document_name: string;
    page_number: number;
    source_text: string;
  }>;
  resolved: boolean;
  created_at: string;
}

function getContext(caseId: string): LegalContext {
  const c = getOrCreateDemoCase(caseId);
  const docs = listDemoDocuments(caseId);
  return {
    caseId,
    caseName: c.name,
    caseType: c.case_type,
    jurisdictionState: c.jurisdiction_state,
    description: c.description,
    documentNames: docs.map((d) => d.file_name),
  };
}

function createDefaultCaseData(caseId: string, name = "Vodafone International Holdings B.V. v. Union of India"): DemoCase {
  const isVodafone = name.toLowerCase().includes("vodafone") || caseId.includes("vodafone");
  return {
    id: caseId,
    name: isVodafone ? "Vodafone International Holdings B.V. v. Union of India" : name,
    case_type: isVodafone ? "TAX" : "PROPERTY",
    status: "ACTIVE",
    organization_id: "demo-org",
    jurisdiction_state: isVodafone ? "Supreme Court of India" : "Karnataka",
    jurisdiction_district: isVodafone ? "New Delhi / Mumbai" : "Bengaluru Urban",
    description: isVodafone
      ? "Direct tax appeal regarding Section 9(1)(i) and Section 195 withholding tax on offshore transfer of shares of CGP Investments (Holdings) Ltd."
      : "Title investigation and due diligence for Survey Number 124/3.",
    created_at: new Date(Date.now() - 7 * 86400000).toISOString(),
    updated_at: new Date().toISOString(),
  };
}

function createDefaultDocuments(caseId: string): DemoDocument[] {
  const c = getStorage<Record<string, DemoCase>>("cases", {})[caseId];
  const isTax = c ? detectDomain({ caseId, caseName: c.name, caseType: c.case_type, documentNames: [] }) === "TAX" : false;

  if (isTax || (c && c.name.toLowerCase().includes("vodafone"))) {
    return [
      {
        id: `${caseId}-doc-1`,
        case_id: caseId,
        file_name: "39003.pdf",
        file_type: "application/pdf",
        file_size: 1536000,
        page_count: 5,
        ocr_confidence: 0.98,
        status: "COMPLETED",
        language: "en",
        created_at: new Date(Date.now() - 6 * 86400000).toISOString(),
        updated_at: new Date(Date.now() - 6 * 86400000).toISOString(),
      },
      {
        id: `${caseId}-doc-2`,
        case_id: caseId,
        file_name: "share_purchase_agreement_2007.pdf",
        file_type: "application/pdf",
        file_size: 2457600,
        page_count: 8,
        ocr_confidence: 0.96,
        status: "COMPLETED",
        language: "en",
        created_at: new Date(Date.now() - 5 * 86400000).toISOString(),
        updated_at: new Date(Date.now() - 5 * 86400000).toISOString(),
      },
      {
        id: `${caseId}-doc-3`,
        case_id: caseId,
        file_name: "section_201_show_cause_notice.pdf",
        file_type: "application/pdf",
        file_size: 984000,
        page_count: 3,
        ocr_confidence: 0.95,
        status: "COMPLETED",
        language: "en",
        created_at: new Date(Date.now() - 4 * 86400000).toISOString(),
        updated_at: new Date(Date.now() - 4 * 86400000).toISOString(),
      },
    ];
  }

  return [
    {
      id: `${caseId}-doc-1`,
      case_id: caseId,
      file_name: "sale_deed_1987.pdf",
      file_type: "application/pdf",
      file_size: 2457600,
      page_count: 7,
      ocr_confidence: 0.94,
      status: "COMPLETED",
      language: "en",
      created_at: new Date(Date.now() - 6 * 86400000).toISOString(),
      updated_at: new Date(Date.now() - 6 * 86400000).toISOString(),
    },
    {
      id: `${caseId}-doc-2`,
      case_id: caseId,
      file_name: "partition_deed_2004.pdf",
      file_type: "application/pdf",
      file_size: 1843200,
      page_count: 4,
      ocr_confidence: 0.91,
      status: "COMPLETED",
      language: "kn",
      created_at: new Date(Date.now() - 5 * 86400000).toISOString(),
      updated_at: new Date(Date.now() - 5 * 86400000).toISOString(),
    },
    {
      id: `${caseId}-doc-3`,
      case_id: caseId,
      file_name: "rtc_pahani_record.pdf",
      file_type: "application/pdf",
      file_size: 984000,
      page_count: 2,
      ocr_confidence: 0.89,
      status: "COMPLETED",
      language: "kn",
      created_at: new Date(Date.now() - 3 * 86400000).toISOString(),
      updated_at: new Date(Date.now() - 3 * 86400000).toISOString(),
    },
  ];
}

// ---------------------- Public Demo Store Operations ----------------------

export function getOrCreateDemoCase(caseId: string): DemoCase {
  const cases = getStorage<Record<string, DemoCase>>("cases", {});
  if (cases[caseId]) return cases[caseId];

  const defaultCase = createDefaultCaseData(caseId);
  cases[caseId] = defaultCase;
  setStorage("cases", cases);
  return defaultCase;
}

export function listDemoCases(orgId: string): { items: DemoCase[]; total: number } {
  const casesMap = getStorage<Record<string, DemoCase>>("cases", {});
  let items = Object.values(casesMap);
  if (items.length === 0) {
    const demo = createDefaultCaseData("demo-case-001");
    casesMap[demo.id] = demo;
    setStorage("cases", casesMap);
    items = [demo];
  }
  return { items, total: items.length };
}

export function createDemoCase(body: {
  name: string;
  case_type: string;
  organization_id: string;
  jurisdiction_state?: string;
  jurisdiction_district?: string;
  description?: string;
}): DemoCase {
  const id = `demo-case-${Date.now()}`;
  const c: DemoCase = {
    id,
    name: body.name,
    case_type: body.case_type || "PROPERTY",
    status: "ACTIVE",
    organization_id: body.organization_id || "demo-org",
    jurisdiction_state: body.jurisdiction_state || "Karnataka",
    jurisdiction_district: body.jurisdiction_district || "Bengaluru Urban",
    description: body.description || "",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  const cases = getStorage<Record<string, DemoCase>>("cases", {});
  cases[id] = c;
  setStorage("cases", cases);
  return c;
}

export function getDemoSummary(caseId: string) {
  const c = getOrCreateDemoCase(caseId);
  const docs = listDemoDocuments(caseId);
  const risks = getDemoRisks(caseId);
  const openRisks = risks.filter((r) => !r.resolved);

  return {
    case: c,
    document_count: docs.length,
    processing_count: 0,
    risk_summary: {
      total: openRisks.length,
      critical: openRisks.filter((r) => r.level === "CRITICAL").length,
      high: openRisks.filter((r) => r.level === "HIGH").length,
      medium: openRisks.filter((r) => r.level === "MEDIUM").length,
      low: openRisks.filter((r) => r.level === "LOW").length,
    },
  };
}

export function getDemoActivity(caseId: string) {
  const ctx = getContext(caseId);
  const domain = detectDomain(ctx);

  const isTax = domain === "TAX";
  const defaultActivities = isTax
    ? [
        {
          id: "act-1",
          description: "AI synthesized Section 9(1)(i) ratio from Supreme Court judgment 39003.pdf",
          created_at: new Date(Date.now() - 3600000).toISOString(),
        },
        {
          id: "act-2",
          description: "Corporate holding chain mapped: Vodafone B.V. → CGP Investments → Hutchison Essar",
          created_at: new Date(Date.now() - 7200000).toISOString(),
        },
        {
          id: "act-3",
          description: "OCR pipeline extracted 5 pages from 39003.pdf (98% confidence)",
          created_at: new Date(Date.now() - 86400000).toISOString(),
        },
        {
          id: "act-4",
          description: "Case workspace initialized for Tax Due Diligence & Litigation",
          created_at: new Date(Date.now() - 2 * 86400000).toISOString(),
        },
      ]
    : [
        {
          id: "act-1",
          description: "Title verification completed for Sale Deed 1987 & Partition Deed 2004",
          created_at: new Date(Date.now() - 3600000).toISOString(),
        },
        {
          id: "act-2",
          description: "Ownership chain reconstructed with 3 parties and evidenced transfers",
          created_at: new Date(Date.now() - 7200000).toISOString(),
        },
        {
          id: "act-3",
          description: "OCR pipeline extracted 7 pages from sale_deed_1987.pdf (94% confidence)",
          created_at: new Date(Date.now() - 86400000).toISOString(),
        },
        {
          id: "act-4",
          description: "Case workspace initialized for due diligence",
          created_at: new Date(Date.now() - 2 * 86400000).toISOString(),
        },
      ];

  const activities = getStorage<Array<{ id: string; description: string; created_at: string }>>(
    `activities_${caseId}`,
    defaultActivities
  );
  return activities;
}

export function listDemoDocuments(caseId: string): DemoDocument[] {
  const docsMap = getStorage<Record<string, DemoDocument[]>>("documents", {});
  if (!docsMap[caseId]) {
    docsMap[caseId] = createDefaultDocuments(caseId);
    setStorage("documents", docsMap);
  }
  return docsMap[caseId];
}

export function uploadDemoDocument(caseId: string, file: File, documentType?: string): DemoDocument {
  const ctx = getContext(caseId);
  const docId = `doc-${Date.now()}`;
  const doc: DemoDocument = {
    id: docId,
    case_id: caseId,
    file_name: file.name,
    file_type: file.type || "application/pdf",
    file_size: file.size || 1536000,
    page_count: Math.floor(Math.random() * 4) + 3,
    ocr_confidence: 0.96,
    status: "COMPLETED",
    language: "en",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  const docsMap = getStorage<Record<string, DemoDocument[]>>("documents", {});
  docsMap[caseId] = [doc, ...(docsMap[caseId] || [])];
  setStorage("documents", docsMap);

  // Generate dynamic pages based on file name & case context
  const dynamicPages = generateDocumentPages(ctx, file.name);
  const allPages = getStorage<Record<string, DemoPage[]>>("pages", {});
  allPages[docId] = dynamicPages.map((p) => ({ ...p, document_id: docId }));
  allPages[file.name] = allPages[docId]; // also map by filename
  setStorage("pages", allPages);

  // Add activity log
  const acts = getDemoActivity(caseId);
  acts.unshift({
    id: `act-${Date.now()}`,
    description: `Uploaded "${file.name}" — OCR & AI legal extraction completed (${doc.page_count} pages)`,
    created_at: new Date().toISOString(),
  });
  setStorage(`activities_${caseId}`, acts);

  return doc;
}

export function deleteDemoDocument(caseId: string, docId: string): void {
  const docsMap = getStorage<Record<string, DemoDocument[]>>("documents", {});
  if (docsMap[caseId]) {
    docsMap[caseId] = docsMap[caseId].filter((d) => d.id !== docId && d.file_name !== docId);
    setStorage("documents", docsMap);
  }
}

export function getDemoPages(caseId: string, docId: string): DemoPage[] {
  const ctx = getContext(caseId);
  const allPages = getStorage<Record<string, DemoPage[]>>("pages", {});

  if (allPages[docId] && allPages[docId].length > 0) {
    return allPages[docId];
  }

  // Check matching by doc filename
  const docs = listDemoDocuments(caseId);
  const matchingDoc = docs.find((d) => d.id === docId || d.file_name === docId);
  const fileName = matchingDoc ? matchingDoc.file_name : docId;

  if (allPages[fileName] && allPages[fileName].length > 0) {
    return allPages[fileName];
  }

  // Generate fresh dynamic pages
  const generated = generateDocumentPages(ctx, fileName);
  allPages[docId] = generated;
  setStorage("pages", allPages);
  return generated;
}

export async function explainDemoDocument(docId: string, lang = "en") {
  const allPages = getStorage<Record<string, any[]>>("pages", {});
  const pages = allPages[docId] || [];
  const textSample = pages.map((p) => p.text).join(" ");
  const isTax = textSample.toLowerCase().includes("vodafone") || textSample.toLowerCase().includes("tax") || textSample.toLowerCase().includes("revenue");
  const explanation = await explainLegalDocument(docId, "Court Judgment", lang, isTax);
  return { explanation };
}

export async function requestDemoTranslation(caseId: string, docId: string, pageNumber: number, lang: string) {
  const pages = getDemoPages(caseId, docId);
  const targetPage = pages.find((p) => p.page_number === pageNumber) || pages[0];
  const sourceText = targetPage?.text || "";
  const translated = await translateLegalText(sourceText, lang);
  return {
    status: "COMPLETED",
    text: translated,
  };
}

export function getDemoAnalysis(caseId: string) {
  const ctx = getContext(caseId);
  return generateAnalysisData(ctx);
}

export function getDemoProperty(caseId: string, forceRefresh = false) {
  const ctx = getContext(caseId);
  const domain = detectDomain(ctx);
  const isTaxOrVodafone = domain === "TAX" || ctx.caseName.toLowerCase().includes("vodafone");

  const stored = forceRefresh ? null : getStorage<Record<string, any>>(`property_${caseId}`, null);

  if (stored && stored.fields && Array.isArray(stored.fields)) {
    const isStoredTax = stored.fields.some(
      (f: any) =>
        (f.value || "").toLowerCase().includes("cgp") ||
        (f.value || "").toLowerCase().includes("cayman") ||
        (f.value || "").toLowerCase().includes("offshore")
    );
    if (isStoredTax === isTaxOrVodafone) {
      return stored;
    }
  }

  const prop = generatePropertyData(ctx);
  setStorage(`property_${caseId}`, prop);
  return prop;
}

export function updateDemoProperty(caseId: string, updates: Record<string, string>) {
  const current = getDemoProperty(caseId);
  const updatedFields = current.fields.map((f: any) => {
    if (updates[f.field] !== undefined) {
      return { ...f, value: updates[f.field], verification: "USER_PROVIDED" };
    }
    return f;
  });

  for (const [key, val] of Object.entries(updates)) {
    if (!updatedFields.some((f: any) => f.field === key)) {
      updatedFields.push({ field: key, value: val, verification: "USER_PROVIDED" });
    }
  }

  const result = { fields: updatedFields };
  setStorage(`property_${caseId}`, result);
  return result;
}

export function getDemoPropertyEntities(caseId: string) {
  const ctx = getContext(caseId);
  const isTax = detectDomain(ctx) === "TAX" || ctx.caseName.toLowerCase().includes("vodafone");
  const doc = ctx.documentNames[0] || (isTax ? "10765_2016_12_1501_36337_Judgement_14-Jul-2022.pdf" : "sale_deed_1987.pdf");

  if (isTax) {
    return {
      name: [{ document: doc, page: 1, source_text: "Acquisition of 100% share capital of CGP Investments (Holdings) Ltd" }],
      registration_number: [{ document: doc, page: 1, source_text: "Cayman Islands Reg No. 124988" }],
      address: [{ document: doc, page: 1, source_text: "P.O. Box 309, George Town, Grand Cayman, Cayman Islands" }],
      description: [{ document: doc, page: 2, source_text: "100% share capital of CGP Investments (Holdings) Ltd conferring 67% equity in Hutchison Essar Limited" }],
      state: [{ document: doc, page: 1, source_text: "Cayman Islands & Indian Telecommunication Jurisdiction" }],
      district: [{ document: doc, page: 2, source_text: "Offshore Cayman Islands / Mumbai Operating Nexus" }],
      khata_number: [{ document: doc, page: 1, source_text: "PAN: AABCV1290K (Non-Resident Corporation)" }],
    };
  }

  return {
    name: [{ document: "sale_deed_1987.pdf", page: 1, source_text: "Absolute Sale Deed dated 14th July 1987" }],
    survey_number: [{ document: "sale_deed_1987.pdf", page: 2, source_text: "bearing Survey No. 124/3" }],
    village: [{ document: "sale_deed_1987.pdf", page: 2, source_text: "situated at Whitefield Village" }],
    registration_number: [{ document: "sale_deed_1987.pdf", page: 1, source_text: "Doc No: BNG-U/4521/1987-88" }],
    address: [{ document: "sale_deed_1987.pdf", page: 2, source_text: "Whitefield Village, K.R. Puram Hobli, Bengaluru East Taluk" }],
  };
}

export function getDemoOwnership(caseId: string) {
  const ctx = getContext(caseId);
  return generateOwnershipGraph(ctx);
}

export function getDemoTimeline(caseId: string) {
  const ctx = getContext(caseId);
  return generateTimeline(ctx);
}

export function getDemoComparison(caseId: string) {
  const ctx = getContext(caseId);
  const isTax = detectDomain(ctx) === "TAX";

  if (isTax) {
    return [
      {
        id: "cmp-1",
        field_name: "statutory_jurisdiction_assessment",
        verdict: "MISMATCH",
        explanation: "High Court of Bombay held offshore transfer was taxable in India; Supreme Court reversed and held no extra-territorial tax jurisdiction existed.",
        values: [
          {
            document_name: "bombay_high_court_order.pdf",
            page_number: 12,
            value: "Taxable under Section 9(1)(i) due to underlying economic nexus",
            source_text: "…transfer of CGP share is composite transaction with nexus to Indian operating assets…",
          },
          {
            document_name: "39003.pdf",
            page_number: 5,
            value: "Not Taxable in India under Section 9(1)(i) / Section 195",
            source_text: "…Held: Indian tax authorities had no territorial jurisdiction; demand of Rs. 11,000 Crores is quashed…",
          },
        ],
      },
      {
        id: "cmp-2",
        field_name: "transaction_consideration",
        verdict: "MATCH",
        explanation: "Both documents record exact purchase price of USD $11.1 Billion for 100% shareholding in CGP Investments.",
        values: [
          {
            document_name: "39003.pdf",
            page_number: 1,
            value: "USD $11.1 Billion",
            source_text: "…cash consideration of USD 11.1 Billion…",
          },
          {
            document_name: "share_purchase_agreement_2007.pdf",
            page_number: 4,
            value: "USD $11.1 Billion",
            source_text: "…total aggregate consideration of USD 11,100,000,000…",
          },
        ],
      },
    ];
  }

  return [
    {
      id: "cmp-1",
      field_name: "survey_number",
      verdict: "MISMATCH",
      explanation: "Sale Deed 1987 references Sy. No. 124/3, whereas Partition Deed 2004 references Sy. No. 124/2 in Schedule A.",
      values: [
        {
          document_name: "sale_deed_1987.pdf",
          page_number: 2,
          value: "124/3",
          source_text: "…Survey No. 124/3 situated in Whitefield Village…",
        },
        {
          document_name: "partition_deed_2004.pdf",
          page_number: 2,
          value: "124/2",
          source_text: "…ಸರ್ವೆ ನಂ. 124/2 ರ ಪೈಕಿ ಪೂರ್ವ ಭಾಗದ 1 ಎಕರೆ 7 ಗುಂಟೆ…",
        },
      ],
    },
  ];
}

export function getDemoRisks(caseId: string): DemoRisk[] {
  const ctx = getContext(caseId);
  const risksMap = getStorage<Record<string, DemoRisk[]>>("risks", {});
  if (!risksMap[caseId]) {
    risksMap[caseId] = generateRisks(ctx);
    setStorage("risks", risksMap);
  }
  return risksMap[caseId];
}

export function updateDemoRisk(riskId: string, resolved: boolean): void {
  const risksMap = getStorage<Record<string, DemoRisk[]>>("risks", {});
  for (const cid of Object.keys(risksMap)) {
    const list = risksMap[cid];
    const target = list.find((r) => r.id === riskId);
    if (target) {
      target.resolved = resolved;
      setStorage("risks", risksMap);
      break;
    }
  }
}

export function listDemoResearch(caseId: string) {
  const ctx = getContext(caseId);
  const isTax = detectDomain(ctx) === "TAX";

  const defaultResearch = isTax
    ? [
        {
          id: "res-1",
          case_id: caseId,
          question: "What is the legal effect of Section 9(1)(i) and Section 195 regarding offshore indirect transfers in India?",
          status: "COMPLETED",
          jurisdiction: "Supreme Court of India",
          answer: `### Legal Research: Section 9(1)(i) & Section 195 Withholding Tax

1. **Supreme Court Precedent ((2012) 6 SCC 613)**:
   The Supreme Court held that Section 9(1)(i) does not have extra-territorial look-through effect. Transfer of shares of a foreign offshore company does not constitute transfer of a capital asset situated in India.

2. **Withholding Tax under Section 195**:
   Section 195 applies only to payments containing income chargeable to tax under the Indian Income Tax Act. Where income is not chargeable u/s 9, no withholding liability arises (GE India Technology, (2010) 10 SCC 29).

3. **Current Status**:
   Retrospective tax demands under Finance Act 2012 were repealed by the Taxation Laws (Amendment) Act 2021 following international BIT arbitration awards [Source: https://indiankanoon.org/doc/1158524/].`,
          created_at: new Date(Date.now() - 86400000).toISOString(),
        },
      ]
    : [
        {
          id: "res-1",
          case_id: caseId,
          question: "What is the legal effect of a survey number mismatch between a Sale Deed and Partition Deed in Karnataka?",
          status: "COMPLETED",
          jurisdiction: "Karnataka",
          answer: "Under Indian property law, where there is a discrepancy between the Survey Number and the specific Schedule Boundaries in a registered conveyance deed, the settled legal position is that **Boundaries Prevail Over Survey Numbers / Dimensions** (Subhaga & Ors v. Shobha Rani & Ors, Supreme Court of India). [Source: https://indiankanoon.org/doc/1498114/].",
          created_at: new Date(Date.now() - 86400000).toISOString(),
        },
      ];

  const research = getStorage<any[]>(`research_${caseId}`, defaultResearch);
  return research;
}

export async function startDemoResearch(caseId: string, question: string, jurisdiction = "India", language = "en", model?: string) {
  const ctx = getContext(caseId);
  const research = listDemoResearch(caseId);
  const newSession = await generateLegalResearch(ctx, question, jurisdiction, language, model);
  research.unshift(newSession);
  setStorage(`research_${caseId}`, research);
  return newSession;
}

export function getDemoResearchSources(sessionId: string) {
  return [
    { id: "src-1", title: "Supreme Court Judgment in Vodafone v. Union of India ((2012) 6 SCC 613)", url: "https://indiankanoon.org/doc/1158524/", verified: true },
    { id: "src-2", title: "Section 9(1) in The Income-Tax Act, 1961", url: "https://indiankanoon.org/doc/178294/", verified: true },
    { id: "src-3", title: "Section 195 in The Income-Tax Act, 1961", url: "https://indiankanoon.org/doc/1183350/", verified: true },
  ];
}

export function getDemoChatHistory(caseId: string) {
  const ctx = getContext(caseId);
  const isTax = detectDomain(ctx) === "TAX";

  const defaultChat = [
    {
      id: "msg-1",
      role: "assistant",
      content: isTax
        ? `Hello! I am your Jurisiva Legal Intelligence Assistant. I have indexed the case files and Supreme Court records for **${ctx.caseName}**. Ask me any question regarding Section 9(1)(i), Section 195 withholding tax, offshore holding structures, or transaction facts.`
        : `Hello! I am your Jurisiva Legal Assistant. I have indexed the documents in **${ctx.caseName}**. Ask me anything regarding title history, parties, survey numbers, or risks.`,
      created_at: new Date(Date.now() - 86400000).toISOString(),
    },
  ];

  return getStorage<any[]>(`chat_${caseId}`, defaultChat);
}

export async function askDemoQuestion(caseId: string, question: string, language = "en", model?: string) {
  const ctx = getContext(caseId);
  const history = getDemoChatHistory(caseId);

  const answer = await generateLegalAnswer(ctx, question, language, model);

  const userMsg = { id: `msg-${Date.now()}-user`, role: "user", content: question, created_at: new Date().toISOString() };
  const botMsg = { id: `msg-${Date.now()}-bot`, role: "assistant", content: answer.content, citations: answer.citations, created_at: new Date().toISOString() };

  history.push(userMsg, botMsg);
  setStorage(`chat_${caseId}`, history);
  return botMsg;
}

export function listDemoDrafts(caseId: string) {
  const ctx = getContext(caseId);
  const isTax = detectDomain(ctx) === "TAX";

  const defaultDrafts = isTax
    ? [
        {
          id: "draft-1",
          case_id: caseId,
          draft_type: "application",
          title: "Writ Petition under Article 226 — Quashing of Section 201 Notice",
          version: 1,
          status: "REVIEW",
          content: generateLegalDraft(ctx, "application", "Writ Petition under Article 226", "Challenge Section 201 withholding tax demand on offshore CGP share purchase").content,
          created_at: new Date(Date.now() - 86400000).toISOString(),
          updated_at: new Date(Date.now() - 86400000).toISOString(),
        },
      ]
    : [
        {
          id: "draft-1",
          case_id: caseId,
          draft_type: "legal_notice",
          title: "Legal Notice for Title Verification & Survey Demarcation",
          version: 1,
          status: "REVIEW",
          content: generateLegalDraft(ctx, "legal_notice", "Legal Notice for Title Verification", "Joint survey measurement request to ADLR").content,
          created_at: new Date(Date.now() - 86400000).toISOString(),
          updated_at: new Date(Date.now() - 86400000).toISOString(),
        },
      ];

  return getStorage<any[]>(`drafts_${caseId}`, defaultDrafts);
}

export function createDemoDraft(caseId: string, body: { draft_type: string; title: string; instructions: string }) {
  const ctx = getContext(caseId);
  const drafts = listDemoDrafts(caseId);
  const newDraft = generateLegalDraft(ctx, body.draft_type, body.title, body.instructions);
  drafts.unshift(newDraft);
  setStorage(`drafts_${caseId}`, drafts);
  return newDraft;
}

export function updateDemoDraft(draftId: string, updates: any) {
  if (typeof window === "undefined") return { id: draftId, ...updates };
  const allDraftKeys = Object.keys(localStorage).filter((k) => k.startsWith(STORAGE_PREFIX + "drafts_"));
  for (const k of allDraftKeys) {
    const list = getStorage<any[]>(k.replace(STORAGE_PREFIX, ""), []);
    const target = list.find((d) => d.id === draftId);
    if (target) {
      Object.assign(target, updates, { updated_at: new Date().toISOString() });
      setStorage(k.replace(STORAGE_PREFIX, ""), list);
      return target;
    }
  }
  return { id: draftId, ...updates, updated_at: new Date().toISOString() };
}

export function deleteDemoDraft(draftId: string) {
  if (typeof window === "undefined") return;
  const allDraftKeys = Object.keys(localStorage).filter((k) => k.startsWith(STORAGE_PREFIX + "drafts_"));
  for (const k of allDraftKeys) {
    const rawKey = k.replace(STORAGE_PREFIX, "");
    let list = getStorage<any[]>(rawKey, []);
    list = list.filter((d) => d.id !== draftId);
    setStorage(rawKey, list);
  }
}

export function listDemoReports(caseId: string) {
  const ctx = getContext(caseId);
  const defaultReport = generateLegalReport(ctx);
  const raw = getStorage<any[]>(`reports_${caseId}`, [defaultReport]);

  // Ensure unique reports and IDs
  const seen = new Set<string>();
  const uniqueList: any[] = [];
  for (let i = 0; i < raw.length; i++) {
    const item = raw[i];
    let rid = item.id;
    if (!rid || seen.has(rid)) {
      rid = `rep-${Date.now()}-${Math.random().toString(36).slice(2, 8)}-${i}`;
      item.id = rid;
    }
    seen.add(rid);
    uniqueList.push(item);
  }

  return uniqueList;
}

export function generateDemoReport(caseId: string) {
  const ctx = getContext(caseId);
  const reports = listDemoReports(caseId);
  const newReport = generateLegalReport(ctx);
  reports.unshift(newReport);
  setStorage(`reports_${caseId}`, reports);
  return newReport;
}

export function getDemoJobs(caseId: string) {
  return [
    { id: "job-1", job_type: "OCR", state: "COMPLETED", progress: 100, document_id: "doc-1", error_message: null, updated_at: new Date().toISOString() },
    { id: "job-2", job_type: "EXTRACTION", state: "COMPLETED", progress: 100, document_id: "doc-1", error_message: null, updated_at: new Date().toISOString() },
  ];
}

export function getDemoBilling() {
  return {
    plan: { name: "Enterprise Law Practice" },
    status: "ACTIVE",
    period: { start: new Date(Date.now() - 15 * 86400000).toISOString(), end: new Date(Date.now() + 15 * 86400000).toISOString() },
    usage: { pages: 142, ai_runs: 88, cases: 6 },
    limits: { pages_per_month: 2500, ai_runs_per_month: 1000, cases: 50 },
  };
}

export function getDemoMembers() {
  return [
    { id: "mem-1", user_id: "u-1", email: "demo@example.com", full_name: "Demo Counsel", role: "OWNER", created_at: new Date(Date.now() - 30 * 86400000).toISOString() },
    { id: "mem-2", user_id: "u-2", email: "partner@firm.com", full_name: "Senior Partner", role: "ADMIN", created_at: new Date(Date.now() - 20 * 86400000).toISOString() },
  ];
}
