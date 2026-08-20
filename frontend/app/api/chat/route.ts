import { NextRequest, NextResponse } from "next/server";

const OLLAMA_BASE_URL =
  process.env.OLLAMA_BASE_URL ||
  process.env.NEXT_PUBLIC_OLLAMA_URL ||
  "http://localhost:11434";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { messages = [], model = "llama3", temperature = 0.7, system } = body;

    // 1. Try local Ollama instance if reachable
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000);

      const formattedMessages = system
        ? [{ role: "system", content: system }, ...messages]
        : messages;

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
      // Ollama unreachable, continue
    }

    // 2. Try NVIDIA NIM if configured in environment
    const nvidiaKey = process.env.NVIDIA_API_KEY;
    const openaiKey = process.env.OPENAI_API_KEY;
    const groqKey = process.env.GROQ_API_KEY;

    if (nvidiaKey) {
      try {
        const nvidiaRes = await fetch("https://integrate.api.nvidia.com/v1/chat/completions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${nvidiaKey}`,
          },
          body: JSON.stringify({
            model: "meta/llama-3.3-70b-instruct",
            messages: system ? [{ role: "system", content: system }, ...messages] : messages,
            temperature,
          }),
        });

        if (nvidiaRes.ok) {
          const nvidiaData = await nvidiaRes.json();
          return NextResponse.json({
            text: nvidiaData.choices[0].message.content,
            model: "NVIDIA Llama 3.3 70B",
            provider: "nvidia",
          });
        }
      } catch {
        // continue
      }
    }

    if (groqKey) {
      try {
        const groqRes = await fetch("https://api.groq.com/openai/v1/chat/completions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${groqKey}`,
          },
          body: JSON.stringify({
            model: "llama-3.3-70b-versatile",
            messages: system ? [{ role: "system", content: system }, ...messages] : messages,
            temperature,
          }),
        });

        if (groqRes.ok) {
          const groqData = await groqRes.json();
          return NextResponse.json({
            text: groqData.choices[0].message.content,
            model: "Groq Llama 3.3 70B",
            provider: "groq",
          });
        }
      } catch {
        // continue
      }
    }

    if (openaiKey) {
      try {
        const aiRes = await fetch("https://api.openai.com/v1/chat/completions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${openaiKey}`,
          },
          body: JSON.stringify({
            model: "gpt-4o-mini",
            messages: system ? [{ role: "system", content: system }, ...messages] : messages,
            temperature,
          }),
        });

        if (aiRes.ok) {
          const aiData = await aiRes.json();
          return NextResponse.json({
            text: aiData.choices[0].message.content,
            model: "GPT-4o Mini",
            provider: "openai",
          });
        }
      } catch {
        // continue
      }
    }

    return NextResponse.json(
      { error: "no_active_provider", message: "No live LLM provider responded." },
      { status: 503 }
    );
  } catch (err: any) {
    return NextResponse.json(
      { error: "chat_error", message: err.message || "Failed to process chat" },
      { status: 500 }
    );
  }
}
