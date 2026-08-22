/**
 * Theming: named presets plus token overrides, applied through CSS custom
 * properties on the viewer root. The stylesheet below is injected once and is
 * fully scoped under `.dv-root` — no CSS framework required in the host app.
 */

import type { ThemePreset, ThemeTokens, ViewerTheme } from "./types";

export const THEME_PRESETS: Record<ThemePreset, ThemeTokens> = {
  light: {
    primary: "#2563eb",
    background: "#ffffff",
    surface: "#f8fafc",
    panel: "#ffffff",
    text: "#0f172a",
    textMuted: "#64748b",
    border: "#e2e8f0",
    hover: "#f1f5f9",
  },
  dark: {
    primary: "#60a5fa",
    background: "#0f172a",
    surface: "#1e293b",
    panel: "#0b1222",
    text: "#e2e8f0",
    textMuted: "#94a3b8",
    border: "#334155",
    hover: "#24334a",
  },
  sepia: {
    primary: "#b45309",
    background: "#f7f0e3",
    surface: "#efe6d3",
    panel: "#fbf6ec",
    text: "#43302b",
    textMuted: "#8a7360",
    border: "#e0d2b8",
    hover: "#f1e7d2",
  },
  ocean: {
    primary: "#0e7490",
    background: "#f0f9ff",
    surface: "#e0f2fe",
    panel: "#ffffff",
    text: "#082f49",
    textMuted: "#0369a1",
    border: "#bae6fd",
    hover: "#e0f2fe",
  },
};

export function resolveTheme(theme?: ViewerTheme): ThemeTokens {
  if (!theme) return THEME_PRESETS.light;
  if (typeof theme === "string") return THEME_PRESETS[theme] ?? THEME_PRESETS.light;
  const base = (theme as Partial<ThemeTokens> & { preset?: ThemePreset }).preset
    ? THEME_PRESETS[(theme as { preset: ThemePreset }).preset]
    : THEME_PRESETS.light;
  return { ...base, ...theme };
}

export function themeStyle(theme: ThemeTokens): React.CSSProperties {
  return {
    "--dv-primary": theme.primary,
    "--dv-background": theme.background,
    "--dv-surface": theme.surface,
    "--dv-panel": theme.panel,
    "--dv-text": theme.text,
    "--dv-text-muted": theme.textMuted,
    "--dv-border": theme.border,
    "--dv-hover": theme.hover,
  } as React.CSSProperties;
}

let stylesheetInjected = false;

/** Inject the component stylesheet once per document. Safe under React strict mode. */
export function ensureStylesheet(): void {
  if (stylesheetInjected || typeof document === "undefined") return;
  const style = document.createElement("style");
  style.id = "document-viewer-styles";
  style.textContent = STYLESHEET;
  document.head.appendChild(style);
  stylesheetInjected = true;
}

