"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  Search,
  Loader2,
  ExternalLink,
  ShieldCheck,
  ShieldAlert,
  Cpu,
  Languages,
  Sparkles,
  BookOpen,
  Scale,
} from "lucide-react";
import { api } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { formatDateTime, LANGUAGES } from "@/lib/utils";
import { checkOllamaStatus, OllamaStatus } from "@/lib/ollama";
import { downloadDraftFile } from "@/lib/reportExporter";
import { KanoonSearchPanel } from "@/components/research/KanoonSearchPanel";

const TAX_RESEARCH_PROMPTS = [
  "What is the ratio decidendi in Vodafone International Holdings ((2012) 6 SCC 613)?",
  "Analyze Section 195 withholding tax on offshore payments to non-residents.",
  "What was the legal effect of Taxation Laws (Amendment) Act 2021 on retrospective tax?",
  "How does the 'Look At' doctrine apply to multi-tiered foreign holding structures?",
];

const PROPERTY_RESEARCH_PROMPTS = [
  "What is the legal effect of a survey number mismatch between deeds in Karnataka?",
  "What is the limitation period for filing a suit for partition under the Limitation Act 1963?",
  "Can oral evidence contradict registered conveyance terms under the Indian Evidence Act / BSA?",
  "What is the evidentiary value of an unmutated RTC revenue record in property title disputes?",
];

