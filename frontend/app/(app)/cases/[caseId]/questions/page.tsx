"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Send, Loader2, MessageSquare, FileText, Languages, Cpu, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { Card, Badge, Button } from "@/components/ui";
import { LANGUAGES } from "@/lib/utils";
import { checkOllamaStatus, OllamaStatus } from "@/lib/ollama";

const TAX_SUGGESTIONS = [
  "What was the main tax dispute?",
  "Explain Section 9(1)(i) and the 'Look At' doctrine.",
  "What are the withholding tax obligations under Section 195?",
  "Summarize the $11.1 Billion CGP Cayman share acquisition.",
  "What was the Supreme Court's ruling on Jan 20, 2012?",
  "What are the risks regarding retrospective tax amendments?",
];

const PROPERTY_SUGGESTIONS = [
  "Who is the current verified title holder?",
  "Show the complete chain of ownership.",
  "Explain the survey number mismatch between deeds.",
  "Which registered deed proves the boundary dimensions?",
  "What documents or encumbrance certificates are missing?",
  "What remedial steps should be taken at the Taluk Survey office?",
];

export default function QuestionsPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [asking, setAsking] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedLang, setSelectedLang] = useState("en");
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus>({
    online: false,
    models: [],
    activeModel: null,
  });
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [caseInfo, setCaseInfo] = useState<any>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 1. Fetch Chat History & Case Info
    Promise.all([
      api.getChatHistory(caseId),
      api.getCase(caseId).catch(() => null),
    ])
      .then(([msgs, c]) => {
        setMessages(msgs || []);
        setCaseInfo(c);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));

    // 2. Check local Ollama status
    checkOllamaStatus().then((status) => {
      setOllamaStatus(status);
      if (status.activeModel) {
        setSelectedModel(status.activeModel);
      }
    });
  }, [caseId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, asking]);

  async function ask(question: string) {
    if (!question.trim() || asking) return;
    setAsking(true);
    setError(null);
    setInput("");

    // Optimistic user message
    setMessages((m) => [...m, { id: `temp-${Date.now()}`, role: "user", content: question }]);

    try {
      const answer = await api.askQuestion(caseId, question, selectedLang, selectedModel || undefined);
      setMessages((m) => [...m, answer]);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setAsking(false);
    }
  }

  const isTax =
    caseInfo?.case_type === "TAX" ||
    caseInfo?.name?.toLowerCase().includes("vodafone") ||
    caseId?.toLowerCase().includes("vodafone");

  const suggestions = isTax ? TAX_SUGGESTIONS : PROPERTY_SUGGESTIONS;

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-4xl flex-col">
      {/* Header & Controls */}
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-semibold text-white">Questions & Legal AI Chat</h1>
          <p className="mt-1 text-xs text-text-secondary">
            Ask any question on any legal aspect. Powered by Local Ollama & Indian Legal Reasoner.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Ollama Status & Model Selector */}
          {ollamaStatus.online ? (
            <div className="flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs text-emerald-400">
              <Cpu size={13} className="animate-pulse text-emerald-400" />
              {ollamaStatus.models.length > 1 ? (
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="bg-transparent font-mono text-xs text-emerald-300 outline-none"
                >
                  {ollamaStatus.models.map((m) => (
                    <option key={m} value={m} className="bg-bg text-white">
                      Ollama: {m}
                    </option>
                  ))}
                </select>
              ) : (
                <span className="font-mono text-xs">Ollama: {ollamaStatus.activeModel || "Online"}</span>
              )}
            </div>
          ) : (
            <div
              className="flex items-center gap-1.5 rounded-lg border border-border bg-bg-elevated px-2.5 py-1 text-xs text-text-muted"
              title="Start Ollama locally ('ollama run llama3') on port 11434 to switch inference to your local GPU/CPU."
            >
              <Cpu size={13} className="text-primary" />
              <span>Local Legal AI Engine</span>
            </div>
          )}

          {/* Response Language Selector */}
          <div className="flex items-center gap-1.5 rounded-lg border border-border bg-bg px-2.5 py-1 text-xs text-white">
            <Languages size={13} className="text-primary" />
            <select
              value={selectedLang}
              onChange={(e) => setSelectedLang(e.target.value)}
              className="bg-transparent text-xs text-white outline-none"
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code} className="bg-bg text-white">
                  {l.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-xs text-red-400">{error}</div>
      )}

      {/* Messages Feed */}
      <Card className="mt-4 flex-1 overflow-y-auto p-5">
        {loading ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <MessageSquare size={36} className="mb-3 text-primary/60" />
            <h3 className="text-base font-semibold text-white">Ask anything about this case</h3>
            <p className="mt-1 max-w-md text-xs text-text-secondary">
              The AI answers with deep legal reasoning, statutory citations, and document evidence.
            </p>
            <div className="mt-6 flex max-w-xl flex-wrap justify-center gap-2">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => ask(s)}
                  className="rounded-full border border-border bg-bg-elevated px-3 py-1.5 text-xs text-text-secondary transition-colors hover:border-primary/50 hover:text-white"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            {messages.map((msg) => (
              <div key={msg.id} className={msg.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <div className={msg.role === "user" ? "max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-3" : "max-w-[92%] rounded-2xl rounded-bl-md border border-border bg-bg px-5 py-4"}>
                  {msg.role === "user" ? (
                    <p className="text-sm leading-relaxed text-white">{msg.content}</p>
                  ) : (
                    <>
                      <div className="mb-2 flex items-center justify-between border-b border-border/50 pb-2">
                        <div className="flex items-center gap-2">
                          <Sparkles size={13} className="text-primary" />
                          <span className="text-xs font-medium text-primary">Jurisiva Legal Intelligence</span>
                        </div>
                        {selectedLang !== "en" && (
                          <Badge className="border-border bg-bg-elevated text-[11px] text-text-muted">
                            {LANGUAGES.find((l) => l.code === selectedLang)?.label}
                          </Badge>
                        )}
                      </div>
                      <pre className="whitespace-pre-wrap text-sm leading-relaxed text-text-secondary font-sans">{msg.content}</pre>
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="mt-4 border-t border-border/60 pt-3">
                          <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                            Evidentiary Citations & Sources
                          </p>
                          <div className="space-y-1.5">
                            {msg.citations.map((c: any, i: number) => (
                              <div key={i} className="flex items-start gap-2 rounded-lg border border-border/40 bg-bg-elevated/40 px-3 py-1.5 text-xs">
                                <FileText size={13} className="mt-0.5 shrink-0 text-primary" />
                                <span className="text-text-secondary">
                                  <span className="font-medium text-white">{c.document_name}</span> · p.{c.page_number} — &ldquo;{c.source_text?.slice(0, 120)}…&rdquo;
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}
            {asking && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2.5 rounded-2xl border border-border bg-bg px-4 py-3">
                  <Loader2 size={15} className="animate-spin text-primary" />
                  <span className="text-xs text-text-muted">Analyzing case record & generating response…</span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </Card>

      {/* Suggestion Bar */}
      {messages.length > 0 && (
        <div className="mt-2 flex gap-1.5 overflow-x-auto pb-1 text-xs text-text-muted">
          {suggestions.slice(0, 4).map((s) => (
            <button
              key={s}
              onClick={() => ask(s)}
              className="shrink-0 rounded-full border border-border/60 bg-bg px-3 py-1 text-[11px] text-text-secondary transition-colors hover:border-primary/50 hover:text-white"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <form
        onSubmit={(e) => { e.preventDefault(); ask(input); }}
        className="mt-2 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={`Ask anything about this case (${selectedLang !== "en" ? LANGUAGES.find((l) => l.code === selectedLang)?.label : "parties, statutes, tax dispute, precedents"}…)`}
          className="flex-1 rounded-xl border border-border bg-bg-surface px-4 py-3 text-sm text-white placeholder-text-muted outline-none transition-colors focus:border-primary"
        />
        <button
          type="submit"
          disabled={asking || !input.trim()}
          className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-white transition-colors hover:bg-primary-hover disabled:opacity-40"
        >
          {asking ? <Loader2 size={17} className="animate-spin" /> : <Send size={17} />}
        </button>
      </form>
    </div>
  );
}