const STYLESHEET = `
.dv-root {
  background: var(--dv-background); color: var(--dv-text);
  border: 1px solid var(--dv-border); border-radius: 0.85rem;
  overflow: hidden; box-shadow: 0 1px 2px rgb(0 0 0 / 0.06);
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
.dv-root *, .dv-root *::before, .dv-root *::after { box-sizing: border-box; }
.dv-body { display: flex; min-height: 34rem; height: 100%; }

/* Sidebar */
.dv-sidebar { width: 15rem; flex-shrink: 0; background: var(--dv-surface); border-right: 1px solid var(--dv-border); overflow-y: auto; }
.dv-sidebar-title { padding: 0.75rem 1rem 0.5rem; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase; color: var(--dv-text-muted); }
.dv-doc-button { display: flex; width: 100%; align-items: center; gap: 0.55rem; padding: 0.65rem 0.85rem; border: 0; border-bottom: 1px solid var(--dv-border); background: transparent; text-align: left; cursor: pointer; color: var(--dv-text-muted); font: inherit; font-size: 0.85rem; }
.dv-doc-button:hover { background: var(--dv-hover); }
.dv-doc-button[data-active="true"] { background: var(--dv-panel); color: var(--dv-text); font-weight: 600; box-shadow: inset 3px 0 0 var(--dv-primary); }
.dv-doc-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; min-width: 0; }

/* Main column */
.dv-main { display: flex; flex: 1; min-width: 0; flex-direction: column; }
.dv-header { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; padding: 0.65rem 1rem; border-bottom: 1px solid var(--dv-border); background: var(--dv-surface); }
.dv-header-left { display: flex; min-width: 0; align-items: center; gap: 0.5rem; }
.dv-file-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.875rem; font-weight: 600; }
.dv-badge { flex-shrink: 0; border-radius: 999px; border: 1px solid var(--dv-border); background: var(--dv-panel); color: var(--dv-text-muted); padding: 0.1rem 0.5rem; font-size: 0.65rem; font-weight: 600; }
.dv-header-actions { display: flex; flex-shrink: 0; align-items: center; gap: 0.15rem; }
.dv-icon-button { display: inline-flex; align-items: center; justify-content: center; padding: 0.4rem; border: 0; border-radius: 0.45rem; background: transparent; color: var(--dv-text-muted); cursor: pointer; }
.dv-icon-button:hover { background: var(--dv-hover); color: var(--dv-text); }
.dv-content { position: relative; flex: 1; min-height: 0; background: var(--dv-panel); }

/* Renderers */
.dv-frame { width: 100%; height: 100%; border: 0; display: block; background: #fff; }
.dv-image-wrap { display: flex; height: 100%; align-items: center; justify-content: center; overflow: auto; padding: 1.5rem; background-image: linear-gradient(45deg, rgb(0 0 0 / 0.03) 25%, transparent 25%, transparent 75%, rgb(0 0 0 / 0.03) 75%), linear-gradient(45deg, rgb(0 0 0 / 0.03) 25%, transparent 25%, transparent 75%, rgb(0 0 0 / 0.03) 75%); background-size: 1.25rem 1.25rem; background-position: 0 0, 0.625rem 0.625rem; }
.dv-image { max-width: 100%; max-height: 100%; object-fit: contain; }
.dv-text { height: 100%; margin: 0; overflow: auto; padding: 1.25rem 1.5rem; white-space: pre-wrap; word-break: break-word; font-family: ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.8rem; line-height: 1.55; color: var(--dv-text); }
.dv-table-wrap { height: 100%; overflow: auto; padding: 0; }
.dv-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.dv-table th, .dv-table td { border-bottom: 1px solid var(--dv-border); padding: 0.45rem 0.75rem; text-align: left; white-space: nowrap; color: var(--dv-text); }
.dv-table thead th { position: sticky; top: 0; z-index: 1; background: var(--dv-surface); font-weight: 700; border-bottom: 2px solid var(--dv-border); }
.dv-table tbody tr:nth-child(even) { background: color-mix(in srgb, var(--dv-surface) 55%, transparent); }
.dv-office-page { width: min(100%, 64rem); margin: 0 auto; padding: 1rem; }
.dv-sheet-tabs { display: flex; gap: 0.25rem; overflow-x: auto; padding: 0.5rem 0.75rem 0; border-bottom: 1px solid var(--dv-border); background: var(--dv-surface); }
.dv-sheet-tab { border: 1px solid var(--dv-border); border-bottom: 0; border-radius: 0.45rem 0.45rem 0 0; background: transparent; color: var(--dv-text-muted); padding: 0.3rem 0.75rem; font: inherit; font-size: 0.72rem; font-weight: 600; cursor: pointer; white-space: nowrap; }
.dv-sheet-tab[data-active="true"] { background: var(--dv-panel); color: var(--dv-text); box-shadow: inset 0 -2px 0 var(--dv-primary); }
.dv-xlsx-table-wrap { height: 100%; overflow: auto; }
.dv-xlsx-table-wrap table { border-collapse: collapse; font-size: 0.78rem; }
.dv-xlsx-table-wrap td, .dv-xlsx-table-wrap th { border: 1px solid var(--dv-border); padding: 0.3rem 0.6rem; white-space: nowrap; color: var(--dv-text); min-width: 3.5rem; }
.dv-xlsx-table-wrap th { background: var(--dv-surface); font-weight: 700; }

/* Docx renderer container: docx-preview renders .docx-wrapper sections */
.dv-docx-scroll { height: 100%; overflow: auto; background: var(--dv-text-muted); }
.dv-docx-scroll .docx-wrapper { background: transparent; padding: 1rem 0; gap: 1rem; }
.dv-docx-scroll .docx-wrapper > section.docx { box-shadow: 0 2px 8px rgb(0 0 0 / 0.18); margin-bottom: 1rem; }

/* Shared states */
.dv-state { display: flex; height: 100%; min-height: 16rem; flex-direction: column; align-items: center; justify-content: center; gap: 0.75rem; padding: 2rem; text-align: center; }
.dv-state-icon { color: var(--dv-text-muted); }
.dv-state-title { font-size: 0.9rem; font-weight: 600; }
.dv-state-message { max-width: 26rem; font-size: 0.8rem; line-height: 1.5; color: var(--dv-text-muted); }
.dv-spinner { width: 1.75rem; height: 1.75rem; border-radius: 999px; border: 3px solid var(--dv-border); border-top-color: var(--dv-primary); animation: dv-spin 0.8s linear infinite; }
@keyframes dv-spin { to { transform: rotate(360deg); } }
.dv-button { display: inline-flex; align-items: center; gap: 0.4rem; border-radius: 0.5rem; background: var(--dv-text); color: var(--dv-background); padding: 0.45rem 0.9rem; font: inherit; font-size: 0.8rem; font-weight: 600; text-decoration: none; cursor: pointer; border: 0; }
.dv-button:hover { opacity: 0.9; }
.dv-empty { display: flex; height: 16rem; align-items: center; justify-content: center; border: 1px dashed var(--dv-border); border-radius: 0.75rem; color: var(--dv-text-muted); font-size: 0.875rem; }
`;
