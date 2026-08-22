"use client";

import type { WatermarkConfig } from "./types";

/**
 * Confidential-style watermark tiled over the rendered document. Purely
 * visual (pointer-events: none); it is not a security control. Colors follow
 * the viewer theme via CSS custom properties.
 */
export function WatermarkOverlay({ config }: { config?: boolean | WatermarkConfig }) {
  if (!config) return null;
  const settings = config === true ? {} : config;
  const time = new Date().toISOString().replace("T", " ").substring(0, 19) + " UTC";
  const identity = [settings.viewerEmail ?? "confidential", settings.viewerIp, time]
    .filter(Boolean)
    .join(" • ");

  return (
    <div
      aria-hidden="true"
      style={{
        position: "absolute",
        inset: 0,
        zIndex: 5,
        overflow: "hidden",
        pointerEvents: "none",
        userSelect: "none",
        display: "flex",
        flexWrap: "wrap",
        alignContent: "center",
        justifyContent: "center",
        gap: "7rem 5rem",
        transform: "rotate(-14deg) scale(1.15)",
        opacity: 0.13,
        color: "var(--dv-text)",
      }}
    >
      {Array.from({ length: 9 }).map((_, i) => (
        <div key={i} style={{ textAlign: "center", font: "700 0.65rem/1.5 ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", whiteSpace: "nowrap" }}>
          <div>{settings.label ?? "Confidential"}</div>
          <div>{identity}</div>
        </div>
      ))}
    </div>
  );
}
