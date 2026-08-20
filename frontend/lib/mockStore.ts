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
  document_type?: string;
  badge_label?: string;
  badge_color?: string;
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

function createDefaultCaseData(caseId: string, name?: string): DemoCase {
  const caseName = name || (caseId.toLowerCase().includes("vodafone") ? "Vodafone International Holdings B.V. v. Union of India" : "Whitefield Property Dispute & Title Investigation");
  const isVodafone = caseName.toLowerCase().includes("vodafone") || caseId.toLowerCase().includes("vodafone");
  return {
    id: caseId,
    name: isVodafone ? "Vodafone International Holdings B.V. v. Union of India" : caseName,
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

  const stored = forceRefresh ? null : getStorage<Record<string, any> | null>(`property_${caseId}`, null);

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

export function compareDemoDocumentsDirect(caseId: string, documentIds: string[]) {
  const ctx = getContext(caseId);
  const comparisonResults = getDemoComparison(caseId);
  const docA = ctx.documentNames[0] || "sale_deed_1987.pdf";
  const docB = ctx.documentNames[1] || "partition_deed_2004.pdf";

  return {
    case_id: caseId,
    doc_a: { id: documentIds[0] || "doc-1", name: docA },
    doc_b: { id: documentIds[1] || "doc-2", name: docB },
    field_comparisons: comparisonResults,
    diff_chunks: [
      { type: "equal", text_a: "THIS SALE DEED is executed on this 12th day of March 1987 at Bengaluru.", text_b: "THIS PARTITION DEED is executed on this 15th day of June 2004 at Bengaluru." },
      { type: "replace", text_a: "Venkatarama Reddy S/o Late Krishnappa", text_b: "Venkatarama Reddy and Legal Heirs" },
      { type: "delete", text_a: "absolute sale for Rs. 45,000 consideration", text_b: "" },
      { type: "insert", text_a: "", text_b: "partition among coparceners with Schedule A & B allotments" },
      { type: "equal", text_a: "Survey Number 124/3 situated at Whitefield Village", text_b: "Survey Number 124/2 situated at Whitefield Village" },
    ],
  };
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

export async function askDemoQuestion(
  caseId: string,
  question: string,
  language = "en",
  model?: string,
  onChunk?: (chunk: string) => void,
  options?: { mode?: string; india_context?: boolean; document_ids?: string[] }
) {
  const ctx = getContext(caseId);
  const history = getDemoChatHistory(caseId);

  const answer = await generateLegalAnswer(ctx, question, language, model);

  if (onChunk && answer.content) {
    const words = answer.content.split(" ");
    for (let i = 0; i < words.length; i += 4) {
      const chunk = words.slice(i, i + 4).join(" ") + (i + 4 < words.length ? " " : "");
      onChunk(chunk);
      await new Promise((resolve) => setTimeout(resolve, 15));
    }
  }

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

// --- Milestone 3: Review Tables Demo Store ---

export function listDemoReviewTables(caseId: string) {
  const defaultTables = [
    {
      id: `rt-${caseId}-1`,
      case_id: caseId,
      name: "Due Diligence Master Review Grid",
      description: "Structured legal prompts extracted across all matter documents.",
      column_count: 5,
      created_at: new Date(Date.now() - 5 * 86400000).toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: `rt-${caseId}-2`,
      case_id: caseId,
      name: "Lease Deed Term & Liability Audit",
      description: "Commercial lease terms, notice periods, and indemnity caps.",
      column_count: 4,
      created_at: new Date(Date.now() - 2 * 86400000).toISOString(),
      updated_at: new Date().toISOString(),
    },
  ];
  return getStorage<any[]>(`review_tables_${caseId}`, defaultTables);
}

export function getDemoReviewTable(caseId: string, tableId: string) {
  const tables = listDemoReviewTables(caseId);
  const table = tables.find((t) => t.id === tableId) || tables[0] || {
    id: tableId,
    case_id: caseId,
    name: "Review Table",
    description: "Spreadsheet Extraction Grid",
  };

  const columns = [
    { id: "col-1", table_id: tableId, name: "Governing Law", column_type: "prompt", prompt: "What is the governing law?", position: 0 },
    { id: "col-2", table_id: tableId, name: "Jurisdiction & Seat", column_type: "prompt", prompt: "Which court has jurisdiction?", position: 1 },
    { id: "col-3", table_id: tableId, name: "Indemnity Cap", column_type: "prompt", prompt: "Is indemnity capped?", position: 2 },
    { id: "col-4", table_id: tableId, name: "Termination Notice", column_type: "prompt", prompt: "What is the notice period?", position: 3 },
    { id: "col-5", table_id: tableId, name: "Stamp Duty Paid", column_type: "prompt", prompt: "What stamp duty is paid?", position: 4 },
  ];

  const docs = listDemoDocuments(caseId);
  const rows = docs.map((doc, idx) => ({
    document_id: doc.id,
    document_name: doc.file_name,
    document_type: doc.document_type || "Legal Deed",
    status: doc.status || "COMPLETED",
    cells: {
      "col-1": {
        id: `cell-${doc.id}-1`,
        value: "Laws of India (Substantive)",
        confidence_score: 0.94,
        status: "completed",
        evidence: {
          doc_id: doc.id,
          doc_name: doc.file_name,
          page_num: 1,
          text_snippet: "This Agreement shall be governed by and construed in accordance with the substantive laws of India.",
          bbox: [0.15, 0.1, 0.25, 0.9],
        },
      },
      "col-2": {
        id: `cell-${doc.id}-2`,
        value: "Bengaluru Courts & MCIA Arbitration",
        confidence_score: 0.89,
        status: "completed",
        evidence: {
          doc_id: doc.id,
          doc_name: doc.file_name,
          page_num: 2,
          text_snippet: "Courts at Bengaluru shall have exclusive jurisdiction. Arbitration seat: Bengaluru.",
          bbox: [0.2, 0.1, 0.3, 0.85],
        },
      },
      "col-3": {
        id: `cell-${doc.id}-3`,
        value: idx % 2 === 0 ? "Capped at 1x 12-Month Fees" : "UNLIMITED (High Risk Flag)",
        confidence_score: idx % 2 === 0 ? 0.91 : 0.72,
        status: "completed",
        evidence: {
          doc_id: doc.id,
          doc_name: doc.file_name,
          page_num: 3,
          text_snippet: idx % 2 === 0 ? "The aggregate liability under this indemnity shall not exceed 100% of the total fees paid in preceding 12 months." : "Vendor provides unlimited indemnity and holds harmless for any and all losses.",
          bbox: [0.4, 0.1, 0.5, 0.9],
        },
      },
      "col-4": {
        id: `cell-${doc.id}-4`,
        value: "30 Days Written Notice",
        confidence_score: 0.96,
        status: "completed",
        evidence: {
          doc_id: doc.id,
          doc_name: doc.file_name,
          page_num: 2,
          text_snippet: "Either party may terminate this Agreement by giving 30 days prior written notice.",
          bbox: [0.6, 0.1, 0.7, 0.9],
        },
      },
      "col-5": {
        id: `cell-${doc.id}-5`,
        value: "Rs. 75,000 (Karnataka Stamp Act)",
        confidence_score: 0.88,
        status: "completed",
        evidence: {
          doc_id: doc.id,
          doc_name: doc.file_name,
          page_num: 1,
          text_snippet: "Duly stamped with stamp duty of Rs. 75,000 before the Sub-Registrar.",
          bbox: [0.05, 0.1, 0.15, 0.9],
        },
      },
    },
  }));

  return {
    ...table,
    columns,
    rows,
    total_documents: rows.length,
  };
}

export function createDemoReviewTable(caseId: string, body: any) {
  const tables = listDemoReviewTables(caseId);
  const newTable = {
    id: `rt-${Date.now()}`,
    case_id: caseId,
    name: body.name || "New Review Table",
    description: body.description || "",
    column_count: body.columns?.length || 5,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  tables.unshift(newTable);
  setStorage(`review_tables_${caseId}`, tables);
  return newTable;
}

// --- Milestone 5: Clause Library & Playbooks Demo Store ---

export const DEMO_CLAUSE_LIBRARY = [
  {
    clause_id: "LIB-INDEM-001",
    clause_type: "indemnity",
    title: "Mutual Indemnification with Cap",
    category: "Commercial",
    standard_language: "Each party agrees to defend and indemnify the other against direct third-party claims arising from gross negligence or IP infringement, capped at 12 months fees.",
    fallback_tier_1: "Indemnity for direct damages only, capped at 2x contract value.",
    fallback_tier_2: "Indemnity capped at proceeds of commercial insurance.",
    walkaway_language: "WALKAWAY: Reject uncapped indemnities or indemnities extending to consequential damages.",
    guidance_notes: "Sections 124 & 125 of Indian Contract Act 1872 require express conduct linkage.",
    statutory_reference: "Indian Contract Act, 1872 §124, §125",
    tags: ["indemnity", "liability", "commercial"],
  },
  {
    clause_id: "LIB-NONCOMP-001",
    clause_type: "non_compete",
    title: "Enforceable Restrictive Covenant & Section 27 Compliance",
    category: "Employment & Services",
    standard_language: "During the term only, Service Provider shall not compete with Client. Post-termination restrictions are explicitly excluded per Section 27 Indian Contract Act.",
    fallback_tier_1: "In-term non-compete with 6-month post-termination non-solicitation of active personnel.",
    fallback_tier_2: "12-month non-solicitation of clients with whom direct interaction occurred.",
    walkaway_language: "WALKAWAY: Post-termination non-competes are void ab initio in India (Percept D'Mark v. Zaheer Khan).",
    guidance_notes: "Section 27 voidness is absolute under Indian jurisprudence.",
    statutory_reference: "Indian Contract Act, 1872 Section 27 (§27); Percept D'Mark (2006)",
    tags: ["non-compete", "section-27", "restraint-of-trade"],
  },
  {
    clause_id: "LIB-GOVLAW-001",
    clause_type: "governing_law",
    title: "Governing Law & Institutional Arbitration (India)",
    category: "Dispute Resolution",
    standard_language: "Governed by laws of India. Arbitration administered by MCIA or DIAC in Mumbai/Bengaluru under Arbitration Act 1996.",
    fallback_tier_1: "Sole arbitrator appointed under Arbitration and Conciliation Act 1996 in New Delhi.",
    fallback_tier_2: "3-arbitrator panel with 30-day executive mediation period.",
    walkaway_language: "WALKAWAY: Reject unilateral appointment of arbitrator (Perkins Eastman violation).",
    guidance_notes: "Seat determines exclusive supervisory court jurisdiction.",
    statutory_reference: "Arbitration and Conciliation Act, 1996 §7, §12(5)",
    tags: ["arbitration", "governing-law", "dispute-resolution"],
  },
  {
    clause_id: "LIB-DPDP-001",
    clause_type: "data_protection",
    title: "Digital Personal Data Protection (DPDP Act 2023)",
    category: "Privacy & Compliance",
    standard_language: "Compliance with DPDP Act 2023, data processor terms, purpose limitation, and 24-hour data breach notification.",
    fallback_tier_1: "DPDP compliance with 48-hour breach notification.",
    fallback_tier_2: "Standard data processing with annual SOC2 summary.",
    walkaway_language: "WALKAWAY: Unrestricted processing of biometric/Aadhaar data without consent.",
    guidance_notes: "Penalties up to INR 250 Crores under DPDP Act 2023 for data breaches.",
    statutory_reference: "DPDP Act, 2023 §6, §8",
    tags: ["dpdp-act", "data-privacy", "personal-data"],
  },
];

export const DEMO_PLAYBOOKS = [
  {
    playbook_id: "PB-MSA-001",
    name: "Enterprise Master Services Agreement (MSA) Playbook",
    description: "Firm standard negotiation guidelines for B2B IT, SaaS, and Professional Services contracts in India.",
    contract_type: "master_services_agreement",
    rules_count: 6,
  },
  {
    playbook_id: "PB-EMPLOY-001",
    name: "Employment & Executive Services (India §27 ICA Compliant)",
    description: "Indian employment contracts ensuring strict compliance with Section 27 and BSA 2023.",
    contract_type: "employment_agreement",
    rules_count: 4,
  },
  {
    playbook_id: "PB-LEASE-001",
    name: "Commercial Real Estate Lease Deed Playbook",
    description: "Playbook for commercial leases and licenses under Indian State Stamp Acts & Registration Act.",
    contract_type: "lease_deed",
    rules_count: 5,
  },
];

export function evaluateDemoPlaybook(caseId: string, body: any) {
  const isMSA = (body.playbook_id || "").includes("MSA");
  const isEmployment = (body.playbook_id || "").includes("EMPLOY");

  return {
    contract_id: body.contract_id || "demo-contract",
    playbook_id: body.playbook_id || "PB-MSA-001",
    playbook_name: isEmployment ? "Employment Agreement Playbook" : "Enterprise MSA Playbook",
    compliance_score: isEmployment ? 55.0 : 78.5,
    overall_status: isEmployment ? "walkaway_triggered" : "minor_deviations",
    total_rules_evaluated: 6,
    passed_rules: isEmployment ? 3 : 4,
    deviations: isEmployment
      ? [
          {
            deviation_id: "DEV-001",
            rule_id: "RULE-EMP-NONCOMP",
            clause_type: "non_compete",
            severity: "critical",
            deviation_type: "statutory_violation",
            current_text: "Employee shall not compete for 1 year following termination in India.",
            issue_description: "CRITICAL STATUTORY VIOLATION: Post-termination non-compete is void ab initio under Section 27 Indian Contract Act 1872.",
            recommended_redline: "Employee shall not engage in competing business during the active term of employment only. No post-termination restraint applies per Section 27 ICA.",
            statutory_reference: "Indian Contract Act, 1872 Section 27 (§27); Percept D'Mark (2006)",
          },
        ]
      : [
          {
            deviation_id: "DEV-002",
            rule_id: "RULE-MSA-INDEM",
            clause_type: "indemnity",
            severity: "high",
            deviation_type: "forbidden_term_detected",
            current_text: "Developer provides unlimited indemnity against all claims.",
            issue_description: "Forbidden terms: 'unlimited indemnity'. Playbook mandates 12-month fee cap.",
            recommended_redline: "Indemnity capped at total fees paid in preceding 12 months for direct damages.",
            statutory_reference: "Indian Contract Act, 1872 §73, §124",
          },
        ],
    redline_recommendations: [
      {
        action: "replace",
        clause_type: isEmployment ? "non_compete" : "indemnity",
        suggested_text: isEmployment
          ? "In accordance with Section 27 of the Indian Contract Act, 1872, no post-termination restraint on trade shall apply."
          : "Each party's total liability under this indemnity shall not exceed 100% of fees paid in preceding 12 months.",
        rationale: "Align with firm standard playbook risk controls and Indian statutes.",
      },
    ],
  };
}

export function getDemoContractHeatmap(caseId: string) {
  return {
    contract_id: "demo-contract",
    overall_score: 58.0,
    overall_risk: "medium",
    categories: {
      "Liability & Indemnity": {
        score: 75.0,
        highest_risk: "high",
        clause_count: 2,
        clauses: [
          { clause_id: "CL-002", title: "Indemnification", type: "indemnity", risk_level: "high", risk_factors: ["High: broad indemnity"] },
          { clause_id: "CL-003", title: "Limitation of Liability", type: "limitation_of_liability", risk_level: "medium", risk_factors: ["Medium: consequential damages"] },
        ],
      },
      "Commercial & Term": {
        score: 35.0,
        highest_risk: "medium",
        clause_count: 3,
        clauses: [
          { clause_id: "CL-004", title: "Termination", type: "termination", risk_level: "medium", risk_factors: ["Medium: termination notice"] },
          { clause_id: "CL-001", title: "Parties", type: "parties", risk_level: "negligible", risk_factors: [] },
        ],
      },
      "Restrictive Covenants": {
        score: 95.0,
        highest_risk: "critical",
        clause_count: 1,
        clauses: [
          { clause_id: "CL-006", title: "Non-Compete", type: "non_compete", risk_level: "critical", risk_factors: ["Critical: Section 27 ICA void post-termination non-compete"] },
        ],
      },
      "Compliance & Statutory": {
        score: 40.0,
        highest_risk: "medium",
        clause_count: 2,
        clauses: [
          { clause_id: "CL-007", title: "Stamp Duty", type: "stamp_duty", risk_level: "medium", risk_factors: ["Medium: stamp duty compliance"] },
        ],
      },
      "Dispute & Governance": {
        score: 20.0,
        highest_risk: "low",
        clause_count: 1,
        clauses: [
          { clause_id: "CL-005", title: "Governing Law", type: "governing_law", risk_level: "low", risk_factors: [] },
        ],
      },
    },
  };
}
