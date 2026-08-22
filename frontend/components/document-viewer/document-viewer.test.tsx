import { useState } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import {
  DocumentViewer,
  detectKind,
  documentFromFile,
  parseDelimited,
  resolveTheme,
  THEME_PRESETS,
  type DocumentRenderer,
  type ViewerDocument,
} from "./";

/* ------------------------------- csv.ts ------------------------------- */

describe("parseDelimited", () => {
  it("parses simple rows", () => {
    const { rows } = parseDelimited("a,b\nc,d");
    expect(rows).toEqual([
      ["a", "b"],
      ["c", "d"],
    ]);
  });

  it("handles quoted fields with commas, escaped quotes, and embedded newlines", () => {
    const csv = 'name,note\n"Smith, John","said ""hi""\nsecond line"\nlast,plain';
    const { rows } = parseDelimited(csv);
    expect(rows).toEqual([
      ["name", "note"],
      ["Smith, John", 'said "hi"\nsecond line'],
      ["last", "plain"],
    ]);
  });

  it("handles CRLF line endings without ghost rows", () => {
    const { rows } = parseDelimited("a,b\r\nc,d\r\n");
    expect(rows).toEqual([
      ["a", "b"],
      ["c", "d"],
    ]);
  });

  it("sniffs tab and semicolon delimiters", () => {
    expect(parseDelimited("a\tb\nc\td").delimiter).toBe("\t");
    expect(parseDelimited("a;b\nc;d").delimiter).toBe(";");
  });
});

/* ------------------------------ detect.ts ------------------------------ */

describe("detectKind", () => {
  it("explicit fileType wins", () => {
    expect(detectKind({ uri: "x.bin", fileType: "pdf" })).toBe("pdf");
  });

  it("falls back to MIME then extension", () => {
    expect(detectKind({ mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" })).toBe("xlsx");
    expect(detectKind({ uri: "https://example.com/docs/report.DOCX?x=1" })).toBe("docx");
    expect(detectKind({ fileName: "photo.jpeg" })).toBe("jpeg");
  });

  it("reads the name from a File object", () => {
    const file = new File(["x"], "brief.docx", { type: "" });
    expect(detectKind({ file })).toBe("docx");
  });

  it("unknown when nothing signals a type", () => {
    expect(detectKind({ uri: "https://example.com/noext" })).toBe("unknown");
  });
});

describe("documentFromFile", () => {
  it("wraps a File with name and mime", () => {
    const file = new File(["hello"], "notes.txt", { type: "text/plain" });
    const doc = documentFromFile(file, "custom-id");
    expect(doc.id).toBe("custom-id");
    expect(doc.fileName).toBe("notes.txt");
    expect(doc.mimeType).toBe("text/plain");
  });
});

/* ------------------------------- theme.ts ------------------------------ */

describe("resolveTheme", () => {
  it("returns presets by name and defaults to light", () => {
    expect(resolveTheme("dark")).toEqual(THEME_PRESETS.dark);
    expect(resolveTheme()).toEqual(THEME_PRESETS.light);
    expect(resolveTheme("nonsense" as never)).toEqual(THEME_PRESETS.light);
  });

  it("merges token overrides onto the light base", () => {
    const theme = resolveTheme({ primary: "#ff0000" });
    expect(theme.primary).toBe("#ff0000");
    expect(theme.background).toBe(THEME_PRESETS.light.background);
  });
});

/* ---------------------------- DocumentViewer --------------------------- */

const stubRenderer = (label: string, types: string[]): DocumentRenderer => ({
  name: label,
  fileTypes: types,
  Renderer: () => <div data-testid={`renderer-${label}`}>{label}</div>,
});

const docs: ViewerDocument[] = [
  { id: "one", uri: "https://example.com/a.pdf", fileName: "contract.pdf" },
  { id: "two", uri: "https://example.com/b.txt", fileName: "notes.txt" },
  { id: "three", uri: "https://example.com/c.zzz", fileName: "blob.zzz" },
];

it("shows the first document by default and lists all documents", () => {
  render(<DocumentViewer documents={docs} renderers={[stubRenderer("pdf", ["pdf"]), stubRenderer("txt", ["txt"]), stubRenderer("unknown", ["unknown"])]} />);
  expect(screen.getByTestId("renderer-pdf")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /contract\.pdf/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /notes\.txt/ })).toBeInTheDocument();
});

it("switches documents from the sidebar and reports onActiveChange", async () => {
  const user = userEvent.setup();
  const onChange = vi.fn();
  render(
    <DocumentViewer
      documents={docs}
      onActiveChange={onChange}
      renderers={[stubRenderer("pdf", ["pdf"]), stubRenderer("txt", ["txt"]), stubRenderer("unknown", ["unknown"])]}
    />,
  );
  await user.click(screen.getByRole("button", { name: /notes\.txt/ }));
  expect(screen.getByTestId("renderer-txt")).toBeInTheDocument();
  expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ id: "two" }), 1);
});

