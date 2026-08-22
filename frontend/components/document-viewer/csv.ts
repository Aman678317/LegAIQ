/**
 * Small RFC 4180-style delimited-text parser: quoted fields, escaped quotes,
 * delimiters and newlines inside quotes, and \r\n line endings.
 */

export type DelimitedTable = {
  rows: string[][];
  delimiter: string;
};

export function parseDelimited(text: string, delimiter?: string): DelimitedTable {
  const delim = delimiter ?? sniffDelimiter(text);
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;
  let started = false; // current row has visible content (avoids trailing empty row)

  const pushField = () => {
    row.push(field);
    field = "";
    started = true;
  };
  const pushRow = () => {
    if (started || row.length > 0) {
      pushField();
      rows.push(row);
      row = [];
      started = false;
    }
  };

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (inQuotes) {
      if (char === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i += 1;
        } else {
          inQuotes = false;
        }
      } else {
        field += char;
      }
      continue;
    }
    if (char === '"' && field === "") {
      inQuotes = true;
      started = true;
      continue;
    }
    if (char === delim) {
      pushField();
      continue;
    }
    if (char === "\n") {
      pushRow();
      continue;
    }
    if (char === "\r") {
      if (text[i + 1] === "\n") i += 1;
      pushRow();
      continue;
    }
    field += char;
    started = true;
  }
  if (field !== "" || row.length > 0) pushRow();
  return { rows, delimiter: delim };
}

function sniffDelimiter(text: string): string {
  const sample = text.slice(0, 4000);
  const count = (needle: string) => sample.split(needle).length - 1;
  const tabs = count("\t");
  const commas = count(",");
  const semis = count(";");
  const pipes = count("|");
  const best = Math.max(tabs, commas, semis, pipes);
  if (best === 0) return ",";
  if (best === tabs) return "\t";
  if (best === semis) return ";";
  if (best === pipes) return "|";
  return ",";
}
