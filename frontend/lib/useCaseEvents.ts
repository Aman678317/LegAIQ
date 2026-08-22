"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { createClient } from "@/lib/supabase";
import { api, isDemoMode } from "@/lib/api";

export interface JobEvent {
  id: string;
  job_type: string;
  state: string;
  progress: number;
  document_id: string | null;
  error_message: string | null;
  updated_at: string;
}

export interface DocumentEvent {
  id: string;
  file_name: string;
  status: string;
  page_count: number | null;
  ocr_confidence: number | null;
  error_message: string | null;
  badge_label?: string | null;
  badge_color?: string | null;
  updated_at: string;
}

type ConnectionStatus = "connecting" | "live" | "polling";

/**
 * Subscribes to real-time case updates via SSE, with automatic fallback
 * to interval polling if the stream drops (or demo mode).
 */
export function useCaseEvents(caseId: string | undefined, pollMs = 5000) {
  const [jobs, setJobs] = useState<Record<string, JobEvent>>({});
  const [documents, setDocuments] = useState<Record<string, DocumentEvent>>({});
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const applyJob = useCallback((job: JobEvent) => {
    setJobs((prev) => {
      if (prev[job.id]?.state === job.state && prev[job.id]?.progress === job.progress && prev[job.id]?.updated_at === job.updated_at) {
        return prev;
      }
      return { ...prev, [job.id]: job };
    });
  }, []);

  const applyDocument = useCallback((doc: DocumentEvent) => {
    setDocuments((prev) => {
      if (prev[doc.id]?.status === doc.status && prev[doc.id]?.updated_at === doc.updated_at) {
        return prev;
      }
      return { ...prev, [doc.id]: doc };
    });
  }, []);

  // Fallback poll
  const poll = useCallback(async () => {
    if (!caseId) return;
    try {
      if (isDemoMode(caseId)) {
        const docs = await api.listDocuments(caseId);
        const jobList = await api.listJobs(caseId);
        if (docs) {
          setDocuments((prev) => {
            const next = Object.fromEntries(docs.map((d: DocumentEvent) => [d.id, d]));
            const prevKeys = Object.keys(prev);
            const nextKeys = Object.keys(next);
            if (
              prevKeys.length === nextKeys.length &&
              prevKeys.every((k) => prev[k]?.status === next[k]?.status && prev[k]?.updated_at === next[k]?.updated_at)
            ) {
              return prev;
            }
            return next;
          });
        }
        if (jobList) {
          setJobs((prev) => {
            const next = Object.fromEntries(jobList.map((j: JobEvent) => [j.id, j]));
            const prevKeys = Object.keys(prev);
            const nextKeys = Object.keys(next);
            if (
              prevKeys.length === nextKeys.length &&
              prevKeys.every((k) => prev[k]?.state === next[k]?.state && prev[k]?.progress === next[k]?.progress)
            ) {
              return prev;
            }
            return next;
          });
        }
        setStatus("live");
        return;
      }

      const supabase = createClient();
      const [{ data: docRows }, { data: jobRows }] = await Promise.all([
        supabase.from("documents").select("id, file_name, status, page_count, ocr_confidence, error_message, updated_at").eq("case_id", caseId),
        supabase.from("jobs").select("id, job_type, state, progress, document_id, error_message, updated_at").eq("case_id", caseId).order("updated_at", { ascending: false }).limit(40),
      ]);
      if (docRows) {
        setDocuments((prev) => {
          const next = Object.fromEntries(docRows.map((d: DocumentEvent) => [d.id, d]));
          const prevKeys = Object.keys(prev);
          const nextKeys = Object.keys(next);
          if (
            prevKeys.length === nextKeys.length &&
            prevKeys.every((k) => prev[k]?.status === next[k]?.status && prev[k]?.updated_at === next[k]?.updated_at)
          ) {
            return prev;
          }
          return next;
        });
      }
      if (jobRows) {
        setJobs((prev) => {
          const next = Object.fromEntries(jobRows.map((j: JobEvent) => [j.id, j]));
          const prevKeys = Object.keys(prev);
          const nextKeys = Object.keys(next);
          if (
            prevKeys.length === nextKeys.length &&
            prevKeys.every((k) => prev[k]?.state === next[k]?.state && prev[k]?.progress === next[k]?.progress)
          ) {
            return prev;
          }
          return next;
        });
      }
    } catch {
      // ignore; next poll retries
    }
  }, [caseId]);

  useEffect(() => {
    if (!caseId) return;
    let es: EventSource | null = null;
    let cancelled = false;

    if (isDemoMode(caseId)) {
      // Use setTimeout to avoid synchronous setState in effect warning
      setTimeout(() => {
        setStatus("live");
        poll();
      }, 0);
      return () => {
        cancelled = true;
      };
    }

    async function connect() {
      try {
        const supabase = createClient();
        const { data: { session } } = await supabase.auth.getSession();
        if (!session || cancelled) {
          setStatus("polling");
          return;
        }

        const url = safeApiUrl(`/cases/${caseId}/events?token=${session.access_token}`);
        es = new EventSource(url);

        es.addEventListener("open", () => {
          if (!cancelled) setStatus("live");
          stopPolling();
        });

        es.addEventListener("state", (e: MessageEvent) => {
          const data = JSON.parse(e.data);
          setDocuments(Object.fromEntries((data.documents || []).map((d: DocumentEvent) => [d.id, d])));
          setJobs(Object.fromEntries((data.jobs || []).map((j: JobEvent) => [j.id, j])));
        });

        es.addEventListener("job", (e) => applyJob(JSON.parse((e as MessageEvent).data)));
        es.addEventListener("document", (e) => applyDocument(JSON.parse((e as MessageEvent).data)));

        es.addEventListener("error", () => {
          if (cancelled) return;
          setStatus("polling");
          es?.close();
          startPolling();
          setTimeout(() => {
            if (!cancelled) {
              stopPolling();
              connect();
            }
          }, 15000);
        });
      } catch {
        setStatus("polling");
        startPolling();
      }
    }

    function startPolling() {
      if (!pollRef.current) {
        poll();
        pollRef.current = setInterval(poll, pollMs);
      }
    }
    function stopPolling() {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }

    // Use setTimeout to avoid synchronous setState in effect warning
    setTimeout(() => poll(), 0);
    connect();

    return () => {
      cancelled = true;
      es?.close();
      stopPolling();
    };
  }, [caseId, pollMs, poll, applyJob, applyDocument]);

  const jobsList = useMemo(() => Object.values(jobs), [jobs]);
  const documentsList = useMemo(() => Object.values(documents), [documents]);

  return {
    jobs: jobsList,
    documents: documentsList,
    documentMap: documents,
    status,
  };
}
