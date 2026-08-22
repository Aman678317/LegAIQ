"use client";

import { Download, FileWarning } from "lucide-react";
import type { RendererProps } from "../types";

const OFFICE_EMBED_LIMIT_BYTES = 10 * 1024 * 1024; // Microsoft's hard limit for the web viewer

/**
 * PowerPoint (.ppt/.pptx) and legacy Word (.doc): rendered through Microsoft's
 * Office web viewer, which requires a publicly reachable https URL and files
 * under 10 MB. Everything else (uploads, blobs, authenticated links) gets a
 * clear fallback with a download button — plug in a custom renderer for those.
 */
export function OfficeEmbedRenderer({ source, document, inspection, fileType }: RendererProps) {
  const isRemote = /^https?:\/\//i.test(source);
  const tooLarge = (inspection?.contentLength ?? 0) > OFFICE_EMBED_LIMIT_BYTES;

  if (isRemote && !tooLarge) {
    return (
      <iframe
        className="dv-frame"
        title={`${fileType.toUpperCase()} preview`}
        src={`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(source)}`}
      />
    );
  }

  return (
    <div className="dv-state">
      <FileWarning size={34} className="dv-state-icon" />
      <p className="dv-state-title">
        {fileType.toUpperCase()} preview needs a public URL
      </p>
      <p className="dv-state-message">
        {tooLarge
          ? "This file exceeds the 10 MB limit of Microsoft's Office web viewer."
          : "Microsoft's Office web viewer can only fetch publicly reachable https URLs — uploaded or authenticated files can't be previewed this way."}{" "}
        Pass a <code>renderers</code> entry for <code>{fileType}</code> to render it locally, or
        download the file below.
      </p>
      <a className="dv-button" href={source} download={document.fileName}>
        <Download size={14} /> Download file
      </a>
    </div>
  );
}

/** Anything unrecognized: friendly card + download + pointer to custom renderers. */
export function FallbackRenderer({ source, document, fileType }: RendererProps) {
  return (
    <div className="dv-state">
      <FileWarning size={34} className="dv-state-icon" />
      <p className="dv-state-title">No built-in preview for {fileType || "this file type"}</p>
      <p className="dv-state-message">
        Add a custom renderer via the <code>renderers</code> prop matching file type{" "}
        <code>{fileType || "unknown"}</code> to teach the viewer this format.
      </p>
      {source && (
        <a className="dv-button" href={source} download={document.fileName}>
          <Download size={14} /> Download file
        </a>
      )}
    </div>
  );
}
