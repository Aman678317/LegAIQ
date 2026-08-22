# DocumentViewer

A self-contained React (TypeScript) component for displaying common document
types — PDF, Word, Excel, PowerPoint, text, CSV/TSV, images, and HTML — from
remote URLs, local files, or blob uploads.

- **No CSS framework dependency.** Styling is a single injected, fully scoped
  stylesheet driven by CSS custom properties — drop it into any app.
- **Pluggable renderers.** The bundled defaults cover the common types; pass
  your own per file type and they take precedence.
- **Controlled or uncontrolled.** Show the first document by default, pin an
  initial one, or drive the active document entirely from the parent.
- **Configurable requests.** Inspection (Content-Type/Length probe) and
  document fetches honor custom methods, headers, and a fetch override.

Live playground: `/document-viewer-demo` (theme presets, uploads, remote URLs,
controlled-mode toggle, watermark, and a demo custom markdown renderer).

## Quick start

```tsx
import { DocumentViewer, documentFromFile } from "@/components/document-viewer";

<DocumentViewer
  documents={[
    { id: "contract", uri: "https://cdn.example.com/msa.pdf" },
    { id: "upload", ...documentFromFile(fileInput.files[0]) },
  ]}
  initialActive="contract"       // omit → first document
  theme="dark"                    // light | dark | sepia | ocean
/>
```

### Controlled active document

```tsx
const [activeId, setActiveId] = useState("contract");

<DocumentViewer
  documents={documents}
  active={activeId}                       // parent owns the selection
  onActiveChange={(doc, index) => setActiveId(doc.id ?? doc.uri!)}
/>
```

`initialActive`/`active` accept a document id, uri, fileName, or the document
object itself.

## Default renderers

| Type | Renderer | Notes |
|---|---|---|
| `pdf` | Browser PDF engine (`iframe`) | Works with http(s), blob:, and data: URLs |
| `docx` | [docx-preview](https://www.npmjs.com/package/docx-preview) (lazy-loaded) | Fully client-side — uploads and authenticated files work |
| `xlsx`, `xls` | [SheetJS](https://www.npmjs.com/package/xlsx) (lazy-loaded) | Client-side, with sheet tabs |
| `ppt`, `pptx`, `doc` | Microsoft Office web viewer | Public https URLs only, 10 MB limit; informative fallback otherwise |
| `png/jpg/jpeg/gif/webp/svg/bmp` | `<img>` on a checkerboard | Transparency-friendly |
| `html`, `htm` | Sandboxed iframe | Scripts intentionally disabled |
| `csv`, `tsv` | Parsed table | RFC 4180-style parser: quoted fields, delimiter sniffing, sticky header |
| `txt/md/json/xml/log` | Monospace text | Fetched through the configured request |
| anything else | Fallback card | Download link + pointer to custom renderers |

## Custom renderers

```tsx
import type { DocumentRenderer } from "@/components/document-viewer";

const markdownRenderer: DocumentRenderer = {
  name: "Markdown",
  fileTypes: ["md"],
  Renderer: ({ request }) => { /* your component */ },
};

<DocumentViewer documents={docs} renderers={[markdownRenderer]} />
```

Renderers receive `{ document, source, fileType, request, inspection, theme }`:

- `source` — a URL ready for `src` attributes (the original uri, or an object
  URL created from `document.file`).
- `request()` — a `() => Promise<Response>` that respects `requestOptions`,
  including local `File` documents (wrapped in a `Response`, so text/csv/
  docx/xlsx renderers work for uploads without special-casing).
- `inspection` — `{ contentType, contentLength }` from the inspection probe,
  or `null` when none ran (local files, or inspection not configured).

## Theming

```tsx
<DocumentViewer documents={docs} theme="sepia" />
<DocumentViewer documents={docs} theme={{ preset: "dark", primary: "#f97316" }} />
<DocumentViewer documents={docs} theme={{ primary: "#7c3aed", border: "#ddd" }} />
```

Presets: `light`, `dark`, `sepia`, `ocean`. Any token (`primary`, `background`,
`surface`, `panel`, `text`, `textMuted`, `border`, `hover`) can be overridden
on top of a preset or on the default light base. All styles consume the tokens
through `--dv-*` CSS variables on the viewer root.

## Request customization

Some links only work with certain methods or headers (signed URLs, hosts that
reject `HEAD`, authenticated buckets):

```tsx
<DocumentViewer
  documents={docs}
  requestOptions={{
    inspectMethod: "GET",                          // default HEAD; auto-retries GET on 405/501 when unset
    inspectInit: { headers: { Authorization: "Bearer …" } },
    requestInit: (doc) => ({ headers: { Authorization: tokenFor(doc) } }),
    requestFile: (doc, init) => signedFetch(doc.uri!, init),  // optional full override
  }}
/>
```

Inspection only runs for remote `http(s)` documents and only when
`requestOptions` is provided. Its result powers the header badge (content type)
and the Office viewer's over-10-MB warning.

## Watermark

```tsx
<DocumentViewer documents={docs} watermark />
<DocumentViewer documents={docs} watermark={{ viewerEmail: "me@firm.com", label: "Privileged" }} />
```

Tiles a diagonal confidential watermark over the rendered document
(pointer-events: none — visual only, not a security control).

## Structure

```text
document-viewer/
├── DocumentViewer.tsx    shell: sidebar, header, selection state, inspection
├── types.ts              public types (also re-exported from index.ts)
├── detect.ts             file-kind detection, display names, documentFromFile
├── csv.ts                RFC 4180-style delimited parser
├── theme.ts              presets + scoped stylesheet injection
├── useObjectUrl.ts       object-URL lifecycle hook
├── WatermarkOverlay.tsx  optional watermark overlay
├── renderers/            default renderer set (docx/xlsx lazy-loaded)
└── document-viewer.test.tsx
```

Dependencies: `docx-preview`, `xlsx` (both lazy-loaded on first use),
`lucide-react` for icons. Everything else is React + standard browser APIs.
