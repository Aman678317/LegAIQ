/** The default renderer set, ordered by precedence. Custom renderers win. */

import type { DocumentRenderer } from "../types";
import { CsvRenderer } from "./CsvRenderer";
import { DocxRenderer } from "./DocxRenderer";
import { FallbackRenderer, OfficeEmbedRenderer } from "./OfficeEmbedRenderer";
import { HtmlRenderer, ImageRenderer, PdfRenderer, TextRenderer } from "./native";
import { XlsxRenderer } from "./XlsxRenderer";

export const defaultRenderers: DocumentRenderer[] = [
  { name: "PDF", fileTypes: ["pdf"], Renderer: PdfRenderer },
  { name: "Word", fileTypes: ["docx"], Renderer: DocxRenderer },
  { name: "Excel", fileTypes: ["xlsx", "xls"], Renderer: XlsxRenderer },
  { name: "PowerPoint", fileTypes: ["ppt", "pptx", "doc"], Renderer: OfficeEmbedRenderer },
  { name: "Image", fileTypes: ["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp"], Renderer: ImageRenderer },
  { name: "HTML", fileTypes: ["html", "htm"], Renderer: HtmlRenderer },
  { name: "CSV", fileTypes: ["csv", "tsv"], Renderer: CsvRenderer },
  { name: "Text", fileTypes: ["txt", "md", "json", "xml", "log"], Renderer: TextRenderer },
  { name: "Fallback", fileTypes: ["unknown"], Renderer: FallbackRenderer },
];

export {
  CsvRenderer,
  DocxRenderer,
  FallbackRenderer,
  HtmlRenderer,
  ImageRenderer,
  OfficeEmbedRenderer,
  PdfRenderer,
  TextRenderer,
  XlsxRenderer,
};
