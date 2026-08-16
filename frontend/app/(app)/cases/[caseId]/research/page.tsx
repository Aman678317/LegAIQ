"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Search, Loader2, ExternalLink, ShieldCheck, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { formatDateTime } from "@/lib/utils";

export default function ResearchPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [sessions, setSessions] = useState<any[]>([]);
  const [question, setQuestion] = useState("");
  const [researching, setResearching] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sourcesBySession, setSourcesBySession] = useState<Record<string, any[]>>({});

  async function load() {
    try {
      setSessions(await api.listResearch(caseId));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [caseId]);

  async function runResearch(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || researching) return;
    setResearching(true);
    setError(null);
    try {
      await api.startResearch(caseId, question);
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
    // Convert [Source: URL] patterns to clickable links
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

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Legal Research</h1>
        <p className="mt-1 text-sm text-text-secondary">
          The research agent searches authoritative Indian sources and cites what it finds.
          It never fabricates citations.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      <form onSubmit={runResearch} className="flex gap-3">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g., What is the limitation period for suit for partition in Karnataka?"
          className="flex-1 rounded-xl border border-border bg-bg-surface px-4 py-3 text-sm text-white placeholder-text-muted outline-none focus:border-primary"
        />
        <Button type="submit" disabled={researching || !question.trim()}>
          {researching ? <Loader2 size={15} className="animate-spin" /> : <Search size={15} />}
          Research
        </Button>
      </form>

      {loading ? (
        <div className="flex h-48 items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
        </div>
      ) : sessions.length === 0 ? (
        <Card className="flex flex-col items-center p-12 text-center">
          <Search size={32} className="mb-3 text-text-muted" />
          <h3 className="text-base font-semibold text-white">No research yet</h3>
          <p className="mt-2 max-w-md text-sm text-text-secondary">
            Ask a legal question above. The agent plans a search, retrieves sources,
            verifies what it can, and answers with citations.
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
                <h3 className="text-sm font-semibold text-white">{session.question}</h3>
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

              {session.jurisdiction && (
                <p className="mt-1 text-xs text-text-muted">Jurisdiction: {session.jurisdiction}</p>
              )}
              <p className="text-xs text-text-muted">{formatDateTime(session.created_at)}</p>

              {session.answer && (
                <div className="mt-4 whitespace-pre-wrap border-t border-border pt-4 text-sm leading-relaxed text-text-secondary">
                  {renderAnswer(session.answer)}
                </div>
              )}

              {sourcesBySession[session.id] && sourcesBySession[session.id].length > 0 && (
                <div className="mt-4 border-t border-border pt-4">
                  <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                    Sources ({sourcesBySession[session.id].length})
                  </p>
                  <div className="space-y-1.5">
                    {sourcesBySession[session.id].map((s: any) => (
                      <div key={s.id} className="flex items-center gap-2 text-xs">
                        {s.verified ? (
                          <ShieldCheck size={12} className="shrink-0 text-emerald-400" />
                        ) : (
                          <ShieldAlert size={12} className="shrink-0 text-amber-400" />
                        )}
                        <a
                          href={s.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="truncate text-text-secondary hover:text-white"
                        >
                          {s.title}
                        </a>
                        <span className="shrink-0 text-text-muted">· {new URL(s.url).hostname}</span>
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
  );
}
