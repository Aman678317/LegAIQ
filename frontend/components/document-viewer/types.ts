/**
 * Public types for the DocumentViewer component.
 *
 * The component is intentionally self-contained: no UI framework beyond React,
 * no CSS framework — all styling comes from the scoped stylesheet in theme.ts
 * and CSS custom properties, so it can be dropped into any app.
 */

export type ViewerDocument = {
  /** Stable id. Generated from fileName/uri when omitted; used by controlled mode. */
  id?: string;
  /** Remote (http/https), blob:, data:, or app-relative URL. */
  uri?: string;
  /** Local file from an upload or drag-and-drop. Rendered via an object URL. */
  file?: File | Blob;
  fileName?: string;
  /** Extension override, e.g. "pdf". Wins over every other detection signal. */
  fileType?: string;
  /** MIME type hint; used as a detection fallback. */
  mimeType?: string;
};

export type ThemeTokens = {
  /** Accent color for active states, links, and icons. */
  primary: string;
  /** Page background behind the whole viewer. */
  background: string;
  /** Sidebar and header surface color. */
  surface: string;
  /** Content viewport background (where the document renders). */
  panel: string;
  text: string;
  textMuted: string;
  border: string;
  /** Selection/hover highlight in the sidebar. */
  hover: string;
};

export type ThemePreset = "light" | "dark" | "sepia" | "ocean";

/** A named preset, token overrides on top of a preset, or full tokens. */
export type ViewerTheme = ThemePreset | (Partial<ThemeTokens> & { preset?: ThemePreset });

/**
 * Request customization. Inspection runs a cheap request against remote
 * documents before rendering (to read Content-Type/Content-Length); some hosts
 * reject HEAD, so the method is configurable. The same options feed the
 * `request()` helper handed to renderers.
 */
export type RequestOptions = {
  /** Method for the inspection request. Default "HEAD". Use "GET" for hosts that reject HEAD. */
  inspectMethod?: "HEAD" | "GET";
  /** Extra init (headers, credentials…) for the inspection request. */
  inspectInit?: RequestInit | ((doc: ViewerDocument) => RequestInit);
  /** Init used by renderers when they fetch document bytes. */
  requestInit?: RequestInit | ((doc: ViewerDocument) => RequestInit);
  /** Replace the fetch entirely, e.g. to sign URLs or use an authenticated client. */
  requestFile?: (doc: ViewerDocument, init: RequestInit) => Promise<Response>;
};

export type InspectionResult = {
  contentType: string;
  contentLength: number | null;
};

/** Everything a renderer needs. Stable identity for `request` per active document. */
export type RendererProps = {
  document: ViewerDocument;
  /** URL ready for src attributes (uri, or an object URL created from `file`). */
  source: string;
  /** Normalized file kind, e.g. "pdf" | "docx" | "csv" — see detect.ts. */
  fileType: string;
  /** Configured fetch for this document's bytes (respects RequestOptions). */
  request: () => Promise<Response>;
  /** Result of the inspection request when one ran (remote docs only). */
  inspection: InspectionResult | null;
  theme: ThemeTokens;
};

export type DocumentRenderer = {
  name: string;
  /** File kinds this renderer handles; first match wins (custom before defaults). */
  fileTypes: string[];
  Renderer: React.ComponentType<RendererProps>;
};

export type WatermarkConfig = {
  viewerEmail?: string;
  viewerIp?: string;
  label?: string;
};

export type DocumentViewerProps = {
  documents: ViewerDocument[];
  /** Uncontrolled: which document is active on mount (id, uri, fileName, or the object). */
  initialActive?: string | ViewerDocument;
  /** Controlled: pass an id (or document) and the viewer follows it. */
  active?: string | ViewerDocument;
  onActiveChange?: (document: ViewerDocument, index: number) => void;
  /** Custom renderers; matched by fileType before the built-in set. */
  renderers?: DocumentRenderer[];
  requestOptions?: RequestOptions;
  theme?: ViewerTheme;
  /** Show/hide the document sidebar. Default true. */
  showSidebar?: boolean;
  /** Overlay a confidential-style watermark over the rendered document. */
  watermark?: boolean | WatermarkConfig;
  className?: string;
  style?: React.CSSProperties;
};
