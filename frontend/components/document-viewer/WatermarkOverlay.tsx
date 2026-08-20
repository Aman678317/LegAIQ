"use client";

interface WatermarkOverlayProps {
  viewerEmail?: string;
  viewerIp?: string;
  timestamp?: string;
  enabled?: boolean;
}

export function WatermarkOverlay({
  viewerEmail = "user@legaiq.in",
  viewerIp = "127.0.0.1",
  timestamp,
  enabled = true,
}: WatermarkOverlayProps) {
  if (!enabled) return null;

  const displayTime = timestamp || new Date().toISOString().replace("T", " ").substring(0, 19) + " UTC";
  const watermarkText = `${viewerEmail} • ${viewerIp} • ${displayTime} • CONFIDENTIAL`;

  return (
    <div className="pointer-events-none absolute inset-0 z-30 overflow-hidden select-none opacity-[0.14]">
      <div className="grid h-full w-full grid-cols-2 gap-24 p-8 -rotate-12 transform scale-110">
        {Array.from({ length: 12 }).map((_, i) => (
          <div key={i} className="flex flex-col items-center justify-center font-mono text-[11px] font-bold tracking-widest text-slate-400">
            <span className="uppercase">LegAIQ Confidential &amp; Privileged</span>
            <span>{watermarkText}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
