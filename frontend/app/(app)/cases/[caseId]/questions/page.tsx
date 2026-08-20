"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import {
  Send, Loader2, MessageSquare, FileText, Languages, Cpu, Sparkles,
  HelpCircle, Scale, PenTool, CheckCircle2, ShieldCheck, ExternalLink,
  ChevronRight, X, BookOpen, AlertTriangle
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, Badge, Button } from "@/components/ui";
import { LANGUAGES } from "@/lib/utils";
import { checkOllamaStatus, OllamaStatus } from "@/lib/ollama";

type ChatMode = "ask" | "analyze" | "draft";

const MODE_CONFIG: Record<ChatMode, { label: string; icon: any; description: string; badge: string; color: string }> = {
  ask: {
    label: "Ask",
    icon: HelpCircle,
    description: "Direct, crisp legal Q&A with pinpoint document and statutory citations",
    badge: "Direct Q&A",
    color: "from-blue-600 to-indigo-600",
  },
  analyze: {
    label: "Analyze",
    icon: Scale,
    description: "Deep FIRAC legal reasoning, issue spotting, statutory scrutiny, and risk matrix",
    badge: "Deep FIRAC Reasoning",
    color: "from-purple-600 to-violet-600",
  },
  draft: {
    label: "Draft",
    icon: PenTool,
    description: "Court-ready petitions, legal notices, sale deed clauses, and verification affidavits",
    badge: "Legal Drafting Studio",
    color: "from-emerald-600 to-teal-600",
  },
};

const SUGGESTIONS_BY_MODE: Record<ChatMode, { tax: string[]; property: string[] }> = {
  ask: {
    tax: [
      "What was the core tax dispute in Vodafone v. UOI?",
      "Explain Section 9(1)(i) and the 'Look At' doctrine.",
      "What are the withholding tax obligations under Section 195?",
      "What was the Supreme Court's ruling on Jan 20, 2012?",
    ],
    property: [
      "Who is the current verified title holder?",
      "Show the complete chain of ownership across all deeds.",
      "Explain the survey number mismatch between deeds.",
      "What documents or encumbrance certificates are missing?",
    ],
  },
  analyze: {
    tax: [
      "Perform structured FIRAC analysis on offshore share transfer nexus under Section 9(1)(i).",
      "Evaluate retrospective tax amendment exposure under BSA 2023 evidence standards.",
      "Conduct risk matrix assessment on Section 201 'assessee-in-default' penalties.",
      "Analyze extraterritorial jurisdictional limitations of Indian Revenue authorities.",
    ],
    property: [
      "Perform exhaustive FIRAC breakdown on Survey No. 124/3 boundary and area discrepancies.",
      "Audit admissibility of historical 1987 deed under Bharatiya Sakshya Adhiniyam 2023 Section 63.",
      "Evaluate risk profile for agricultural land conversion under Karnataka Land Revenue Act Section 95.",
      "Analyze legal implications of uncertified pencil entries in Mutation Register (Form 6).",
    ],
  },
  draft: {
    tax: [
      "Draft a Writ Petition under Article 226 before High Court of Bombay quashing Section 201 Notice.",
      "Draft formal Representation to the Assessing Officer invoking Supreme Court ruling (2012) 6 SCC 613.",
      "Draft an Indemnity & Tax Gross-Up Clause for cross-border Share Purchase Agreement.",
      "Draft a Stay of Demand Application under Section 220(6) of Income Tax Act.",
    ],
    property: [
      "Draft formal Section 106 Transfer of Property Act Legal Notice for boundary rectification.",
      "Draft an Interlocutory Application under CPC Order XXXIX Rules 1 & 2 for Temporary Injunction.",
      "Draft comprehensive Title Search & Due Diligence Clause with Seller Indemnity warranty.",
      "Draft Mutation Application before the jurisdictional Tahsildar / Talathi under State Revenue Code.",
    ],
  },
};

