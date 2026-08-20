import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const BACKEND_URL =
  process.env.BACKEND_URL ||
  (process.env.NEXT_PUBLIC_API_URL
    ? process.env.NEXT_PUBLIC_API_URL.replace(/\/api\/v1\/?$/, "")
    : "http://localhost:8000");

/**
 * Health check proxy for Rajora AI Private LLM runtime.
 * Proxies to backend /api/rajora/health (or fallback /api/v1/rajora/health / /api/health).
 */
export async function GET(req: NextRequest) {
  const start = Date.now();
  const timeoutMs = 3000;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    const targetUrl = `${BACKEND_URL.replace(/\/$/, "")}/api/rajora/health`;

    let res: Response;
    try {
      res = await fetch(targetUrl, {
        method: "GET",
        signal: controller.signal,
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
    } catch (fetchErr: any) {
      // Try fallback to /api/v1/rajora/health if /api/rajora/health returned connection refused or 404
      const fallbackUrl = `${BACKEND_URL.replace(/\/$/, "")}/api/v1/rajora/health`;
      try {
        res = await fetch(fallbackUrl, {
          method: "GET",
          signal: controller.signal,
          headers: { Accept: "application/json" },
          cache: "no-store",
        });
      } catch {
        throw fetchErr;
      }
    } finally {
      clearTimeout(timeoutId);
    }

    const latency_ms = Date.now() - start;

    if (!res.ok) {
      let errorText = `Backend responded with HTTP ${res.status}`;
      try {
        const errorData = await res.json();
        errorText = errorData.detail || errorData.error || errorText;
      } catch {
        // use fallback text
      }

      return NextResponse.json(
        {
          online: false,
          status: "unhealthy",
          provider: "rajora",
          model: "rajora-private",
          latency_ms,
          error: errorText,
        },
        { status: 503 }
      );
    }

    const data = await res.json().catch(() => ({}));

    return NextResponse.json(
      {
        online: true,
        status: data.status || "healthy",
        provider: data.provider || "rajora",
        model: data.model || "rajora-private",
        latency_ms: typeof data.latency_ms === "number" ? data.latency_ms : latency_ms,
        ...(data.version ? { version: data.version } : {}),
      },
      { status: 200 }
    );
  } catch (err: any) {
    const latency_ms = Date.now() - start;
    const isTimeout = err?.name === "AbortError" || err?.message?.includes("aborted");
    const errorMessage = isTimeout
      ? `Rajora backend health check timed out after ${timeoutMs}ms`
      : err?.message || "Rajora private inference service is unreachable";

    return NextResponse.json(
      {
        online: false,
        status: "unreachable",
        provider: "rajora",
        model: "rajora-private",
        latency_ms,
        error: errorMessage,
      },
      { status: 503 }
    );
  }
}
