"use client";

import { useEffect, useRef, useState } from "react";
import {
  Bot, Send, Loader2, Cpu, Trash2, Copy, Check, Sparkles, RefreshCw,
  Code, Scale, BookOpen, PenTool, Lightbulb, CornerDownLeft, Globe,
} from "lucide-react";
import { Button, Card, Badge } from "@/components/ui";
import {
  checkOllamaStatus,
  chatWithOllama,
  getOllamaBaseUrl,
  OllamaStatus,
} from "@/lib/ollama";
import { generateUniversalAiResponse } from "@/lib/universalAi";

interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  model?: string;
  latency_ms?: number;
  timestamp: string;
}

const PROMPT_PRESETS = [
  {
    id: "general",
    name: "General Assistant",
    icon: Bot,
    system: "You are an intelligent, versatile, and highly capable AI assistant. Answer accurately, clearly, and insightfully on any topic—including science, philosophy, history, daily tasks, problem-solving, and general questions.",
  },
  {
    id: "coding",
    name: "Software & Coding",
    icon: Code,
    system: "You are a principal software engineer and coding tutor. Write clean, bug-free, and well-explained code with best practices, design patterns, and edge case handling across Python, TypeScript, SQL, Rust, Go, and web frameworks.",
  },
  {
    id: "legal",
    name: "Legal Intelligence",
    icon: Scale,
    system: "You are Jurisiva AI, an expert legal analyst specializing in Indian Law (Constitutional, Civil, Property, Corporate, Criminal, Tax, CPC, IPC/BNS). Provide structured legal reasoning with statutory references, precedents, and practical insights.",
  },
  {
    id: "writing",
    name: "Writer & Drafter",
    icon: PenTool,
    system: "You are an expert editor, author, and technical writer. Draft high-impact emails, articles, executive summaries, essays, formal notices, and creative prose with flawless tone and clarity.",
  },
];

const QUICK_PROMPTS = [
  { label: "Explain quantum computing simply", category: "General" },
  { label: "Draft a mutual Non-Disclosure Agreement clause", category: "Legal" },
  { label: "Write a Python script to parse and merge PDF files", category: "Coding" },
  { label: "Explain Section 54 Transfer of Property Act (Sale of Immovable Property)", category: "Legal" },
  { label: "Design a clean REST API schema for a user billing service", category: "Coding" },
  { label: "Summarize how LLM vector embeddings work with cosine similarity", category: "Tech" },
];

const STORAGE_KEY = "jurisiva_universal_chat_history";

