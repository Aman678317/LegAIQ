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
    }).catch(() => null);
    clearTimeout(timeoutId);

    if (!res || !res.ok) {
      return { online: false, models: [], activeModel: null };
    }

    const data = await res.json();
    const allModels = (data.models || []).map((m: any) => m.name);
    // Separate text/chat generation models from embedding-only models
    const chatModels = allModels.filter(
      (m: string) =>
        !m.toLowerCase().includes("embed") &&
        !m.toLowerCase().includes("bge") &&
        !m.toLowerCase().includes("minilm")
    );
    const models = chatModels.length > 0 ? chatModels : allModels;
    const activeModel = chatModels[0] || (allModels.length > 0 ? allModels[0] : "llama3");
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

  // If the user selected an embedding model, fallback to llama3 or let universal fallback handle it
  const isEmbedModel =
    model.toLowerCase().includes("embed") ||
    model.toLowerCase().includes("bge") ||
    model.toLowerCase().includes("minilm");
  const actualModel = isEmbedModel ? "llama3" : model;

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
    const timeoutId = setTimeout(() => controller.abort(), 60000); // 1 min timeout

    const res = await fetch(`${baseUrl}/api/chat`, {
      method: "POST",
      signal: controller.signal,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: actualModel,
        messages: formattedMessages,
        stream: false,
        options: { temperature },
      }),
    }).catch(() => null);
    clearTimeout(timeoutId);

    if (res && res.ok) {
      const data = await res.json().catch(() => null);
      const content = data?.message?.content || "";
      if (content) {
        return {
          text: content,
          model: actualModel,
          duration_ms: Date.now() - start,
        };
      }
    }
  } catch {
    // direct connection failed (e.g. CORS or network error), try proxy next
  }

  // 2. Try Next.js Unified Chat API route /api/chat
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: actualModel,
        messages: formattedMessages,
        system: systemPrompt,
      }),
    }).catch(() => null);

    if (res && res.ok) {
      const data = await res.json().catch(() => null);
      const content = data?.content || data?.text || "";
      if (content) {
        return {
          text: content,
          model: actualModel,
          duration_ms: Date.now() - start,
        };
      }
    }
  } catch {
    // API route unavailable or offline
  }

  // 3. Try Next.js Ollama proxy /api/ollama/chat
  try {
    const res = await fetch("/api/ollama/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: actualModel,
        messages: formattedMessages,
        stream: false,
        options: { temperature },
      }),
    }).catch(() => null);

    if (res && res.ok) {
      const data = await res.json().catch(() => null);
      const content = data?.message?.content || data?.content || "";
      if (content) {
        return {
          text: content,
          model: actualModel,
          duration_ms: Date.now() - start,
        };
      }
    }
  } catch {
    // proxy also failed
  }

  return null;
}
