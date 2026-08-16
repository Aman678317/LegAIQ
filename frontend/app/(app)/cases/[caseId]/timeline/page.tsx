"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Clock, Loader2, FileText } from "lucide-react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui";

export default function TimelinePage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getTimeline(caseId)
      .then(setEvents)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [caseId]);

  if (loading) {
    return <div className="flex h-96 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Property Timeline</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Chronological events extracted from documents. Click an event to see its source.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {events.length === 0 ? (
        <Card className="flex flex-col items-center p-12 text-center">
          <Clock size={32} className="mb-3 text-text-muted" />
          <h3 className="text-base font-semibold text-white">No timeline events yet</h3>
          <p className="mt-2 max-w-md text-sm text-text-secondary">
            Timeline events appear when documents with dated transactions (registrations,
            sales, mutations) are processed.
          </p>
        </Card>
      ) : (
        <div className="relative space-y-0 pl-8">
          {/* Vertical line */}
          <div className="absolute bottom-2 left-3 top-2 w-px bg-border-light" />

          {events.map((event, i) => (
            <div key={event.id} className="relative pb-8">
              {/* Node */}
              <div className={`absolute -left-[1.35rem] top-1 h-3 w-3 rounded-full border-2 border-bg ${
                i === events.length - 1 ? "bg-primary" : "bg-border-light"
              }`} />

              <Card className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-blue-300">
                        {event.transaction_type}
                      </span>
                      {event.event_date && (
                        <span className="text-xs font-medium text-white">
                          {new Date(event.event_date).toLocaleDateString("en-IN", {
                            day: "numeric", month: "long", year: "numeric",
                          })}
                        </span>
                      )}
                    </div>
                    <p className="mt-2 text-sm leading-relaxed text-white">{event.description}</p>
                    {event.party && (
                      <p className="mt-1 text-xs text-text-secondary">Party: {event.party}</p>
                    )}
                  </div>
                  {event.confidence != null && (
                    <span className="shrink-0 text-xs text-text-muted">
                      {(event.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                </div>

                {(event.evidence_text || event.documents) && (
                  <div className="mt-3 rounded-lg border border-border bg-bg px-3 py-2">
                    <div className="flex items-center gap-1.5 text-[11px] text-text-muted">
                      <FileText size={11} />
                      {event.documents?.file_name || "Document"}
                      {event.page_number ? ` · p.${event.page_number}` : ""}
                    </div>
                    {event.evidence_text && (
                      <p className="mt-1 font-mono text-[11px] text-emerald-400">
                        &ldquo;{event.evidence_text.slice(0, 180)}&rdquo;
                      </p>
                    )}
                  </div>
                )}
              </Card>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
