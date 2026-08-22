"use client";

import type { RendererProps } from "../types";
import { RendererError, RendererLoading, useRendererData } from "./shared";

/** PDFs: the browser's native viewer via iframe. Works for http(s), blob:, and data:. */
export function PdfRenderer({ source }: RendererProps) {
  if (!source) return <RendererLoading label="Preparing PDF…" />;
  return <iframe className="dv-frame" title="PDF preview" src={source} />;
}

/** Images: centered, transparency-friendly checkerboard behind the image. */
export function ImageRenderer({ source, document }: RendererProps) {
  if (!source) return <RendererLoading label="Preparing image…" />;
  return (
    <div className="dv-image-wrap">
      {/* Plain <img> on purpose: the component stays framework-agnostic and the
          src is usually a blob/data URL where next/image adds no value. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="dv-image" src={source} alt={document.fileName || "Document image"} />
    </div>
  );
}

/**
 * HTML: sandboxed iframe. Scripts are intentionally NOT enabled; styles and
 * markup render, which is the right trade-off for untrusted documents.
 */
export function HtmlRenderer({ source }: RendererProps) {
  if (!source) return <RendererLoading label="Preparing HTML…" />;
  return <iframe className="dv-frame" title="HTML preview" sandbox="allow-same-origin" src={source} />;
}

/** Plain text (txt/md/json/xml/log): fetched through the configured request. */
export function TextRenderer({ request }: RendererProps) {
  const { state, retry } = useRendererData(() => request().then((res) => res.text()), "text");
  if (state.status === "loading") return <RendererLoading label="Reading text…" />;
  if (state.status === "error") return <RendererError error={state.error} onRetry={retry} />;
  return <pre className="dv-text">{state.data}</pre>;
}
