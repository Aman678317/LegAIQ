import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock localStorage
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

// We need to test the mockStore functions
// Since the module uses localStorage directly, we'll test the behavior

describe("mockStore", () => {
  beforeEach(() => {
    mockLocalStorage.clear();
  });

  it("should be importable", async () => {
    const mockStore = await import("./mockStore");
    expect(mockStore).toBeDefined();
  });

  it("should have required exports", async () => {
    const mockStore = await import("./mockStore");
    expect(typeof mockStore.getOrCreateDemoCase).toBe("function");
    expect(typeof mockStore.listDemoCases).toBe("function");
    expect(typeof mockStore.listDemoDocuments).toBe("function");
    expect(typeof mockStore.getDemoRisks).toBe("function");
    expect(typeof mockStore.getDemoTimeline).toBe("function");
  });
});

describe("mockStore localStorage integration", () => {
  beforeEach(() => {
    mockLocalStorage.clear();
  });

  it("persists cases to localStorage", async () => {
    const mockStore = await import("./mockStore");
    
    const case1 = mockStore.getOrCreateDemoCase("demo-case-1");
    expect(case1.id).toBe("demo-case-1");
    
    const stored = localStorage.getItem("jurisiva_demo_cases");
    expect(stored).toBeTruthy();
    
    const parsed = JSON.parse(stored!);
    expect(parsed["demo-case-1"]).toBeDefined();
    expect(parsed["demo-case-1"].id).toBe("demo-case-1");
  });

  it("persists documents to localStorage", async () => {
    const mockStore = await import("./mockStore");
    
    const case1 = mockStore.getOrCreateDemoCase("demo-case-2");
    // Use uploadDemoDocument (the actual exported function) instead of addDemoDocument
    const file = new File(["test content"], "test.pdf", { type: "application/pdf" });
    const doc = mockStore.uploadDemoDocument(case1.id, file);
    
    expect(doc.id).toBeDefined();
    expect(doc.case_id).toBe(case1.id);
    
    const stored = localStorage.getItem("jurisiva_demo_documents");
    expect(stored).toBeTruthy();
  });

  it("lists cases from localStorage", async () => {
    const mockStore = await import("./mockStore");
    
    mockStore.getOrCreateDemoCase("demo-case-3");
    mockStore.getOrCreateDemoCase("demo-case-4");
    
    const cases = mockStore.listDemoCases("demo-org");
    // listDemoCases returns { items: DemoCase[], total: number }
    expect(cases.items.length).toBeGreaterThanOrEqual(2);
    expect(cases.items.find(c => c.id === "demo-case-3")).toBeDefined();
    expect(cases.items.find(c => c.id === "demo-case-4")).toBeDefined();
  });

  it("lists documents for a case", async () => {
    const mockStore = await import("./mockStore");
    
    const case1 = mockStore.getOrCreateDemoCase("demo-case-5");
    const file1 = new File(["test content 1"], "doc1.pdf", { type: "application/pdf" });
    const file2 = new File(["test content 2"], "doc2.pdf", { type: "application/pdf" });
    mockStore.uploadDemoDocument(case1.id, file1);
    mockStore.uploadDemoDocument(case1.id, file2);
    
    const docs = mockStore.listDemoDocuments(case1.id);
    // Includes 3 default documents + 2 uploaded = 5
    expect(docs.length).toBe(5);
  });

  it("manages demo review tables and columns", async () => {
    const mockStore = await import("./mockStore");
    const tables = mockStore.listDemoReviewTables("demo-case-rt");
    expect(tables.length).toBeGreaterThanOrEqual(1);

    const fullTable = mockStore.getDemoReviewTable("demo-case-rt", tables[0].id);
    expect(fullTable.columns.length).toBeGreaterThanOrEqual(4);
    expect(fullTable.rows.length).toBeGreaterThanOrEqual(1);
    expect(fullTable.rows[0].cells["col-1"]).toBeDefined();
    expect(fullTable.rows[0].cells["col-1"].confidence_score).toBeGreaterThan(0.8);
  });

  it("provides clause library and evaluates contract playbooks", async () => {
    const mockStore = await import("./mockStore");
    expect(mockStore.DEMO_CLAUSE_LIBRARY.length).toBeGreaterThanOrEqual(4);
    expect(mockStore.DEMO_PLAYBOOKS.length).toBeGreaterThanOrEqual(3);

    // Evaluate Employment Playbook
    const empResult = mockStore.evaluateDemoPlaybook("demo-case-pb", {
      playbook_id: "PB-EMPLOY-001",
      full_text: "Non-compete post termination 1 year.",
    });
    expect(empResult.overall_status).toBe("walkaway_triggered");
    expect(empResult.deviations.length).toBeGreaterThanOrEqual(1);
    expect(empResult.deviations[0].statutory_reference).toContain("Section 27");

    // Heatmap
    const heatmap = mockStore.getDemoContractHeatmap("demo-case-pb");
    expect(heatmap.categories["Liability & Indemnity"]).toBeDefined();
    expect(heatmap.categories["Restrictive Covenants"].highest_risk).toBe("critical");
  });

  it("deletes a demo case from store", async () => {
    const mockStore = await import("./mockStore");
    const caseToDel = mockStore.getOrCreateDemoCase("delete-me-case");
    expect(caseToDel.id).toBe("delete-me-case");

    const deleted = mockStore.deleteDemoCase("delete-me-case");
    expect(deleted).toBe(true);

    const nonExistent = mockStore.deleteDemoCase("already-deleted-case");
    expect(nonExistent).toBe(false);
  });
});