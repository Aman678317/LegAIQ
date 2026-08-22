"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Download,
  ExternalLink,
  File,
  FileImage,
  FileSpreadsheet,
  FileText,
  Globe,
  Presentation,
  Table,
} from "lucide-react";
import { detectKind, displayName, documentId, kindFamily } from "./detect";
import { defaultRenderers } from "./renderers";
import { ensureStylesheet, resolveTheme, themeStyle } from "./theme";
import type {
  DocumentViewerProps,
  InspectionResult,
  RendererProps,
  ViewerDocument,
} from "./types";
import { useDocumentSource } from "./useObjectUrl";
import { WatermarkOverlay } from "./WatermarkOverlay";

/** File-type icon. Static branches — no component aliasing during render. */
function KindIcon({ kind, size, color }: { kind: string; size: number; color?: string }) {
  const style = color ? { color } : undefined;
  switch (kindFamily(kind)) {
    case "excel":
      return <FileSpreadsheet size={size} style={style} />;
    case "powerpoint":
      return <Presentation size={size} style={style} />;
    case "csv":
      return <Table size={size} style={style} />;
    case "image":
      return <FileImage size={size} style={style} />;
    case "html":
      return <Globe size={size} style={style} />;
    case "pdf":
    case "word":
    case "text":
      return <FileText size={size} style={style} />;
    default:
      return <File size={size} style={style} />;
  }
}

function resolveInit(
  init: RequestInit | ((doc: ViewerDocument) => RequestInit) | undefined,
  doc: ViewerDocument,
): RequestInit {
  return typeof init === "function" ? init(doc) : init ?? {};
}

/** Match a selection (id / uri / fileName / document object) to an index. */
function matchIndex(documents: ViewerDocument[], selection?: string | ViewerDocument): number {
  if (selection === undefined) return -1;
  if (typeof selection === "string") {
    return documents.findIndex(
      (doc, i) => doc.id === selection || doc.uri === selection || displayName(doc, i) === selection,
    );
  }
  const wanted = documentId(selection, -1);
  return documents.findIndex((doc, i) => documentId(doc, i) === wanted);
}

/**
 * DocumentViewer — display PDFs, Word, Excel, PowerPoint, text, CSV, images,
 * and HTML from remote URLs or local files, with a themed chrome, pluggable
 * renderers, and configurable requests. See README.md for the full API.
 */
