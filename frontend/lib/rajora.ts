/**
 * Rajora AI Private LLM Client & Health Utilities
 * Connects to the sovereign, self-hosted Rajora inference runtime
 * (per RAJORA-SOP-AI-2026-04) for 100% private, zero third-party data egress.
 */

export interface RajoraModelInfo {
  id: string;
  name: string;
  provider: "rajora";
  badge: string;
  description: string;
  contextWindow: number;
  private: boolean;
  zeroThirdParty: boolean;
}

export const RAJORA_PRIVATE_MODEL: RajoraModelInfo = {
  id: "rajora-private",
  name: "Rajora Private LLM",
  provider: "rajora",
  badge: "Private · Zero Third-Party",
  description: "Self-hosted sovereign LLM inference with zero data retention and zero third-party transmission.",
  contextWindow: 32768,
  private: true,
  zeroThirdParty: true,
};

export interface RajoraStatus {
  online: boolean;
  status?: string;
  provider?: string;
  model?: string;
  latency_ms?: number;
  error?: string;
}

export interface RajoraHealthResponse {
  online: boolean;
  status: string;
  provider: string;
  model: string;
  latency_ms?: number;
  error?: string;
}

export interface RajoraRequestPayload {
  prompt: string;
  max_tokens: number;
  temperature: number;
  model: string;
  provider: "rajora";
}

/**
 * Checks whether a given model ID represents the Rajora Private LLM.
 */
export function isRajoraModel(modelId?: string | null): boolean {
  if (!modelId) return false;
  const normalized = modelId.toLowerCase().trim();
  return (
    normalized === "rajora-private" ||
    normalized === "rajora" ||
    normalized === "rajora_private" ||
    normalized.startsWith("rajora/") ||
    normalized.startsWith("rajora-")
  );
}

/**
 * Returns the badge string for Rajora models, or null for other models.
 */
export function getRajoraBadge(modelId?: string | null): string | null {
  if (isRajoraModel(modelId)) {
    return RAJORA_PRIVATE_MODEL.badge;
  }
  return null;
}

/**
 * Returns model metadata for Rajora if applicable.
 */
export function getRajoraModelInfo(modelId?: string | null): RajoraModelInfo | null {
  if (isRajoraModel(modelId)) {
    return RAJORA_PRIVATE_MODEL;
  }
  return null;
}

/**
 * Formats latency in milliseconds for display.
 */
export function formatRajoraLatency(latencyMs?: number): string {
  if (latencyMs === undefined || latencyMs === null || isNaN(latencyMs)) {
    return "--";
  }
  return `${Math.round(latencyMs)}ms`;
}

/**
 * Builds the standard POST payload for Rajora Private LLM inference.
 */
export function createRajoraRequestPayload(
  prompt: string,
  options?: {
    max_tokens?: number;
    temperature?: number;
    model?: string;
  }
): RajoraRequestPayload {
  return {
    prompt,
    max_tokens: options?.max_tokens ?? 2048,
    temperature: options?.temperature ?? 0.2,
    model: options?.model || RAJORA_PRIVATE_MODEL.id,
    provider: "rajora",
  };
}

/**
 * Queries the Next.js frontend proxy endpoint (/api/rajora/health) with a timeout
 * to determine the connectivity, health, and latency of the Rajora backend service.
 */
export async function checkRajoraStatus(options?: {
  timeoutMs?: number;
  endpoint?: string;
}): Promise<RajoraStatus> {
  const timeoutMs = options?.timeoutMs ?? 2500;
  const endpoint = options?.endpoint ?? "/api/rajora/health";
  const start = Date.now();

  try {
    let res: Response;

    if (typeof AbortController !== "undefined") {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

      try {
        res = await fetch(endpoint, {
          method: "GET",
          signal: controller.signal,
          headers: { Accept: "application/json" },
          cache: "no-store",
        });
      } finally {
        clearTimeout(timeoutId);
      }
    } else {
      res = await fetch(endpoint, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
    }

    const latency_ms = Date.now() - start;

    if (!res.ok) {
      let errorDetail = `HTTP ${res.status}: ${res.statusText || "Service Unavailable"}`;
      try {
        const errorJson = await res.json();
        if (errorJson?.error) {
          errorDetail = typeof errorJson.error === "string" ? errorJson.error : JSON.stringify(errorJson.error);
        } else if (errorJson?.detail) {
          errorDetail = errorJson.detail;
        }
      } catch {
        // use fallback errorDetail
      }

      return {
        online: false,
        status: "unreachable",
        provider: "rajora",
        model: RAJORA_PRIVATE_MODEL.id,
        latency_ms,
        error: errorDetail,
      };
    }

    const data = await res.json();
    return {
      online: Boolean(data?.online ?? (data?.status === "healthy" || data?.status === "online")),
      status: data?.status || "healthy",
      provider: data?.provider || "rajora",
      model: data?.model || RAJORA_PRIVATE_MODEL.id,
      latency_ms: typeof data?.latency_ms === "number" ? data.latency_ms : latency_ms,
    };
  } catch (err: any) {
    const latency_ms = Date.now() - start;
    const isAbort = err?.name === "AbortError" || err?.message?.includes("aborted");
    const message = isAbort
      ? `Health check timed out after ${timeoutMs}ms`
      : err?.message || "Failed to reach Rajora health proxy";

    return {
      online: false,
      status: "unreachable",
      provider: "rajora",
      model: RAJORA_PRIVATE_MODEL.id,
      latency_ms,
      error: message,
    };
  }
}