export default function QuestionsPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [asking, setAsking] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // M1: 3-Mode switcher state
  const [mode, setMode] = useState<ChatMode>("ask");

  // M1: India Context toggle state
  const [indiaContext, setIndiaContext] = useState<boolean>(true);

  // M1: Multi-LLM model selector state
  const [selectedModel, setSelectedModel] = useState<string>("claude-3-5-sonnet");
  const [selectedLang, setSelectedLang] = useState("en");
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus>({
    online: false,
    models: [],
    activeModel: null,
  });

  const [caseInfo, setCaseInfo] = useState<any>(null);
  const [previewDoc, setPreviewDoc] = useState<{ name: string; page: number; snippet?: string } | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
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

    checkOllamaStatus().then((status) => {
      setOllamaStatus(status);
      if (status.online && status.activeModel) {
        // Keep default or allow local
      }
    });
  }, [caseId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, asking]);

  async function ask(questionText: string) {
    const trimmed = questionText.trim();
    if (!trimmed || asking) return;
    setAsking(true);
    setError(null);
    setInput("");

    const userMsgId = `user-${Date.now()}`;
    const streamingMsgId = `streaming-${userMsgId}`;

    setMessages((m) => [
      ...m,
      { id: userMsgId, role: "user", content: trimmed, mode, created_at: new Date().toISOString() },
      { id: streamingMsgId, role: "assistant", content: "", citations: [], mode, isStreaming: true },
    ]);

    try {
      let fullContent = "";
      const answer = await api.askQuestionStream(
        caseId,
        trimmed,
        selectedLang,
        selectedModel || undefined,
        (chunk) => {
          fullContent += chunk;
          setMessages((m) =>
            m.map((msg) =>
              msg.id === streamingMsgId ? { ...msg, content: fullContent } : msg
            )
          );
        },
        {
          mode,
          india_context: indiaContext,
        }
      );

      setMessages((m) => m.filter((msg) => msg.id !== streamingMsgId));
      setMessages((m) => [
        ...m,
        {
          ...answer,
          mode,
          india_context: indiaContext,
          model: selectedModel,
        },
      ]);
    } catch (e: any) {
      setError(e.message || "Failed to generate AI response");
      setMessages((m) => m.filter((msg) => msg.id !== streamingMsgId));
    } finally {
      setAsking(false);
    }
  }

  const isTax =
    caseInfo?.case_type === "TAX" ||
    caseInfo?.name?.toLowerCase().includes("vodafone") ||
    caseId?.toLowerCase().includes("vodafone");

  const currentSuggestions = isTax ? SUGGESTIONS_BY_MODE[mode].tax : SUGGESTIONS_BY_MODE[mode].property;

  // Render text with interactive inline clickable citation chips
  const renderMessageContent = (content: string, citations?: any[]) => {
    if (!content) return null;

    // Pattern matching [Doc: filename, Pg: N], [Doc: filename, Page: N], or [Document: filename, Page: N]
    const citationRegex = /\[(?:Doc|Document):\s*([^,\]]+),\s*(?:Pg|Page):\s*([0-9]+)\]/gi;
    const parts = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = citationRegex.exec(content)) !== null) {
      const matchIndex = match.index;
      if (matchIndex > lastIndex) {
        parts.push(content.slice(lastIndex, matchIndex));
      }
      const docName = match[1].trim();
      const pageNum = parseInt(match[2].trim(), 10) || 1;

      // Find matching citation source text if available
      const matchedCitation = citations?.find(
        (c) => c.document_name?.toLowerCase().includes(docName.toLowerCase()) || docName.toLowerCase().includes(c.document_name?.toLowerCase() || "")
      );

      parts.push(
        <button
          key={`cite-${matchIndex}`}
          type="button"
          onClick={() => setPreviewDoc({ name: docName, page: pageNum, snippet: matchedCitation?.source_text })}
          className="mx-1 inline-flex items-center gap-1 rounded-md border border-primary/40 bg-primary/15 px-2 py-0.5 text-xs font-medium text-blue-300 transition-all hover:border-primary hover:bg-primary/30 hover:text-white"
          title={`Click to inspect evidence in ${docName}, Page ${pageNum}`}
        >
          <FileText size={11} className="shrink-0 text-primary" />
          <span>{docName} · p.{pageNum}</span>
        </button>
      );
      lastIndex = matchIndex + match[0].length;
    }

    if (lastIndex < content.length) {
      parts.push(content.slice(lastIndex));
    }

    return <div className="whitespace-pre-wrap leading-relaxed">{parts}</div>;
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-7.5rem)] max-w-5xl flex-col">
      {/* Top Header & Global Controls */}
      <div className="flex flex-col gap-3 border-b border-border/80 pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">Assistant & Legal Chat Workspace</h1>
            <Badge className="border-primary/40 bg-primary/10 text-xs font-semibold text-primary">
              Harvey-Class AI
            </Badge>
          </div>
          <p className="mt-1 text-xs text-text-secondary">
            Unified multi-mode reasoning workspace grounded in Indian statutes (BNS, BNSS, BSA 2023, CPC, RERA) with live SSE streaming.
          </p>
        </div>

        {/* Runtime Model & Language Selectors */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Multi-LLM Runtime Model Selector */}
          <div className="flex items-center gap-1.5 rounded-lg border border-border bg-bg-elevated px-2.5 py-1.5 text-xs text-white shadow-sm">
            <Cpu size={14} className={ollamaStatus.online ? "animate-pulse text-emerald-400" : "text-primary"} />
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="cursor-pointer bg-transparent text-xs font-medium text-white outline-none"
            >
              <optgroup label="Cloud Legal Frontier Models" className="bg-bg text-white">
                <option value="claude-3-5-sonnet">Claude 3.5 Sonnet (High Precision Legal)</option>
                <option value="gpt-4o">GPT-4o (Enterprise Legal Reasoner)</option>
                <option value="deepseek-r1">DeepSeek R1 (Deep Legal CoT Logic)</option>
              </optgroup>
              <optgroup label="Local / Private Sovereign Models" className="bg-bg text-white">
                <option value="llama3.1:70b">Llama 3.1 70B (Private On-Premises)</option>
                <option value="llama3.1:8b">Llama 3.1 8B (Fast Local Assistant)</option>
                {ollamaStatus.online &&
                  ollamaStatus.models.map((m) => (
                    <option key={m} value={m} className="text-emerald-400">
                      Ollama Local: {m}
                    </option>
                  ))}
              </optgroup>
            </select>
          </div>

          {/* Response Language */}
          <div className="flex items-center gap-1.5 rounded-lg border border-border bg-bg px-2.5 py-1.5 text-xs text-white">
            <Languages size={13} className="text-primary" />
            <select
              value={selectedLang}
              onChange={(e) => setSelectedLang(e.target.value)}
              className="cursor-pointer bg-transparent text-xs text-white outline-none"
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

      {/* Mode Switcher Bar & India Context Toggle */}
      <div className="mt-3 flex flex-col gap-3 rounded-xl border border-border/70 bg-bg-surface/80 p-3 sm:flex-row sm:items-center sm:justify-between">
        {/* 3-Mode Switcher */}
        <div className="flex items-center gap-1.5 rounded-lg bg-bg p-1">
          {(["ask", "analyze", "draft"] as ChatMode[]).map((mKey) => {
            const mConfig = MODE_CONFIG[mKey];
            const Icon = mConfig.icon;
            const isActive = mode === mKey;
            return (
              <button
                key={mKey}
                onClick={() => setMode(mKey)}
                className={`flex items-center gap-2 rounded-md px-3.5 py-1.5 text-xs font-medium transition-all ${
                  isActive
                    ? "bg-primary text-white shadow-md shadow-primary/20"
                    : "text-text-secondary hover:bg-bg-elevated hover:text-white"
                }`}
              >
                <Icon size={14} className={isActive ? "text-white" : "text-text-muted"} />
                <span>{mConfig.label}</span>
              </button>
            );
          })}
        </div>

        {/* India Context Toggle */}
        <div className="flex items-center gap-3">
          <label className="flex cursor-pointer items-center gap-2 text-xs font-medium text-white">
            <input
              type="checkbox"
              checked={indiaContext}
              onChange={(e) => setIndiaContext(e.target.checked)}
              className="h-4 w-4 rounded border-border bg-bg text-primary focus:ring-primary cursor-pointer"
            />
            <div className="flex items-center gap-1.5">
              <ShieldCheck size={14} className={indiaContext ? "text-emerald-400" : "text-text-muted"} />
              <span className={indiaContext ? "text-emerald-300 font-semibold" : "text-text-muted"}>
                India Statutory Context
              </span>
            </div>
          </label>

          {indiaContext && (
            <div className="hidden flex-wrap items-center gap-1 xl:flex">
              <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-400 border border-emerald-500/20">
                BNS/BNSS 2023
              </span>
              <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-400 border border-emerald-500/20">
                BSA Sec 63
              </span>
              <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-400 border border-emerald-500/20">
                CPC Order 39
              </span>
              <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-400 border border-emerald-500/20">
                RERA / IBC
              </span>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="mt-2.5 flex items-center justify-between rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-xs text-red-400">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Messages Feed */}
      <Card className="mt-3 flex-1 overflow-y-auto p-5 shadow-inner">
        {loading ? (
          <div className="flex h-full flex-col items-center justify-center gap-2">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <p className="text-xs text-text-muted">Loading matter intelligence workspace…</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className={`mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br ${MODE_CONFIG[mode].color} text-white shadow-lg`}>
              {mode === "ask" && <HelpCircle size={28} />}
              {mode === "analyze" && <Scale size={28} />}
              {mode === "draft" && <PenTool size={28} />}
            </div>
            <h3 className="text-lg font-bold text-white">{MODE_CONFIG[mode].badge}</h3>
            <p className="mt-1.5 max-w-md text-xs text-text-secondary leading-relaxed">
              {MODE_CONFIG[mode].description}
            </p>

            {/* Mode-specific Quick Start Prompts */}
            <div className="mt-6 w-full max-w-2xl">
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                Recommended {MODE_CONFIG[mode].label} Prompts for this Case
              </p>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {currentSuggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => ask(s)}
                    className="flex items-start gap-2 rounded-xl border border-border/80 bg-bg-elevated/50 p-3 text-left text-xs text-text-secondary transition-all hover:border-primary/60 hover:bg-bg-elevated hover:text-white"
                  >
                    <ChevronRight size={13} className="mt-0.5 shrink-0 text-primary" />
                    <span className="line-clamp-2 leading-relaxed">{s}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            {messages.map((msg) => (
              <div key={msg.id} className={msg.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <div
                  className={
                    msg.role === "user"
                      ? "max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-3 text-white shadow-md"
                      : "max-w-[94%] rounded-2xl rounded-bl-md border border-border bg-bg p-5 text-text-primary shadow-sm"
                  }
                >
                  {msg.role === "user" ? (
                    <div>
                      <div className="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-blue-200">
                        <span>Mode: {(msg.mode || mode).toUpperCase()}</span>
                      </div>
                      <p className="text-sm leading-relaxed text-white">{msg.content}</p>
                    </div>
                  ) : (
                    <>
                      {/* Assistant Header */}
                      <div className="mb-3 flex flex-wrap items-center justify-between border-b border-border/60 pb-2.5">
                        <div className="flex items-center gap-2">
                          <Sparkles size={14} className="text-primary" />
                          <span className="text-xs font-bold text-white">Jurisiva Legal Intelligence</span>
                          <span className="rounded bg-primary/20 px-2 py-0.5 text-[10px] font-semibold text-primary uppercase">
                            {(msg.mode || mode)} mode
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          {indiaContext && (
                            <Badge className="border-emerald-500/30 bg-emerald-500/10 text-[10px] font-medium text-emerald-400">
                              ✓ India Statutes Grounded
                            </Badge>
                          )}
                          {selectedLang !== "en" && (
                            <Badge className="border-border bg-bg-elevated text-[10px] text-text-muted">
                              {LANGUAGES.find((l) => l.code === selectedLang)?.label}
                            </Badge>
                          )}
                        </div>
                      </div>

                      {/* Content with Inline Clickable Citations */}
                      <div className="text-sm leading-relaxed text-text-secondary font-sans">
                        {renderMessageContent(msg.content, msg.citations)}
                      </div>

                      {/* Evidentiary Citations Footer */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="mt-4 border-t border-border/60 pt-3">
                          <div className="mb-2 flex items-center justify-between">
                            <p className="text-[11px] font-bold uppercase tracking-wider text-text-muted">
                              Evidentiary Citations & Sources ({msg.citations.length})
                            </p>
                            <span className="text-[10px] text-text-muted">Click snippet to view page</span>
                          </div>
                          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                            {msg.citations.map((c: any, i: number) => (
                              <button
                                key={i}
                                type="button"
                                onClick={() => setPreviewDoc({ name: c.document_name, page: c.page_number, snippet: c.source_text })}
                                className="flex items-start gap-2.5 rounded-lg border border-border/60 bg-bg-elevated/40 p-2.5 text-left text-xs transition-colors hover:border-primary/60 hover:bg-bg-elevated"
                              >
                                <FileText size={14} className="mt-0.5 shrink-0 text-primary" />
                                <div className="min-w-0 flex-1">
                                  <div className="flex items-center justify-between">
                                    <span className="font-semibold text-white truncate">{c.document_name} · p.{c.page_number}</span>
                                    <span className="rounded bg-primary/20 px-1.5 py-0.2 text-[10px] font-medium text-blue-300">
                                      Page {c.page_number}
                                    </span>
                                  </div>
                                  <p className="mt-1 line-clamp-2 text-[11px] text-text-secondary">
                                    &ldquo;{c.source_text}&rdquo;
                                  </p>
                                </div>
                              </button>
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
                <div className="flex items-center gap-3 rounded-2xl border border-border bg-bg px-4 py-3 shadow-sm">
                  <Loader2 size={16} className="animate-spin text-primary" />
                  <span className="text-xs text-text-secondary font-medium">
                    {mode === "draft"
                      ? "Synthesizing legal clauses & drafting document…"
                      : mode === "analyze"
                      ? "Cross-examining evidence & conducting FIRAC analysis…"
                      : "Reasoning with Indian statutes & retrieving citations…"}
                  </span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </Card>

      {/* Suggestion Bar */}
      {messages.length > 0 && (
        <div className="mt-2 flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
          <span className="shrink-0 text-[10px] font-bold uppercase tracking-wider text-text-muted">
            Suggestions:
          </span>
          {currentSuggestions.slice(0, 4).map((s) => (
            <button
              key={s}
              onClick={() => ask(s)}
              className="shrink-0 rounded-full border border-border/80 bg-bg px-3 py-1 text-[11px] text-text-secondary transition-colors hover:border-primary/60 hover:text-white"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input Box */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
        className="mt-2 flex gap-2"
      >
        <div className="relative flex-1">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              mode === "draft"
                ? "Instruct drafting: e.g., 'Draft an Interim Injunction application under CPC Order XXXIX Rules 1 & 2'…"
                : mode === "analyze"
                ? "Request deep analysis: e.g., 'Analyze the 13-year title chain and highlight break risks'…"
                : "Ask about parties, survey numbers, boundaries, title chain or legal risks…"
            }
            className="w-full rounded-xl border border-border bg-bg-surface px-4 py-3 text-sm text-white placeholder-text-muted outline-none transition-colors focus:border-primary focus:ring-1 focus:ring-primary shadow-sm"
          />
        </div>
        <button
          type="submit"
          disabled={asking || !input.trim()}
          className="flex h-11 w-12 items-center justify-center rounded-xl bg-primary text-white transition-all hover:bg-primary-hover disabled:opacity-40 shadow-md shadow-primary/20"
        >
          {asking ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
        </button>
      </form>

      {/* Document Evidence Viewer Modal */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-6 backdrop-blur-sm">
          <div className="flex h-full max-h-[85vh] w-full max-w-3xl flex-col rounded-2xl border border-border bg-bg-surface shadow-2xl">
            <div className="flex items-center justify-between border-b border-border px-6 py-4">
              <div className="flex items-center gap-2.5">
                <FileText size={18} className="text-primary" />
                <div>
                  <h3 className="text-sm font-bold text-white">{previewDoc.name}</h3>
                  <p className="text-xs text-text-muted">Evidence Inspector · Page {previewDoc.page}</p>
                </div>
              </div>
              <button
                onClick={() => setPreviewDoc(null)}
                className="rounded-lg p-1.5 text-text-muted hover:bg-bg-elevated hover:text-white"
              >
                <X size={18} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              <div className="rounded-xl border border-primary/30 bg-primary/10 p-4">
                <div className="mb-1.5 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-primary">
                  <CheckCircle2 size={14} /> Grounded Evidence Citation
                </div>
                <p className="text-xs text-blue-200">
                  This citation links directly to Page {previewDoc.page} of <strong>{previewDoc.name}</strong> as verified evidence in the case matter vault.
                </p>
              </div>

              {previewDoc.snippet && (
                <Card className="p-4 border-border">
                  <div className="mb-2 text-[11px] font-bold uppercase tracking-wider text-text-muted">
                    Source Text Snippet
                  </div>
                  <blockquote className="border-l-2 border-primary pl-3 font-mono text-xs leading-relaxed text-text-secondary">
                    &ldquo;{previewDoc.snippet}&rdquo;
                  </blockquote>
                </Card>
              )}

              <div className="rounded-xl border border-border bg-bg p-4 text-xs text-text-secondary">
                <div className="mb-1 font-semibold text-white">Bharatiya Sakshya Adhiniyam 2023 Note:</div>
                Electronic records and OCR extracts in this vault are certified with SHA-256 integrity hashes under Section 63 of BSA 2023 for admissibility.
              </div>
            </div>

            <div className="flex items-center justify-end border-t border-border px-6 py-3">
              <Button size="sm" variant="secondary" onClick={() => setPreviewDoc(null)}>
                Close Preview
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
