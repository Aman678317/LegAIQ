/** File-kind detection and display-name resolution. Pure functions — easy to test. */

import type { ViewerDocument } from "./types";

/** Normalized file kinds used for renderer matching. */
export type FileKind =
  | "pdf"
  | "doc" | "docx"
  | "xls" | "xlsx"
  | "ppt" | "pptx"
  | "csv" | "tsv"
  | "txt" | "md" | "json" | "xml" | "log"
  | "png" | "jpg" | "jpeg" | "gif" | "webp" | "svg" | "bmp"
  | "html" | "htm"
  | "unknown";

const MIME_TO_KIND: Record<string, string> = {
  "application/pdf": "pdf",
  "application/msword": "doc",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
  "application/vnd.ms-excel": "xls",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
  "application/vnd.ms-powerpoint": "ppt",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
  "text/plain": "txt",
  "text/markdown": "md",
  "text/csv": "csv",
  "text/tab-separated-values": "tsv",
  "text/html": "html",
  "application/json": "json",
  "application/xml": "xml",
  "image/png": "png",
  "image/jpeg": "jpg",
  "image/gif": "gif",
  "image/webp": "webp",
  "image/svg+xml": "svg",
  "image/bmp": "bmp",
};

function extensionOf(name: string): string {
  const clean = name.split(/[?#]/)[0];
  const lastSegment = clean.slice(clean.lastIndexOf("/") + 1);
  const dot = lastSegment.lastIndexOf(".");
  return dot > 0 ? lastSegment.slice(dot + 1).toLowerCase() : "";
}

function isNamedFile(file?: File | Blob): file is File {
  return Boolean(file && "name" in file && typeof (file as File).name === "string");
}

/** Resolve the file kind: explicit fileType beats MIME beats extension beats unknown. */
export function detectKind(doc: ViewerDocument): string {
  if (doc.fileType) return doc.fileType.toLowerCase().replace(/^\./, "");
  if (doc.mimeType) {
    const kind = MIME_TO_KIND[doc.mimeType.split(";")[0].trim().toLowerCase()];
    if (kind) return kind;
    if (doc.mimeType.startsWith("image/")) return "png"; // any image kind → image renderer
  }
  if (isNamedFile(doc.file)) {
    const ext = extensionOf(doc.file.name);
    if (ext) return ext;
  }
  const ext = extensionOf(doc.fileName || doc.uri || "");
  if (ext) return ext;
  if (doc.mimeType?.startsWith("image/")) return "png";
  return "unknown";
}

/** Human-friendly display name for the sidebar/header. */
export function displayName(doc: ViewerDocument, index: number): string {
  return (
    doc.fileName ||
    (isNamedFile(doc.file) ? doc.file.name : "") ||
    decodeURIComponent(doc.uri?.split(/[?#]/)[0].split("/").pop() || "") ||
    `Document ${index + 1}`
  );
}

/** Stable id for controlled mode and list keys. */
export function documentId(doc: ViewerDocument, index: number): string {
  if (doc.id) return doc.id;
  if (isNamedFile(doc.file)) return `${doc.file.name}:${doc.file.size}:${doc.file.lastModified}`;
  return doc.uri || displayName(doc, index);
}

/** Convenience for uploads: wrap a File/Blob as a ViewerDocument. */
export function documentFromFile(file: File | Blob, id?: string): ViewerDocument {
  return {
    id,
    file,
    fileName: isNamedFile(file) ? file.name : undefined,
    mimeType: file.type || undefined,
  };
}

export const IMAGE_KINDS = ["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp"];
export const TEXT_KINDS = ["txt", "md", "json", "xml", "log"];

/** Group a kind into a coarse family for icons and labels. */
export function kindFamily(kind: string): "pdf" | "word" | "excel" | "powerpoint" | "text" | "csv" | "image" | "html" | "unknown" {
  if (kind === "pdf") return "pdf";
  if (kind === "doc" || kind === "docx") return "word";
  if (kind === "xls" || kind === "xlsx") return "excel";
  if (kind === "ppt" || kind === "pptx") return "powerpoint";
  if (TEXT_KINDS.includes(kind)) return "text";
  if (kind === "csv" || kind === "tsv") return "csv";
  if (IMAGE_KINDS.includes(kind)) return "image";
  if (kind === "html" || kind === "htm") return "html";
  return "unknown";
}