export function DocumentViewer({
  documents,
  initialActive,
  active,
  onActiveChange,
  renderers = [],
  requestOptions,
  theme,
  showSidebar = true,
  watermark = false,
  className = "",
  style,
}: DocumentViewerProps) {
  ensureStylesheet();
  const tokens = useMemo(() => resolveTheme(theme), [theme]);

  const ids = useMemo(() => documents.map((doc, i) => documentId(doc, i)), [documents]);
  const [internalId, setInternalId] = useState<string>(() => {
    const matched = matchIndex(documents, initialActive);
    return matched >= 0 ? ids[matched] : ids[0] ?? "";
  });

  const isControlled = active !== undefined;
  const activeIndex = useMemo(() => {
    if (isControlled) {
      const matched = matchIndex(documents, active);
      if (matched >= 0) return matched;
    }
    const byId = ids.indexOf(internalId);
    return byId >= 0 ? byId : 0;
  }, [active, documents, ids, internalId, isControlled]);

  const activeDocument = documents[activeIndex];
  const source = useDocumentSource(activeDocument?.uri, activeDocument?.file);
  const fileType = activeDocument ? detectKind(activeDocument) : "unknown";
  const docKey = ids[activeIndex] ?? "";

  // Inspection results are keyed to the document they belong to, so switching
  // documents never shows a stale badge without needing a reset effect.
  const [inspectionEntry, setInspectionEntry] = useState<{ key: string; result: InspectionResult | null } | null>(null);
  const inspection = inspectionEntry?.key === docKey ? inspectionEntry.result : null;

  const select = useCallback(
    (index: number) => {
      const doc = documents[index];
      if (!doc) return;
      if (!isControlled) setInternalId(ids[index]);
      if (onActiveChange) onActiveChange(doc, index);
    },
    [documents, ids, isControlled, onActiveChange],
  );

  /** Configured fetch for document bytes — used by text/csv/docx/xlsx renderers. */
  const request = useCallback(async () => {
    if (!activeDocument) throw new Error("No active document");
    if (activeDocument.file) return new Response(activeDocument.file);
    const init = resolveInit(requestOptions?.requestInit, activeDocument);
    return requestOptions?.requestFile
      ? requestOptions.requestFile(activeDocument, init)
      : fetch(source, init);
  }, [activeDocument, requestOptions, source]);

  /**
   * Inspect remote documents before rendering (Content-Type/Content-Length).
   * HEAD first when not explicitly configured; fall back to GET on 405/501
   * because plenty of hosts (and signed-URL services) reject HEAD.
   */
  useEffect(() => {
    if (!activeDocument?.uri || activeDocument.file || !/^https?:\/\//i.test(activeDocument.uri)) return;
    if (!requestOptions) return;

    let live = true;
    const run = async (method: string) => {
      const init = { ...resolveInit(requestOptions.inspectInit, activeDocument), method };
      return requestOptions.requestFile
        ? requestOptions.requestFile(activeDocument, init)
        : fetch(activeDocument.uri!, init);
    };
    const read = (res: Response): InspectionResult | null => ({
      contentType: (res.headers.get("content-type") || "").split(";")[0].trim(),
      contentLength: Number(res.headers.get("content-length")) || null,
    });

    (async () => {
      const record = (result: InspectionResult | null) => {
        if (live) setInspectionEntry({ key: docKey, result });
      };
      const method = requestOptions.inspectMethod ?? "HEAD";
      try {
        const res = await run(method);
        if (!live) return;
        if ((res.status === 405 || res.status === 501) && !requestOptions.inspectMethod && method === "HEAD") {
          const retry = await run("GET");
          if (live && retry.ok) record(read(retry));
          return;
        }
        if (res.ok) record(read(res));
      } catch {
        /* inspection is best-effort; renderers surface real load failures */
      }
    })();

    return () => {
      live = false;
    };
  }, [activeDocument, docKey, requestOptions]);

  const renderer = useMemo(
    () => [...renderers, ...defaultRenderers].find((entry) => entry.fileTypes.includes(fileType)),
    [fileType, renderers],
  );

  if (!activeDocument) {
    return <div className={`dv-empty ${className}`} style={{ ...themeStyle(tokens), ...style }}>No documents to display.</div>;
  }

  const badge =
    inspection?.contentType ||
    activeDocument.mimeType ||
    (fileType !== "unknown" ? fileType.toUpperCase() : "");

  const rendererProps: RendererProps = {
    document: activeDocument,
    source,
    fileType,
    request,
    inspection,
    theme: tokens,
  };
  const Renderer = renderer?.Renderer ?? defaultRenderers[defaultRenderers.length - 1].Renderer;

  return (
    <section
      className={`dv-root ${className}`}
      style={{ ...themeStyle(tokens), ...style }}
      data-document-viewer=""
    >
      <div className="dv-body">
        {showSidebar && documents.length > 0 && (
          <nav className="dv-sidebar" aria-label="Documents" onKeyDown={(e) => {
            if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
            e.preventDefault();
            const next = e.key === "ArrowDown" ? activeIndex + 1 : activeIndex - 1;
            if (next >= 0 && next < documents.length) select(next);
          }}>
            <div className="dv-sidebar-title">
              Documents <span style={{ opacity: 0.7 }}>({documents.length})</span>
            </div>
            {documents.map((doc, index) => {
              const kind = detectKind(doc);
              return (
                <button
                  key={ids[index] || index}
                  type="button"
                  className="dv-doc-button"
                  data-active={index === activeIndex}
                  aria-current={index === activeIndex}
                  onClick={() => select(index)}
                  title={displayName(doc, index)}
                >
                  <KindIcon kind={kind} size={15} color={index === activeIndex ? tokens.primary : undefined} />
                  <span className="dv-doc-name">{displayName(doc, index)}</span>
                </button>
              );
            })}
          </nav>
        )}

        <div className="dv-main">
          <header className="dv-header">
            <div className="dv-header-left">
              <KindIcon kind={fileType} size={17} color={tokens.primary} />
              <span className="dv-file-name" title={displayName(activeDocument, activeIndex)}>
                {displayName(activeDocument, activeIndex)}
              </span>
              {badge && <span className="dv-badge">{badge}</span>}
            </div>
            <div className="dv-header-actions">
              {source && (
                <>
                  <a className="dv-icon-button" href={source} download={activeDocument.fileName} aria-label="Download document" title="Download">
                    <Download size={16} />
                  </a>
                  <a className="dv-icon-button" href={source} target="_blank" rel="noreferrer" aria-label="Open in new tab" title="Open in new tab">
                    <ExternalLink size={16} />
                  </a>
                </>
              )}
            </div>
          </header>

          <div className="dv-content">
            {source || !activeDocument.file ? (
              <Renderer key={`${ids[activeIndex]}:${fileType}`} {...rendererProps} />
            ) : (
              <div className="dv-state"><div className="dv-spinner" /></div>
            )}
            <WatermarkOverlay config={watermark} />
          </div>
        </div>
      </div>
    </section>
  );
}
