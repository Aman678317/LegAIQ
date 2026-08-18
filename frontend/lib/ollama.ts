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
}

const DEFAULT_OLLAMA_URL = process.env.NEXT_PUBLIC_OLLAMA_URL || "http://localhost:11434";

/**
 * Check if local Ollama service is running and retrieve installed models
 */
export async function checkOllamaStatus(baseUrl = DEFAULT_OLLAMA_URL): Promise<OllamaStatus> {
  if (typeof window === "undefined") {
    return { online: false, models: [], activeModel: null };
  }

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

    return {
      online: true,
      models,
      activeModel,
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
  try {
    const start = Date.now();
    const res = await fetch(`${baseUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: prompt },
        ],
        stream: false,
        options: {
          temperature: 0.2,
        },
      }),
    });

    if (!res.ok) return null;
    const data = await res.json();
    const content = data?.message?.content || "";
    return {
      text: content,
      model,
      duration_ms: Date.now() - start,
    };
  } catch {
    return null;
  }
}
