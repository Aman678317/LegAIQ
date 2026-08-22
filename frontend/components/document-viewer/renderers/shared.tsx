"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

/** Loading spinner used by every async renderer. */
export function RendererLoading({ label = "Loading document…" }: { label?: string }) {
  return (
    <div className="dv-state" role="status" aria-live="polite">
      <div className="dv-spinner" />
      <p className="dv-state-message">{label}</p>
    </div>
  );
}

/** Error panel with retry + practical hints (CORS, request method). */
export function RendererError({ error = "The request failed or was blocked.", onRetry }: { error?: string; onRetry?: () => void }) {
  return (
    <div className="dv-state" role="alert">
      <AlertTriangle size={30} className="dv-state-icon" />
      <p className="dv-state-title">Couldn&apos;t load this document</p>
      <p className="dv-state-message">
        {error}
        <br />
        If this is a remote file, the host may be blocking cross-origin requests or the
        request method. Try <code>requestOptions.inspectMethod</code> /{" "}
        <code>requestOptions.requestInit</code>, or provide <code>requestFile</code>.
      </p>
      {onRetry && (
        <button type="button" className="dv-button" onClick={onRetry}>
          <RefreshCw size={14} /> Retry
        </button>
      )}
    </div>
  );
}

/**
 * Small async loader for renderers: loading/error/ready states plus retry.
 * `key` drives reloading (e.g. the document uri) instead of an object dep.
 * Entries are keyed to (key, nonce), so "loading" is derived — no state is
 * set synchronously inside the effect body.
 */
export function useRendererData<T>(load: () => Promise<T>, key: string) {
  type Entry<T> = { key: string; nonce: number; status: "ready" | "error"; data?: T; error?: string };
  const [entry, setEntry] = useState<Entry<T> | null>(null);
  const [nonce, setNonce] = useState(0);
  const retry = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    let live = true;
    load()
      .then((data) => {
        if (live) setEntry({ key, nonce, status: "ready", data });
      })
      .catch((err: unknown) => {
        if (live) setEntry({ key, nonce, status: "error", error: err instanceof Error ? err.message : String(err) });
      });
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, nonce]);

  const current = entry && entry.key === key && entry.nonce === nonce ? entry : null;
  const state: { status: "loading" | "ready" | "error"; data?: T; error?: string } =
    current ? { status: current.status, data: current.data, error: current.error } : { status: "loading" };
  return { state, retry };
}