it("honors initialActive", () => {
  render(
    <DocumentViewer
      documents={docs}
      initialActive="two"
      renderers={[stubRenderer("pdf", ["pdf"]), stubRenderer("txt", ["txt"]), stubRenderer("unknown", ["unknown"])]}
    />,
  );
  expect(screen.getByTestId("renderer-txt")).toBeInTheDocument();
});

it("follows the controlled active prop and ignores internal clicks", async () => {
  const user = userEvent.setup();
  const onChange = vi.fn();
  function Controlled() {
    const [active, setActive] = useState("one");
    return (
      <div>
        <button onClick={() => setActive("two")}>parent: select notes</button>
        <DocumentViewer
          documents={docs}
          active={active}
          onActiveChange={onChange}
          renderers={[stubRenderer("pdf", ["pdf"]), stubRenderer("txt", ["txt"]), stubRenderer("unknown", ["unknown"])]}
        />
      </div>
    );
  }
  render(<Controlled />);
  await user.click(screen.getByText("parent: select notes"));
  expect(screen.getByTestId("renderer-txt")).toBeInTheDocument();

  // Clicking a sidebar doc fires onActiveChange, but with a controlled `active`
  // prop the viewer only changes when the parent changes its state.
  await user.click(screen.getByRole("button", { name: /contract\.pdf/ }));
  expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ id: "one" }), 0);
  expect(screen.getByTestId("renderer-txt")).toBeInTheDocument(); // parent state still "two"
});

it("uses the built-in fallback renderer for unknown types", () => {
  render(<DocumentViewer documents={[docs[2]]} />);
  expect(screen.getByText(/no built-in preview for zzz/i)).toBeInTheDocument();
});

it("renders an empty state without documents", () => {
  render(<DocumentViewer documents={[]} />);
  expect(screen.getByText(/no documents to display/i)).toBeInTheDocument();
});

it("applies theme tokens as CSS variables on the root", () => {
  render(<DocumentViewer documents={[docs[0]]} theme="dark" renderers={[stubRenderer("pdf", ["pdf"])]} />);
  const root = document.querySelector("[data-document-viewer]") as HTMLElement;
  expect(root).not.toBeNull();
  expect(root.style.getPropertyValue("--dv-primary")).toBe(THEME_PRESETS.dark.primary);
  expect(root.style.getPropertyValue("--dv-text")).toBe(THEME_PRESETS.dark.text);
});

it("renders local File documents through an object URL", async () => {
  const file = new File(["%PDF-1.4 sample"], "local.pdf", { type: "application/pdf" });
  render(<DocumentViewer documents={[{ file, fileName: "local.pdf" }]} />);
  await waitFor(() => {
    expect(screen.getByTitle("PDF preview")).toHaveAttribute("src", expect.stringMatching(/^blob:/));
  });
});
