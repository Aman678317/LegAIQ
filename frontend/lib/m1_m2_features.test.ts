import { describe, it, expect, vi, beforeEach } from "vitest";

const mockLocalStorage = {
  store: {} as Record<string, string>,
  getItem(key: string) {
    return this.store[key] || null;
  },
  setItem(key: string, value: string) {
    this.store[key] = value;
  },
  removeItem(key: string) {
    delete this.store[key];
  },
  clear() {
    this.store = {};
  },
};

vi.stubGlobal("localStorage", mockLocalStorage);

describe("Milestone 1 (R1): Assistant & Chat Workspace", () => {
  beforeEach(() => {
    mockLocalStorage.clear();
  });

  it("handles 3 modes (ask, analyze, draft) in mockStore", async () => {
    const mockStore = await import("./mockStore");
    const caseId = "test-case-m1";
    mockStore.getOrCreateDemoCase(caseId);

    // Ask mode
    const askRes = await mockStore.askDemoQuestion(caseId, "Who is the title holder?", "en", "claude-3-5-sonnet");
    expect(askRes.role).toBe("assistant");
    expect(askRes.content).toBeTruthy();
    expect(askRes.citations).toBeDefined();

    // Analyze mode
    const analyzeRes = await mockStore.askDemoQuestion(caseId, "Analyze boundary discrepancy in deed", "en", "gpt-4o");
    expect(analyzeRes.role).toBe("assistant");
    expect(analyzeRes.content).toBeTruthy();

    // Draft mode
    const draftRes = await mockStore.askDemoQuestion(caseId, "Draft legal notice for possession", "en", "deepseek-r1");
    expect(draftRes.role).toBe("assistant");
    expect(draftRes.content).toBeTruthy();
  });

  it("correctly extracts inline citations from text with [Doc: name, Pg: N]", () => {
    const text = "As recorded in [Doc: Sale_Deed_1987.pdf, Pg: 2], the schedule property measures 2 Acres 14 Guntas.";
    const regex = /\[Doc:\s*([^,\]]+),\s*(?:Pg|Page):\s*([0-9]+)\]/gi;
    const match = regex.exec(text);

    expect(match).not.toBeNull();
    expect(match![1]).toBe("Sale_Deed_1987.pdf");
    expect(match![2]).toBe("2");
  });
});

describe("Milestone 2 (R2): Secure Matter Vault & Indic Document Intelligence", () => {
  beforeEach(() => {
    mockLocalStorage.clear();
  });

  it("handles side-by-side direct document comparison", async () => {
    const mockStore = await import("./mockStore");
    const caseId = "test-case-m2";
    mockStore.getOrCreateDemoCase(caseId);

    const diff = mockStore.compareDemoDocumentsDirect(caseId, ["doc-1", "doc-2"]);
    expect(diff.case_id).toBe(caseId);
    expect(diff.doc_a).toBeDefined();
    expect(diff.doc_b).toBeDefined();
    expect(diff.diff_chunks.length).toBeGreaterThan(0);
    expect(diff.field_comparisons.length).toBeGreaterThan(0);

    const surveyComp = diff.field_comparisons.find((f: any) => f.field_name === "survey_number");
    expect(surveyComp).toBeDefined();
    expect(surveyComp?.verdict).toBe("MISMATCH");
  });
});
