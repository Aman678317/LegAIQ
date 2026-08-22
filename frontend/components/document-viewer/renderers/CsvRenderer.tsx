"use client";

import { parseDelimited } from "../csv";
import type { RendererProps } from "../types";
import { RendererError, RendererLoading, useRendererData } from "./shared";

/** CSV/TSV: parsed with a proper quoted-field parser, rendered as a sticky-header table. */
export function CsvRenderer({ request }: RendererProps) {
  const { state, retry } = useRendererData(
    () => request().then((res) => res.text()).then((text) => parseDelimited(text)),
    "csv",
  );

  if (state.status === "loading") return <RendererLoading label="Parsing table…" />;
  if (state.status === "error") return <RendererError error={state.error} onRetry={retry} />;

  const rows = state.data?.rows ?? [];
  if (rows.length === 0) return <RendererError error="The file appears to be empty." />;

  const [header, ...body] = rows;
  return (
    <div className="dv-table-wrap">
      <table className="dv-table">
        <thead>
          <tr>
            {header.map((cell, i) => (
              <th key={i} scope="col">
                {cell}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, r) => (
            <tr key={r}>
              {row.map((cell, c) => (
                <td key={c}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
