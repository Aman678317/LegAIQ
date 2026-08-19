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
});