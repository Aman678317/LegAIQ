/**
 * Local Ollama AI Client
 * Connects directly to local Ollama (http://localhost:11434) for private,
 * local-first Indian legal intelligence, document Q&A, and drafting.
 */

export interface OllamaModel {
  name: string;
  size?: number;
  digest?: string;
  modified_at?: string;
}

export interface OllamaStatus {
  online: boolean;
  models: string[];
  activeModel: string | null;
  latency_ms?: number;
  error?: string;
}

const DEFAULT_OLLAMA_URL = process.env.NEXT_PUBLIC_OLLAMA_URL || "http://localhost:11434";

export function getOllamaBaseUrl(): string {
  if (typeof window !== "undefined") {
    const saved = localStorage.getItem("jurisiva_ollama_url");
    if (saved) return saved;
  }
  return DEFAULT_OLLAMA_URL;
}

/**
 * Check if local Ollama service is running and retrieve installed models
 */
export async function checkOllamaStatus(baseUrl = DEFAULT_OLLAMA_URL): Promise<OllamaStatus> {
  if (typeof window === "undefined") {
    return { online: false, models: [], activeModel: null };
  }

  const start = Date.now();
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 1800);

    const res = await fetch(`${baseUrl}/api/tags`, {
      method: "GET",
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      return { online: false, models: [], activeModel: null };
    }

    const data = await res.json();
    const models = (data.models || []).map((m: any) => m.name);
    const activeModel = models[0] || "llama3";
    const latency_ms = Date.now() - start;

    return {
      online: true,
      models,
      activeModel,
      latency_ms,
    };
  } catch {
    return { online: false, models: [], activeModel: null };
  }
}

/**
 * Generate AI completion directly using local Ollama instance
 */
export async function queryLocalOllama(
  prompt: string,
  systemPrompt: string,
  model = "llama3",
  baseUrl = DEFAULT_OLLAMA_URL
): Promise<{ text: string; model: string; duration_ms: number } | null> {
  return chatWithOllama([{ role: "user", content: prompt }], model, systemPrompt, baseUrl);
}

/**
 * Universal Multi-turn Chat with Ollama (direct fetch with API proxy fallback)
 */
export async function chatWithOllama(
  messages: Array<{ role: string; content: string }>,
  model = "llama3",
  systemPrompt = "You are a helpful, versatile, and highly capable AI assistant. You can answer questions on any topic—including general knowledge, coding, writing, law, science, history, brainstorming, and problem solving. Provide accurate, clear, and well-structured answers.",
  baseUrl = DEFAULT_OLLAMA_URL,
  temperature = 0.7
): Promise<{ text: string; model: string; duration_ms: number } | null> {
  const start = Date.now();
  const formattedMessages: Array<{ role: string; content: string }> = [];

  if (systemPrompt) {
    formattedMessages.push({ role: "system", content: systemPrompt });
  }
  for (const m of messages) {
    formattedMessages.push({ role: m.role, content: m.content });
  }

  // 1. Try direct connection to Ollama
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 min timeout for long generation

    const res = await fetch(`${baseUrl}/api/chat`, {
      method: "POST",
      signal: controller.signal,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        messages: formattedMessages,
        stream: false,
        options: { temperature },
      }),
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      const data = await res.json();
      const content = data?.message?.content || "";
      if (content) {
        return {
          text: content,
          model,
          duration_ms: Date.now() - start,
        };
      }
    }
  } catch {
    // direct connection failed (e.g. CORS or network error), try proxy next
  }

  // 2. Try Next.js API route proxy /api/ollama/chat
  try {
    const res = await fetch("/api/ollama/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        messages: formattedMessages,
        stream: false,
        options: { temperature },
      }),
    });

    if (res.ok) {
      const data = await res.json();
      const content = data?.message?.content || data?.content || "";
      if (content) {
        return {
          text: content,
          model,
          duration_ms: Date.now() - start,
        };
      }
    }
  } catch {
    // proxy failed
  }

  return null;
}
