"use client";

import { useMemo, useState } from "react";
import type { RendererProps } from "../types";
import { RendererError, RendererLoading, useRendererData } from "./shared";

type XlsxModule = {
  read: (data: ArrayBuffer, opts: { type: "array" }) => {
    SheetNames: string[];
    Sheets: Record<string, unknown>;
  };
  utils: { sheet_to_html: (sheet: unknown) => string };
};

/** Load SheetJS once, on first use, so it stays out of the main bundle. */
let xlsxLib: Promise<XlsxModule> | null = null;
function loadXlsxLib(): Promise<XlsxModule> {
  xlsxLib ??= import("xlsx").then((mod) => mod as unknown as XlsxModule);
  return xlsxLib;
}

type Workbook = { lib: XlsxModule; sheetNames: string[]; sheets: Record<string, unknown> };

/**
 * Excel (.xlsx/.xls): parsed client-side with SheetJS and rendered as tables
 * with sheet tabs. Works for uploads and authenticated fetches alike.
 */
export function XlsxRenderer({ request }: RendererProps) {
  const [activeSheet, setActiveSheet] = useState<string | null>(null);
  const { state, retry } = useRendererData<Workbook>(
    () =>
      loadXlsxLib().then(async (lib) => {
        const buffer = await request().then((res) => res.arrayBuffer());
        const workbook = lib.read(buffer, { type: "array" });
        if (workbook.SheetNames.length === 0) throw new Error("This workbook has no sheets.");
        return { lib, sheetNames: workbook.SheetNames, sheets: workbook.Sheets };
      }),
    "xlsx",
  );

  const sheet = activeSheet && state.data?.sheetNames.includes(activeSheet)
    ? activeSheet
    : state.data?.sheetNames[0] ?? null;

  const tableHtml = useMemo(() => {
    if (state.status !== "ready" || !state.data || !sheet) return "";
    return state.data.lib.utils.sheet_to_html(state.data.sheets[sheet]);
  }, [state, sheet]);

  if (state.status === "loading") return <RendererLoading label="Parsing spreadsheet…" />;
  if (state.status === "error") return <RendererError error={state.error} onRetry={retry} />;

  return (
    <div style={{ display: "flex", height: "100%", flexDirection: "column" }}>
      {state.data && state.data.sheetNames.length > 1 && (
        <div className="dv-sheet-tabs" role="tablist" aria-label="Workbook sheets">
          {state.data.sheetNames.map((name) => (
            <button
              key={name}
              type="button"
              role="tab"
              aria-selected={name === sheet}
              className="dv-sheet-tab"
              data-active={name === sheet}
              onClick={() => setActiveSheet(name)}
            >
              {name}
            </button>
          ))}
        </div>
      )}
      <div className="dv-xlsx-table-wrap" dangerouslySetInnerHTML={{ __html: tableHtml }} />
    </div>
  );
}
