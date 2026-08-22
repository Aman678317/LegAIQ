/** Public API for the DocumentViewer component. */
export { DocumentViewer } from "./DocumentViewer";
export { WatermarkOverlay } from "./WatermarkOverlay";
export { defaultRenderers } from "./renderers";
export {
  detectKind,
  displayName,
  documentFromFile,
  documentId,
  kindFamily,
  IMAGE_KINDS,
  TEXT_KINDS,
} from "./detect";
export { parseDelimited } from "./csv";
export { THEME_PRESETS, resolveTheme } from "./theme";
export type {
  DocumentRenderer,
  DocumentViewerProps,
  InspectionResult,
  RendererProps,
  RequestOptions,
  ThemePreset,
  ThemeTokens,
  ViewerDocument,
  ViewerTheme,
  WatermarkConfig,
} from "./types";
