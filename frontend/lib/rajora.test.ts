import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock ollama to avoid ECONNREFUSED in CI/isolated test environments
vi.mock("./ollama", () => ({
  checkOllamaStatus: vi.fn().mockResolvedValue({ online: false, models: [], activeModel: null }),
  queryLocalOllama: vi.fn().mockResolvedValue({ text: "", model: "llama3" }),
  getOllamaBaseUrl: vi.fn().mockReturnValue("http://localhost:11434"),
}));

import {
  RAJORA_PRIVATE_MODEL,
  checkRajoraStatus,
  isRajoraModel,
  getRajoraBadge,
  getRajoraModelInfo,
  formatRajoraLatency,
  createRajoraRequestPayload,
} from "./rajora";
import {
  LEGAL_MODEL_OPTIONS,
  generateLegalAnswer,
  generateLegalResearch,
  generateLegalDraft,
  generateLegalReport,
  LegalContext,
} from "./aiEngine";

describe("Rajora Private LLM - Client & Helpers", () => {
  const sampleContext: LegalContext = {
    caseId: "test-case-rajora-1",
    caseName: "Vodafone International Holdings B.V. v. Union of India",
    caseType: "TAX",
    jurisdictionState: "India",
    description: "Offshore share acquisition of CGP Investments (Holdings) Ltd",
    documentNames: ["39003.pdf"],
  };

  const propertyContext: LegalContext = {
    caseId: "test-case-prop-1",
    caseName: "Whitefield Land Due Diligence",
    caseType: "PROPERTY",
    jurisdictionState: "Karnataka",
    description: "Survey 124/3 boundary verification",
    documentNames: ["sale_deed_1987.pdf", "partition_deed_2004.pdf"],
  };

  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  describe("RAJORA_PRIVATE_MODEL definition", () => {
    it("has required id, name, provider, and badge", () => {
      expect(RAJORA_PRIVATE_MODEL.id).toBe("rajora-private");
      expect(RAJORA_PRIVATE_MODEL.name).toBe("Rajora Private LLM");
      expect(RAJORA_PRIVATE_MODEL.provider).toBe("rajora");
      expect(RAJORA_PRIVATE_MODEL.badge).toBe("Private · Zero Third-Party");
      expect(RAJORA_PRIVATE_MODEL.private).toBe(true);
      expect(RAJORA_PRIVATE_MODEL.zeroThirdParty).toBe(true);
    });
  });

  describe("isRajoraModel()", () => {
    it("identifies rajora models correctly", () => {
      expect(isRajoraModel("rajora-private")).toBe(true);
      expect(isRajoraModel("rajora")).toBe(true);
      expect(isRajoraModel("RAJORA-PRIVATE")).toBe(true);
      expect(isRajoraModel("rajora_private")).toBe(true);
      expect(isRajoraModel("rajora/legal-large")).toBe(true);
    });

    it("returns false for non-rajora models and falsy values", () => {
      expect(isRajoraModel("claude-3-5-sonnet")).toBe(false);
      expect(isRajoraModel("gpt-4o")).toBe(false);
      expect(isRajoraModel("llama3")).toBe(false);
      expect(isRajoraModel("deepseek-r1")).toBe(false);
      expect(isRajoraModel("")).toBe(false);
      expect(isRajoraModel(null)).toBe(false);
      expect(isRajoraModel(undefined)).toBe(false);
    });
  });

  describe("getRajoraBadge()", () => {
    it("returns correct badge string for rajora models", () => {
      expect(getRajoraBadge("rajora-private")).toBe("Private · Zero Third-Party");
      expect(getRajoraBadge("rajora")).toBe("Private · Zero Third-Party");
    });

    it("returns null for non-rajora models", () => {
      expect(getRajoraBadge("claude-3-5-sonnet")).toBeNull();
      expect(getRajoraBadge("gpt-4o")).toBeNull();
      expect(getRajoraBadge(undefined)).toBeNull();
    });
  });

  describe("getRajoraModelInfo()", () => {
    it("returns full metadata for rajora models", () => {
      const info = getRajoraModelInfo("rajora-private");
      expect(info).not.toBeNull();
      expect(info?.id).toBe("rajora-private");
      expect(info?.badge).toBe("Private · Zero Third-Party");
      expect(info?.provider).toBe("rajora");
      expect(info?.private).toBe(true);
    });

    it("returns null for non-rajora models", () => {
      expect(getRajoraModelInfo("gpt-4o")).toBeNull();
      expect(getRajoraModelInfo(null)).toBeNull();
    });
  });

  describe("formatRajoraLatency()", () => {
    it("formats milliseconds correctly", () => {
      expect(formatRajoraLatency(45)).toBe("45ms");
      expect(formatRajoraLatency(12.8)).toBe("13ms");
      expect(formatRajoraLatency(0)).toBe("0ms");
    });

    it("handles undefined, null, and NaN gracefully", () => {
      expect(formatRajoraLatency(undefined)).toBe("--");
      expect(formatRajoraLatency(null as any)).toBe("--");
      expect(formatRajoraLatency(NaN)).toBe("--");
    });
  });

  describe("createRajoraRequestPayload()", () => {
    it("builds valid request payload with provider: rajora and model: rajora-private", () => {
      const payload = createRajoraRequestPayload("Analyze Section 9(1)(i)");
      expect(payload).toEqual({
        prompt: "Analyze Section 9(1)(i)",
        max_tokens: 2048,
        temperature: 0.2,
        model: "rajora-private",
        provider: "rajora",
      });
    });

    it("accepts custom options", () => {
      const payload = createRajoraRequestPayload("Draft notice", {
        max_tokens: 4096,
        temperature: 0.7,
        model: "rajora-private",
      });
      expect(payload.max_tokens).toBe(4096);
      expect(payload.temperature).toBe(0.7);
      expect(payload.model).toBe("rajora-private");
      expect(payload.provider).toBe("rajora");
    });
  });

  describe("checkRajoraStatus()", () => {
    it("returns online status and latency when health proxy returns 200", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          online: true,
          status: "healthy",
          provider: "rajora",
          model: "rajora-private",
          latency_ms: 18,
        }),
      });

      const result = await checkRajoraStatus({ endpoint: "/api/rajora/health" });
      expect(result.online).toBe(true);
      expect(result.status).toBe("healthy");
      expect(result.provider).toBe("rajora");
      expect(result.model).toBe("rajora-private");
      expect(result.latency_ms).toBe(18);
      expect(result.error).toBeUndefined();
    });

    it("returns offline status when health proxy returns 503", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        statusText: "Service Unavailable",
        json: async () => ({
          online: false,
          error: "Rajora inference backend unreachable at http://localhost:8000",
        }),
      });

      const result = await checkRajoraStatus({ endpoint: "/api/rajora/health" });
      expect(result.online).toBe(false);
      expect(result.status).toBe("unreachable");
      expect(result.provider).toBe("rajora");
      expect(result.error).toContain("unreachable");
    });

    it("returns offline status on network connection failure", async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error("Network connection refused"));

      const result = await checkRajoraStatus({ endpoint: "/api/rajora/health" });
      expect(result.online).toBe(false);
      expect(result.status).toBe("unreachable");
      expect(result.error).toContain("Network connection refused");
    });

    it("handles timeout / abort properly", async () => {
      const abortError = new Error("The operation was aborted");
      abortError.name = "AbortError";
      global.fetch = vi.fn().mockRejectedValue(abortError);

      const result = await checkRajoraStatus({ timeoutMs: 500 });
      expect(result.online).toBe(false);
      expect(result.error).toContain("timed out after 500ms");
    });
  });

  describe("aiEngine.ts Integration & Model Registration", () => {
    it("includes rajora-private in LEGAL_MODEL_OPTIONS", () => {
      const rajoraOption = LEGAL_MODEL_OPTIONS.find((opt) => opt.id === "rajora-private");
      expect(rajoraOption).toBeDefined();
      expect(rajoraOption?.name).toBe("Rajora Private LLM");
      expect(rajoraOption?.provider).toBe("rajora");
      expect(rajoraOption?.badge).toBe("Private · Zero Third-Party");
      expect(rajoraOption?.isPrivate).toBe(true);
    });

    it("generates legal answer using rajora-private with zero third-party citation note", async () => {
      const answer = await generateLegalAnswer(
        sampleContext,
        "What was the main tax dispute?",
        "en",
        "rajora-private"
      );

      expect(answer).toBeDefined();
      expect(answer.content).toBeTruthy();
      expect(answer.citations.length).toBeGreaterThan(0);
    });

    it("generates legal answer for property domain using rajora-private", async () => {
      const answer = await generateLegalAnswer(
        propertyContext,
        "Explain the survey discrepancy",
        "en",
        "rajora-private"
      );

      expect(answer).toBeDefined();
      expect(answer.content).toContain("Survey Discrepancy");
      expect(answer.citations[0].source_text).toContain("Bounded on West by Gramathana Road");
    });

    it("generates legal research memorandum with provider: rajora metadata", async () => {
      const research = await generateLegalResearch(
        sampleContext,
        "Analyze Section 195 withholding tax",
        "India",
        "en",
        "rajora-private"
      );

      expect(research.status).toBe("COMPLETED");
      expect(research.provider).toBe("rajora");
      expect(research.model).toBe("rajora-private");
      expect(research.answer).toBeTruthy();
      expect(research.sources.some((s) => s.id === "src-rajora-vault")).toBe(true);
    });

    it("generates legal draft with Rajora Private LLM footer annotation", () => {
      const draft = generateLegalDraft(
        sampleContext,
        "writ_petition",
        "Writ Petition under Article 226",
        "Challenge Section 201 Notice",
        "rajora-private"
      );

      expect(draft.id).toBeDefined();
      expect(draft.model).toBe("rajora-private");
      expect(draft.content).toContain("Rajora Private LLM (Private · Zero Third-Party)");
    });

    it("generates legal report with Rajora Private LLM inference metadata", () => {
      const report = generateLegalReport(sampleContext, "rajora-private");

      expect(report.id).toBeDefined();
      expect(report.model).toBe("rajora-private");
      expect((report.content as any).Inference_Engine).toBe("Rajora Private LLM (Private · Zero Third-Party)");
    });
  });

  describe("Zero Regressions on Existing Providers", () => {
    it("preserves non-rajora model execution without interference", async () => {
      const claudeAnswer = await generateLegalAnswer(
        sampleContext,
        "What was the main tax dispute?",
        "en",
        "claude-3-5-sonnet"
      );
      expect(claudeAnswer.content).toBeTruthy();

      const defaultDraft = generateLegalDraft(
        sampleContext,
        "writ_petition",
        "Writ Petition under Article 226",
        "Challenge Section 201 Notice"
      );
      expect(defaultDraft.content).toContain("AI-generated draft. Review and verify before filing or sending.");
    });
  });
});
