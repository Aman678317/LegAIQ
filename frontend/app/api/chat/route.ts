import { NextRequest, NextResponse } from "next/server";
import { generateUniversalAiResponse } from "@/lib/universalAi";

const OLLAMA_BASE_URL =
  process.env.OLLAMA_BASE_URL ||
  process.env.NEXT_PUBLIC_OLLAMA_URL ||
  "http://localhost:11434";

const BACKEND_API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.API_URL ||
  "https://legaiq-1.onrender.com";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { messages = [], model = "llama3", temperature = 0.7, system } = body;

    const groqKey = process.env.GROQ_API_KEY;
    const openaiKey = process.env.OPENAI_API_KEY;
    const nvidiaKey = process.env.NVIDIA_API_KEY;

    const formattedMessages = system
      ? [{ role: "system", content: system }, ...messages]
      : messages;

    const lastUserMessage = [...messages].reverse().find((m: any) => m.role === "user")?.content || "";

    // 1. Prioritize GROQ LPU (Ultra-Fast: ~300ms - 700ms response time)
    if (groqKey) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 6000);

        const groqRes = await fetch("https://api.groq.com/openai/v1/chat/completions", {
          method: "POST",
          signal: controller.signal,
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${groqKey}`,
          },
          body: JSON.stringify({
            model: "llama-3.3-70b-versatile",
            messages: formattedMessages,
            temperature,
          }),
        });
        clearTimeout(timeoutId);

        if (groqRes.ok) {
          const groqData = await groqRes.json();
          const content = groqData?.choices?.[0]?.message?.content;
          if (content) {
            return NextResponse.json({
              text: content,
              content: content,
              model: "Groq Llama 3.3 70B (Fast)",
              provider: "groq",
            });
          }
        }
      } catch {
        // Fall through to next provider
      }
    }

    // 2. Try OpenAI (Fast & reliable fallback)
    if (openaiKey) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 6000);

        const aiRes = await fetch("https://api.openai.com/v1/chat/completions", {
          method: "POST",
          signal: controller.signal,
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${openaiKey}`,
          },
          body: JSON.stringify({
            model: "gpt-4o-mini",
            messages: formattedMessages,
            temperature,
          }),
        });
        clearTimeout(timeoutId);

        if (aiRes.ok) {
          const aiData = await aiRes.json();
          const content = aiData?.choices?.[0]?.message?.content;
          if (content) {
            return NextResponse.json({
              text: content,
              model: "GPT-4o Mini",
              provider: "openai",
            });
          }
        }
      } catch {
        // Fall through
      }
    }

    // 3. Try NVIDIA NIM (with strict 5s timeout)
    if (nvidiaKey) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);

        const nvidiaRes = await fetch("https://integrate.api.nvidia.com/v1/chat/completions", {
          method: "POST",
          signal: controller.signal,
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${nvidiaKey}`,
          },
          body: JSON.stringify({
            model: "meta/llama-3.3-70b-instruct",
            messages: formattedMessages,
            temperature,
          }),
        });
        clearTimeout(timeoutId);

        if (nvidiaRes.ok) {
          const nvidiaData = await nvidiaRes.json();
          const content = nvidiaData?.choices?.[0]?.message?.content;
          if (content) {
            return NextResponse.json({
              text: content,
              model: "NVIDIA Llama 3.3 70B",
              provider: "nvidia",
            });
          }
        }
      } catch {
        // Fall through
      }
    }

    // 4. Try Backend FastAPI LLM router
    if (BACKEND_API_URL) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        const cleanBase = BACKEND_API_URL.replace(/\/$/, "");
        const backendEndpoint = cleanBase.includes("/api/v1") ? `${cleanBase}/ai/complete` : `${cleanBase}/api/v1/ai/complete`;

        const backendRes = await fetch(backendEndpoint, {
          method: "POST",
          signal: controller.signal,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt: lastUserMessage,
            system: system || "You are an intelligent, versatile legal & technical AI assistant.",
            task: "chat",
            max_tokens: 2048,
          }),
        });
        clearTimeout(timeoutId);

        if (backendRes.ok) {
          const backendData = await backendRes.json();
          const content = backendData?.content || backendData?.text;
          if (content) {
            return NextResponse.json({
              text: content,
              model: backendData.model || "LegAIQ AI Gateway",
              provider: backendData.provider || "backend",
            });
          }
        }
      } catch {
        // Fall through
      }
    }

    // 5. Try local Ollama instance (1s timeout)
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 1000);

      const ollamaRes = await fetch(`${OLLAMA_BASE_URL.replace(/\/$/, "")}/api/chat`, {
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

      if (ollamaRes.ok) {
        const data = await ollamaRes.json();
        const content = data?.message?.content || "";
        if (content) {
          return NextResponse.json({
            text: content,
            model: `Ollama (${model})`,
            provider: "ollama",
          });
        }
      }
    } catch {
      // Ollama unreachable
    }

    // 6. Universal Native AI Response Generator (Always available, zero-failure fallback)
    const fallbackResponse = generateUniversalAiResponse(lastUserMessage, messages);
    return NextResponse.json({
      text: fallbackResponse.text,
      model: fallbackResponse.model,
      provider: "jurisiva_universal",
    });
  } catch (err: any) {
    return NextResponse.json(
      { error: "chat_error", message: err.message || "Failed to process chat" },
      { status: 500 }
    );
  }
}
