"use client";

import { useEffect, useRef, useState } from "react";
import type { RendererProps } from "../types";
import { RendererError, RendererLoading, useRendererData } from "./shared";

type DocxModule = { renderAsync: (data: Blob | ArrayBuffer, container: HTMLElement) => Promise<unknown> };

/** Load docx-preview once, on first use, so it stays out of the main bundle. */
let docxLib: Promise<DocxModule> | null = null;
function loadDocxLib(): Promise<DocxModule> {
  docxLib ??= import("docx-preview").then((mod) => mod as unknown as DocxModule);
  return docxLib;
}

/**
 * Word (.docx): rendered fully client-side with docx-preview, so uploaded and
 * authenticated documents work without a public URL. Legacy binary .doc files
 * are handled by the Office embed renderer instead.
 */
export function DocxRenderer({ request }: RendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [libError, setLibError] = useState<string | null>(null);
  const { state, retry } = useRendererData(
    () => Promise.all([loadDocxLib(), request().then((res) => res.arrayBuffer())]),
    "docx",
  );

  useEffect(() => {
    const container = containerRef.current;
    if (state.status !== "ready" || !container || !state.data) return;
    const [lib, buffer] = state.data;
    container.replaceChildren();
    lib.renderAsync(buffer, container).catch((err: unknown) =>
      setLibError(err instanceof Error ? err.message : String(err)),
    );
    return () => container.replaceChildren();
  }, [state]);

  useEffect(() => {
    loadDocxLib().catch((err: unknown) => setLibError(err instanceof Error ? err.message : String(err)));
  }, []);

  if (libError) return <RendererError error={`docx-preview failed: ${libError}`} onRetry={retry} />;
  if (state.status === "loading") return <RendererLoading label="Rendering Word document…" />;
  if (state.status === "error") return <RendererError error={state.error} onRetry={retry} />;

  return (
    <div className="dv-docx-scroll">
      <div ref={containerRef} className="dv-office-page" />
    </div>
  );
}