export default function ResearchPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [tab, setTab] = useState<"kanoon" | "assistant">("kanoon");
  const [sessions, setSessions] = useState<any[]>([]);
  const [question, setQuestion] = useState("");
  const [researching, setResearching] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sourcesBySession, setSourcesBySession] = useState<Record<string, any[]>>({});
  const [selectedLang, setSelectedLang] = useState("en");
  const [caseInfo, setCaseInfo] = useState<any>(null);
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus>({
    online: false,
    models: [],
    activeModel: null,
  });
  const [selectedModel, setSelectedModel] = useState<string>("");

  async function load() {
    try {
      const [resList, c] = await Promise.all([
        api.listResearch(caseId),
        api.getCase(caseId).catch(() => null),
      ]);
      setSessions(resList);
      setCaseInfo(c);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    checkOllamaStatus().then((status) => {
      setOllamaStatus(status);
      if (status.activeModel) setSelectedModel(status.activeModel);
    });
  }, [caseId]);

  async function runResearch(qText?: string) {
    const q = (qText || question).trim();
    if (!q || researching) return;
    setResearching(true);
    setError(null);
    try {
      await api.startResearch(caseId, q, "India", selectedLang, selectedModel || undefined);
      setQuestion("");
      await load();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setResearching(false);
    }
  }

  async function loadSources(sessionId: string) {
    if (sourcesBySession[sessionId]) return;
    try {
      const sources = await api.researchSources(sessionId);
      setSourcesBySession((prev) => ({ ...prev, [sessionId]: sources }));
    } catch {
      setSourcesBySession((prev) => ({ ...prev, [sessionId]: [] }));
    }
  }

  function renderAnswer(text: string) {
    const parts = text.split(/(\[Source:\s*[^\]]+\])/g);
    return parts.map((part, i) => {
      const match = part.match(/\[Source:\s*(https?:\/\/[^\]]+)\]/);
      if (match) {
        return (
          <a
            key={i}
            href={match[1]}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300"
          >
            <ExternalLink size={11} />
            {new URL(match[1]).hostname}
          </a>
        );
      }
      return <span key={i}>{part}</span>;
    });
  }

  const isTax =
    caseInfo?.case_type === "TAX" ||
    caseInfo?.name?.toLowerCase().includes("vodafone") ||
    caseId?.toLowerCase().includes("vodafone");

  const prompts = isTax ? TAX_RESEARCH_PROMPTS : PROPERTY_RESEARCH_PROMPTS;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-semibold text-white">Legal Research &amp; Kanoon Intelligence</h1>
          <p className="mt-1 text-xs text-text-secondary">
            Indian Kanoon precedent citation network, Supreme Court ratio decidendi, and verified statutory citations.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-border bg-surface p-1">
            <button
              onClick={() => setTab("kanoon")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-semibold transition-colors ${
                tab === "kanoon" ? "bg-primary text-white" : "text-text-secondary hover:text-white"
              }`}
            >
              <Scale size={13} /> Indian Kanoon Network
            </button>
            <button
              onClick={() => setTab("assistant")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-semibold transition-colors ${
                tab === "assistant" ? "bg-primary text-white" : "text-text-secondary hover:text-white"
              }`}
            >
              <BookOpen size={13} /> Research Memos
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {tab === "kanoon" ? (
        <KanoonSearchPanel />
      ) : (
        <div className="space-y-6">
          {/* Search Bar */}
          <form onSubmit={(e) => { e.preventDefault(); runResearch(); }} className="flex gap-3">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={
                isTax
                  ? "e.g., What is the scope of Section 9(1)(i) regarding indirect transfers under Indian Income Tax Act?"
                  : "e.g., What is the limitation period for suit for partition in Karnataka?"
              }
              className="flex-1 rounded-xl border border-border bg-bg-surface px-4 py-3.5 text-sm text-white placeholder-text-muted outline-none focus:border-primary"
            />
            <Button type="submit" disabled={researching || !question.trim()}>
              {researching ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
              Research Memo
            </Button>
          </form>

          {/* Suggested Prompts */}
          <div className="flex flex-wrap gap-2">
            {prompts.map((p) => (
              <button
                key={p}
                onClick={() => runResearch(p)}
                className="rounded-full border border-border/70 bg-bg px-3.5 py-1.5 text-xs text-text-secondary transition-colors hover:border-primary/50 hover:text-white"
              >
                <Sparkles size={11} className="mr-1.5 inline text-primary" />
                {p}
              </button>
            ))}
          </div>

          {/* Research Output Cards */}
          {loading ? (
            <div className="flex h-48 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : sessions.length === 0 ? (
            <Card className="flex flex-col items-center p-12 text-center">
              <BookOpen size={36} className="mb-3 text-text-muted" />
              <h3 className="text-base font-semibold text-white">No research sessions yet</h3>
              <p className="mt-2 max-w-md text-xs text-text-secondary">
                Select a legal prompt above or enter a custom proposition. The research agent analyzes Indian statutes and binding Supreme Court precedents.
              </p>
            </Card>
          ) : (
            <div className="space-y-4">
              {sessions.map((session) => (
                <Card
                  key={session.id}
                  className="p-6"
                  onMouseEnter={() => session.status === "COMPLETED" && loadSources(session.id)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h3 className="text-base font-semibold text-white">{session.question}</h3>
                      <div className="mt-1 flex items-center gap-3 text-xs text-text-muted">
                        {session.jurisdiction && <span>Jurisdiction: {session.jurisdiction}</span>}
                        <span>·</span>
                        <span>{formatDateTime(session.created_at)}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {session.status === "COMPLETED" && (
                        <div className="flex items-center gap-1">
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => downloadDraftFile({ title: `Legal Research Memo: ${session.question}`, content: session.answer }, "pdf")}
                            title="Download / Print as PDF"
                          >
                            PDF
                          </Button>
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => downloadDraftFile({ title: `Legal Research Memo: ${session.question}`, content: session.answer }, "doc")}
                            title="Download Word (.doc) memo"
                          >
                            Word
                          </Button>
                        </div>
                      )}
                      <Badge className={
                        session.status === "COMPLETED"
                          ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-400"
                          : session.status === "RUNNING"
                          ? "border-blue-500/30 bg-blue-500/15 text-blue-400"
                          : "border-red-500/30 bg-red-500/15 text-red-400"
                      }>
                        {session.status}
                      </Badge>
                    </div>
                  </div>

                  {session.answer && (
                    <div className="mt-4 whitespace-pre-wrap border-t border-border pt-4 text-sm leading-relaxed text-text-secondary">
                      {renderAnswer(session.answer)}
                    </div>
                  )}

                  {/* Authoritative Sources */}
                  {sourcesBySession[session.id] && sourcesBySession[session.id].length > 0 && (
                    <div className="mt-5 border-t border-border/60 pt-4">
                      <p className="mb-2.5 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                        Authoritative Citations &amp; Legal Repositories ({sourcesBySession[session.id].length})
                      </p>
                      <div className="space-y-2">
                        {sourcesBySession[session.id].map((s: any) => (
                          <div key={s.id} className="flex items-center justify-between rounded-lg border border-border/40 bg-bg px-3.5 py-2 text-xs">
                            <div className="flex items-center gap-2 truncate">
                              {s.verified ? (
                                <ShieldCheck size={14} className="shrink-0 text-emerald-400" />
                              ) : (
                                <ShieldAlert size={14} className="shrink-0 text-amber-400" />
                              )}
                              <a
                                href={s.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="truncate text-white hover:text-primary hover:underline"
                              >
                                {s.title}
                              </a>
                            </div>
                            <span className="shrink-0 text-text-muted">{new URL(s.url).hostname}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
