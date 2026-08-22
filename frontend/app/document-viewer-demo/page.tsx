"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import {
  DocumentViewer,
  documentFromFile,
  type DocumentRenderer,
  type ThemePreset,
  type ViewerDocument,
} from "@/components/document-viewer";

/* ------------------------------------------------------------------ */
/* Runtime-generated samples: no network needed for the core demo.     */
/* ------------------------------------------------------------------ */

/** Minimal valid one-page PDF with correct xref offsets. */
function makeSamplePdf(lines: string[]): Blob {
  const esc = (s: string) => s.replace(/([()\\])/g, "\\$1");
  const textOps = lines
    .map((line, i) => `BT /F1 ${i === 0 ? 20 : 12} Tf 72 ${740 - i * 26} Td (${esc(line)}) Tj ET`)
    .join("\n");
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    `<< /Length ${textOps.length} >>\nstream\n${textOps}\nendstream`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
  ];
  let pdf = "%PDF-1.4\n";
  const offsets: number[] = [];
  objects.forEach((body, i) => {
    offsets.push(pdf.length);
    pdf += `${i + 1} 0 obj\n${body}\nendobj\n`;
  });
  const xrefStart = pdf.length;
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  offsets.forEach((offset) => {
    pdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
  });
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefStart}\n%%EOF`;
  const bytes = new Uint8Array(pdf.length);
  for (let i = 0; i < pdf.length; i += 1) bytes[i] = pdf.charCodeAt(i) & 0xff;
  return new Blob([bytes], { type: "application/pdf" });
}

function makeSamplePng(label: string): Promise<Blob | null> {
  const canvas = document.createElement("canvas");
  canvas.width = 800;
  canvas.height = 500;
  const ctx = canvas.getContext("2d");
  if (!ctx) return Promise.resolve(null);
  const gradient = ctx.createLinearGradient(0, 0, 800, 500);
  gradient.addColorStop(0, "#1e3a8a");
  gradient.addColorStop(1, "#0e7490");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 800, 500);
  ctx.fillStyle = "#f8fafc";
  ctx.font = "700 44px system-ui, sans-serif";
  ctx.fillText("Deal Structure", 56, 220);
  ctx.font = "22px system-ui, sans-serif";
  ctx.fillText(label, 56, 268);
  ctx.fillStyle = "#fbbf24";
  ctx.fillRect(56, 300, 688, 8);
  return new Promise((resolve) => canvas.toBlob((blob) => resolve(blob), "image/png"));
}

async function makeSampleXlsx(): Promise<Blob | null> {
  try {
    const XLSX = await import("xlsx");
    const capital = XLSX.utils.aoa_to_sheet([
      ["Holder", "Shares", "Class"],
      ["Mara Okafor", "412,500", "Common"],
      ["Harbor Partners GP", "300,000", "Series A"],
      ["Employee pool", "62,500", "Options"],
    ]);
    const debt = XLSX.utils.aoa_to_sheet([
      ["Facility", "Amount (USD)"],
      ["Revolver", 3_600_000],
      ["Finance leases", 900_000],
    ]);
    const book = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(book, capital, "Cap table");
    XLSX.utils.book_append_sheet(book, debt, "Debt schedule");
    const out = XLSX.write(book, { bookType: "xlsx", type: "array" }) as ArrayBuffer;
    return new Blob([out], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  } catch {
    return null;
  }
}

const BASE_SAMPLES: ViewerDocument[] = [
  {
    id: "memo",
    fileName: "closing-memo.txt",
    uri: "data:text/plain,CLOSING%20MEMO%0A%0A1.%20Confirm%20indemnity%20schedule%20matches%20the%20disclosure%20letter.%0A2.%20Wire%20instructions%20verified%20against%20the%20engagement%20letter.%0A3.%20File%20the%20executed%20copies%20in%20the%20deal%20room.",
  },
  {
    id: "tracker",
    fileName: "diligence-tracker.csv",
    uri: "data:text/csv,Item,Owner,Status,Notes%0ABoard%20approval,Legal,Open,Need%20updated%20minutes%0AIP%20assignments,%22HR%2C%20Legal%22,Requested,%22Includes%20the%20%22%22legacy%22%22%20agreements%2C%20tab%204%22%0ARevenue%20schedule,Finance,Complete,%22Per%20Q2%20memo%2C%20see%20also%20sheet%202%22",
  },
  {
    id: "summary",
    fileName: "case-summary.html",
    uri: "data:text/html,%3C!doctype%20html%3E%3Cbody%20style%3D%22font-family%3Asystem-ui%3Bpadding%3A2rem%3Bmax-width%3A40rem%22%3E%3Ch1%3ECase%20summary%3C%2Fh1%3E%3Cp%3ESandboxed%20HTML%20preview%20%E2%80%94%20styles%20render%2C%20scripts%20do%20not%20run.%3C%2Fp%3E%3Cul%3E%3Cli%3EFacts%3C%2Fli%3E%3Cli%3EIssues%3C%2Fli%3E%3Cli%3CHolding%3C%2Fli%3E%3C%2Ful%3E%3C%2Fbody%3E",
  },
  {
    id: "notes",
    fileName: "research-notes.md",
    fileType: "md",
    uri: "data:text/plain,%23%20Research%20notes%0A%0AA%20**custom%20renderer**%20handles%20this%20file%20%E2%80%94%20see%20the%20markdown%20renderer%20below%20the%20viewer.%0A%0A-%20Sidebar%20list%20with%20keyboard%20navigation%0A-%20Inspection%20badge%20in%20the%20header%0A-%20Four%20theme%20presets",
  },
];

/** Demo custom renderer: a ~30-line markdown renderer plugged in via props. */
const MarkdownRenderer: DocumentRenderer = {
  name: "Markdown (demo)",
  fileTypes: ["md"],
  Renderer: ({ request }) => {
    const [html, setHtml] = useState("<p style=\"opacity:.6\">Loading…</p>");
    useEffect(() => {
      let live = true;
      request()
        .then((res) => res.text())
        .then((text) => {
          if (!live) return;
          const escaped = text.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c] ?? c));
          setHtml(
            escaped
              .replace(/^### (.*)$/gm, "<h3>$1</h3>")
              .replace(/^## (.*)$/gm, "<h2>$1</h2>")
              .replace(/^# (.*)$/gm, "<h1>$1</h1>")
              .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
              .replace(/\*(.+?)\*/g, "<em>$1</em>")
              .replace(/`(.+?)`/g, "<code>$1</code>")
              .replace(/^- (.*)$/gm, "<li>$1</li>")
              .replace(/\n{2,}/g, "</p><p>"),
          );
        })
        .catch(() => live && setHtml("<p>Failed to load markdown.</p>"));
      return () => {
        live = false;
      };
    }, [request]);
    return (
      <div
        style={{ padding: "1.5rem 2rem", overflow: "auto", height: "100%", lineHeight: 1.65 }}
        dangerouslySetInnerHTML={{ __html: `<p>${html}</p>` }}
      />
    );
  },
};

const THEMES: ThemePreset[] = ["light", "dark", "sepia", "ocean"];

export default function DocumentViewerDemo() {
  const [documents, setDocuments] = useState<ViewerDocument[]>(BASE_SAMPLES);
  const [activeId, setActiveId] = useState("memo");
  const [controlled, setControlled] = useState(true);
  const [theme, setTheme] = useState<ThemePreset>("light");
  const [showSidebar, setShowSidebar] = useState(true);
  const [watermark, setWatermark] = useState(false);
  const [remoteUrl, setRemoteUrl] = useState("");

  // Generate the binary samples (PDF/PNG/XLSX) once, in the browser.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const png = await makeSamplePng("Exhibit C — org chart placeholder");
      const xlsx = await makeSampleXlsx();
      if (cancelled) return;
      const additions: ViewerDocument[] = [
        documentFromFile(
          makeSamplePdf([
            "Sample Engagement Letter",
            "This PDF was generated in the browser at demo load time.",
            "The viewer renders it through the browser's native PDF engine.",
            "Try the theme presets, uploads, and the request options.",
          ]),
          "sample-pdf",
        ),
        ...(png ? [documentFromFile(png, "sample-png")] : []),
        ...(xlsx ? [documentFromFile(xlsx, "sample-xlsx")] : []),
      ];
      setDocuments((current) => [...current, ...additions]);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const addFiles = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (files.length === 0) return;
    const added = files.map((file) => documentFromFile(file));
    setDocuments((current) => [...current, ...added]);
    setActiveId(added[0].id!);
    event.target.value = "";
  };

  const addRemote = () => {
    const url = remoteUrl.trim();
    if (!/^https?:\/\//i.test(url)) return;
    const name = decodeURIComponent(url.split(/[?#]/)[0].split("/").pop() || "remote-file");
    setDocuments((current) => [...current, { id: `remote:${url}`, uri: url, fileName: name }]);
    setActiveId(`remote:${url}`);
    setRemoteUrl("");
  };

  const viewerProps = useMemo(
    () => ({
      documents,
      theme,
      showSidebar,
      watermark: watermark ? { viewerEmail: "associate@legaiq.in", label: "Privileged & Confidential" } : false,
      renderers: [MarkdownRenderer],
      requestOptions: { inspectMethod: "GET" as const },
    }),
    [documents, theme, showSidebar, watermark],
  );

  return (
    <main style={{ minHeight: "100vh", background: "#f1f5f9", padding: "3rem 1.25rem", color: "#0f172a", fontFamily: "ui-sans-serif, system-ui, sans-serif" }}>
      <div style={{ maxWidth: "72rem", margin: "0 auto" }}>
        <p style={{ fontSize: ".78rem", fontWeight: 700, letterSpacing: ".16em", textTransform: "uppercase", color: "#1d4ed8" }}>Reusable component demo</p>
        <h1 style={{ marginTop: ".5rem", fontSize: "2.4rem", fontWeight: 650, letterSpacing: "-.02em" }}>Document Viewer</h1>
        <p style={{ marginTop: ".75rem", maxWidth: "44rem", color: "#475569", lineHeight: 1.6 }}>
          PDFs, Word, Excel, PowerPoint, text, CSV, images, and HTML — from URLs or local files.
          Everything below runs on runtime-generated samples, so it works offline; upload your own
          files or paste a remote URL to go further.
        </p>

        <div style={{ marginTop: "1.75rem", display: "flex", flexWrap: "wrap", gap: "1.25rem", alignItems: "center" }}>
          <label style={{ display: "flex", gap: ".4rem", alignItems: "center", fontSize: ".85rem" }}>
            Theme
            <select value={theme} onChange={(e) => setTheme(e.target.value as ThemePreset)} style={{ padding: ".35rem .5rem", borderRadius: ".5rem", border: "1px solid #cbd5e1" }}>
              {THEMES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          <label style={{ display: "flex", gap: ".45rem", alignItems: "center", fontSize: ".85rem" }}>
            <input type="checkbox" checked={controlled} onChange={(e) => setControlled(e.target.checked)} />
            Controlled active file
          </label>
          <label style={{ display: "flex", gap: ".45rem", alignItems: "center", fontSize: ".85rem" }}>
            <input type="checkbox" checked={showSidebar} onChange={(e) => setShowSidebar(e.target.checked)} />
            Sidebar
          </label>
          <label style={{ display: "flex", gap: ".45rem", alignItems: "center", fontSize: ".85rem" }}>
            <input type="checkbox" checked={watermark} onChange={(e) => setWatermark(e.target.checked)} />
            Watermark
          </label>
          <label style={{ cursor: "pointer", background: "#0f172a", color: "#fff", padding: ".5rem .9rem", borderRadius: ".55rem", fontSize: ".85rem", fontWeight: 600 }}>
            Upload files
            <input type="file" multiple className="sr-only" onChange={addFiles} />
          </label>
          <span style={{ fontSize: ".75rem", color: "#64748b" }}>Tip: upload a .docx or .pptx — Word renders locally, PowerPoint uses the Office web viewer (public URLs only).</span>
        </div>

        <div style={{ marginTop: ".75rem", display: "flex", gap: ".5rem" }}>
          <input
            value={remoteUrl}
            onChange={(e) => setRemoteUrl(e.target.value)}
            placeholder="https://example.com/report.xlsx"
            style={{ flex: 1, padding: ".5rem .75rem", borderRadius: ".55rem", border: "1px solid #cbd5e1", fontSize: ".85rem" }}
          />
          <button type="button" onClick={addRemote} style={{ padding: ".5rem 1rem", borderRadius: ".55rem", border: 0, background: "#1d4ed8", color: "#fff", fontWeight: 600, fontSize: ".85rem", cursor: "pointer" }}>
            Add URL
          </button>
        </div>

        <div style={{ marginTop: "1.5rem", height: "42rem" }}>
          {controlled ? (
            <DocumentViewer
              {...viewerProps}
              active={activeId}
              onActiveChange={(doc) => setActiveId((doc.id ?? doc.uri)!)}
            />
          ) : (
            <DocumentViewer {...viewerProps} initialActive={activeId} onActiveChange={(doc) => setActiveId((doc.id ?? doc.uri)!)} />
          )}
        </div>

        <pre style={{ marginTop: "1.75rem", overflow: "auto", background: "#0f172a", color: "#e2e8f0", padding: "1.25rem", borderRadius: ".8rem", fontSize: ".75rem", lineHeight: 1.7 }}>
{`import { DocumentViewer, documentFromFile, type DocumentRenderer } from "@/components/document-viewer";

const mdRenderer: DocumentRenderer = { name: "Markdown", fileTypes: ["md"], Renderer: MyMdComponent };

<DocumentViewer
  documents={documents}                 // first file shows by default
  initialActive="closing-memo.txt"      // or: active={activeId} to control it
  onActiveChange={(doc, index) => ...}
  renderers={[mdRenderer]}              // custom renderers win over defaults
  theme="dark" | "sepia" | tokens       // 4 presets or token overrides
  watermark={{ viewerEmail: "me@firm.com" }}
  requestOptions={{
    inspectMethod: "GET",               // for hosts that reject HEAD
    requestInit: { headers: { Authorization: "Bearer …" } },
    requestFile: (doc, init) => …       // or take over fetching entirely
  }}
/>`}
        </pre>
      </div>
    </main>
  );
}
