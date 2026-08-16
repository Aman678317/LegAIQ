"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Send, Loader2, MessageSquare, FileText } from "lucide-react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui";

const SUGGESTIONS = [
  "Who is the current owner?",
  "Show the ownership history.",
  "Which document proves ownership?",
  "What is the survey number?",
  "Is there a mismatch between documents?",
  "What documents are missing?",
  "What should I verify?",
];

export default function QuestionsPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [asking, setAsking] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getChatHistory(caseId)
      .then(setMessages)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
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
      const answer = await api.askQuestion(caseId, question);
      setMessages((m) => [...m, answer]);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-4xl flex-col">
      <div>
        <h1 className="text-2xl font-semibold text-white">Questions</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Ask anything about this case. Answers come only from uploaded documents, with citations.
        </p>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {/* Messages */}
      <Card className="mt-6 flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <MessageSquare size={32} className="mb-3 text-text-muted" />
            <h3 className="text-base font-semibold text-white">Ask your first question</h3>
            <p className="mt-1 max-w-md text-sm text-text-secondary">
              The assistant answers strictly from your uploaded documents.
              If information isn&rsquo;t there, it will say so.
            </p>
            <div className="mt-6 flex max-w-lg flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => ask(s)}
                  className="rounded-full border border-border bg-bg-elevated px-3.5 py-1.5 text-xs text-text-secondary transition-colors hover:border-primary/40 hover:text-white"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {messages.map((msg) => (
              <div key={msg.id} className={msg.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <div className={msg.role === "user" ? "max-w-[85%] rounded-2xl rounded-br-md bg-primary px-5 py-3.5" : "max-w-[90%] rounded-2xl rounded-bl-md border border-border bg-bg px-5 py-3.5"}>
                  {msg.role === "user" ? (
                    <p className="text-sm leading-relaxed text-white">{msg.content}</p>
                  ) : (
                    <>
                      <pre className="whitespace-pre-wrap text-sm leading-relaxed text-text-secondary">{msg.content}</pre>
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="mt-3 border-t border-border pt-3">
                          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                            Sources
                          </p>
                          <div className="space-y-1.5">
                            {msg.citations.map((c: any, i: number) => (
                              <div key={i} className="flex items-start gap-2 text-xs">
                                <FileText size={12} className="mt-0.5 shrink-0 text-primary" />
                                <span className="text-text-secondary">
                                  {c.document_name} · p.{c.page_number} — &ldquo;{c.source_text?.slice(0, 100)}…&rdquo;
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
                <div className="flex items-center gap-2 rounded-2xl border border-border bg-bg px-5 py-3.5">
                  <div className="flex gap-1">
                    {[0, 1, 2].map((i) => (
                      <div key={i} className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-primary" style={{ animationDelay: `${i * 0.2}s` }} />
                    ))}
                  </div>
                  <span className="text-xs text-text-muted">Searching documents…</span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </Card>

      {/* Input */}
      <form
        onSubmit={(e) => { e.preventDefault(); ask(input); }}
        className="mt-4 flex gap-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about parties, survey numbers, ownership, dates…"
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