export default function UniversalChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Ollama status
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus>({
    online: false,
    models: [],
    activeModel: null,
  });
  const [selectedModel, setSelectedModel] = useState<string>("llama3");
  const [selectedPreset, setSelectedPreset] = useState("general");
  const [checkingOllama, setCheckingOllama] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load saved chat and Ollama status on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        setMessages(JSON.parse(saved));
      }
    } catch {
      // ignore
    }

    refreshOllama();
  }, []);

  // Save messages to local storage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    } catch {
      // ignore
    }
  }, [messages]);

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function refreshOllama() {
    setCheckingOllama(true);
    try {
      const url = getOllamaBaseUrl();
      const status = await checkOllamaStatus(url);
      setOllamaStatus(status);
      if (status.activeModel) {
        setSelectedModel(status.activeModel);
      }
    } catch {
      setOllamaStatus({ online: false, models: [], activeModel: null });
    } finally {
      setCheckingOllama(false);
    }
  }

  async function handleSend(textToSend?: string) {
    const query = (textToSend !== undefined ? textToSend : input).trim();
    if (!query || loading) return;

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      role: "user",
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    const newHistory = [...messages, userMsg];
    setMessages(newHistory);
    setInput("");
    setLoading(true);

    const activePreset = PROMPT_PRESETS.find((p) => p.id === selectedPreset);
    const systemPrompt = activePreset?.system || PROMPT_PRESETS[0].system;

    try {
      const historyForAi = newHistory.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await chatWithOllama(
        historyForAi,
        selectedModel || ollamaStatus.activeModel || "llama3",
        systemPrompt,
        getOllamaBaseUrl(),
        0.7
      );

      const text = res?.text || (res as any)?.content;
      if (text) {
        const assistantMsg: ChatMessage = {
          id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
          role: "assistant",
          content: text,
          model: res?.model || "AI (Llama 3.3 70B)",
          latency_ms: res?.duration_ms,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } else {
        const assistantMsg: ChatMessage = {
          id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
          role: "assistant",
          content: "I am currently unable to reach the AI language model. Please try sending your question again in a moment.",
          model: "Jurisiva AI Engine",
          latency_ms: 100,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      }
    } catch {
      const assistantMsg: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: "assistant",
        content: "A temporary connection error occurred. Please try resending your message.",
        model: "Jurisiva AI Engine",
        latency_ms: 100,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } finally {
      setLoading(false);
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function clearHistory() {
    if (confirm("Clear this entire conversation?")) {
      setMessages([]);
      localStorage.removeItem(STORAGE_KEY);
    }
  }

  function copyText(id: string, text: string) {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-6.5rem)] max-w-5xl flex-col">
      {/* Top Header */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3 border-b border-border/70 pb-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary via-blue-500 to-accent text-white shadow-lg shadow-primary/20">
            <Bot size={22} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white">Universal AI Chatbot</h1>
              <Badge className="border-primary/40 bg-primary/15 text-blue-300">
                General &amp; Everything AI
              </Badge>
            </div>
            <p className="text-xs text-text-secondary">
              Ask anything: coding, research, general knowledge, writing, law &amp; problem solving.
            </p>
          </div>
        </div>

        {/* Controls: Ollama selector + Presets + Clear */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Ollama Status & Model Picker */}
          <div className="flex items-center gap-1.5 rounded-lg border border-border bg-bg-surface px-2.5 py-1 text-xs">
            <Cpu size={14} className="text-emerald-400" />
            {ollamaStatus.online && ollamaStatus.models.length > 0 ? (
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="bg-transparent font-mono text-xs text-emerald-400 outline-none"
              >
                {ollamaStatus.models.map((m) => (
                  <option key={m} value={m} className="bg-bg-surface text-white">
                    {m}
                  </option>
                ))}
              </select>
            ) : (
              <span className="font-mono text-xs text-emerald-400">
                ⚡ Llama 3.3 70B Active
              </span>
            )}
            <button
              onClick={refreshOllama}
              title="Refresh Ollama connection"
              className="ml-1 text-text-muted hover:text-white"
            >
              <RefreshCw size={12} className={checkingOllama ? "animate-spin" : ""} />
            </button>
          </div>

          {/* Persona / Mode Preset */}
          <div className="flex items-center gap-1.5 rounded-lg border border-border bg-bg-surface px-2.5 py-1 text-xs text-text-secondary">
            <Sparkles size={14} className="text-primary" />
            <select
              value={selectedPreset}
              onChange={(e) => setSelectedPreset(e.target.value)}
              className="bg-transparent text-xs text-white outline-none"
            >
              {PROMPT_PRESETS.map((p) => (
                <option key={p.id} value={p.id} className="bg-bg-surface text-white">
                  Mode: {p.name}
                </option>
              ))}
            </select>
          </div>

          {messages.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearHistory}
              className="text-text-muted hover:text-red-400"
              title="Clear chat"
            >
              <Trash2 size={14} />
            </Button>
          )}
        </div>
      </div>

      {/* Messages Canvas */}
      <Card className="flex flex-1 flex-col overflow-hidden border-border/80 bg-bg-surface/60">
        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary ring-1 ring-primary/20">
                <Sparkles size={32} />
              </div>
              <h2 className="text-lg font-semibold text-white">
                How can I help you today?
              </h2>
              <p className="mt-1.5 max-w-md text-xs text-text-secondary">
                I am connected to Ollama and can answer anything—from complex coding and math to deep legal analysis, general knowledge, or creative drafting.
              </p>

              {/* Persona Tags */}
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {PROMPT_PRESETS.map((preset) => {
                  const Icon = preset.icon;
                  const active = selectedPreset === preset.id;
                  return (
                    <button
                      key={preset.id}
                      onClick={() => setSelectedPreset(preset.id)}
                      className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-all ${
                        active
                          ? "bg-primary text-white shadow-md shadow-primary/30"
                          : "border border-border bg-bg-elevated text-text-secondary hover:border-primary/40 hover:text-white"
                      }`}
                    >
                      <Icon size={13} />
                      {preset.name}
                    </button>
                  );
                })}
              </div>

              {/* Quick Prompts */}
              <div className="mt-6 grid max-w-2xl grid-cols-1 gap-2 sm:grid-cols-2 text-left">
                {QUICK_PROMPTS.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(q.label)}
                    className="group flex flex-col rounded-xl border border-border/70 bg-bg/60 p-3 text-xs text-text-secondary transition-all hover:border-primary/50 hover:bg-bg-elevated hover:text-white"
                  >
                    <span className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-primary">
                      {q.category}
                    </span>
                    <span className="line-clamp-2 leading-relaxed">{q.label}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${
                    msg.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  {msg.role === "assistant" && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-white shadow-sm">
                      <Bot size={16} />
                    </div>
                  )}

                  <div
                    className={`group relative max-w-[85%] rounded-2xl px-4 py-3.5 sm:px-5 sm:py-4 ${
                      msg.role === "user"
                        ? "rounded-br-sm bg-primary text-white shadow-md shadow-primary/20"
                        : "rounded-bl-sm border border-border bg-bg-surface text-text-primary"
                    }`}
                  >
                    {/* Header info for assistant */}
                    {msg.role === "assistant" && (
                      <div className="mb-2 flex items-center justify-between border-b border-border/40 pb-1.5 text-[11px] text-text-muted">
                        <span className="font-mono text-primary">
                          {msg.model || "Ollama AI"}
                        </span>
                        <div className="flex items-center gap-2">
                          {msg.latency_ms && (
                            <span>{msg.latency_ms}ms</span>
                          )}
                          <span>{msg.timestamp}</span>
                          <button
                            onClick={() => copyText(msg.id, msg.content)}
                            title="Copy text"
                            className="text-text-muted hover:text-white"
                          >
                            {copiedId === msg.id ? (
                              <Check size={12} className="text-emerald-400" />
                            ) : (
                              <Copy size={12} />
                            )}
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Message Body */}
                    <div className="prose prose-invert max-w-none text-sm leading-relaxed whitespace-pre-wrap font-sans break-words">
                      {msg.content}
                    </div>

                    {/* Timestamp for user */}
                    {msg.role === "user" && (
                      <div className="mt-1 text-right text-[10px] text-blue-200/70">
                        {msg.timestamp}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-white shadow-sm">
                    <Bot size={16} />
                  </div>
                  <div className="flex items-center gap-2.5 rounded-2xl rounded-bl-sm border border-border bg-bg-surface px-4 py-3 text-xs text-text-secondary">
                    <Loader2 size={15} className="animate-spin text-primary" />
                    <span>AI is generating response…</span>
                  </div>
                </div>
              )}

              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-border/70 bg-bg/80 p-3 backdrop-blur-sm sm:p-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="relative flex items-end gap-2"
          >
            <textarea
              ref={textareaRef}
              rows={2}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything (general knowledge, coding, writing, law, math, advice…) [Enter to send, Shift+Enter for newline]"
              className="max-h-36 min-h-[52px] flex-1 resize-none rounded-xl border border-border bg-bg-surface px-4 py-3 text-sm text-white placeholder-text-muted outline-none transition-all focus:border-primary focus:ring-1 focus:ring-primary/40"
            />
            <Button
              type="submit"
              disabled={loading || !input.trim()}
              className="h-[52px] w-[52px] shrink-0 rounded-xl"
            >
              {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
            </Button>
          </form>
          <div className="mt-2 flex items-center justify-between text-[11px] text-text-muted">
            <span>Powered by Local Ollama &bull; Private &amp; Offline-capable</span>
            <span className="hidden sm:inline">Press Enter to send, Shift+Enter for new line</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
