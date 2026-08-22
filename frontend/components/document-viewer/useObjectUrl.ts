"use client";

import { useEffect, useState } from "react";

/**
 * Manage an object URL for the lifetime of a File/Blob, revoking it on change
 * and unmount. Returns the given uri unchanged when there is no file.
 *
 * The setState here acquires an external resource (an object URL) inside an
 * effect — the canonical pattern for synchronizing with platform APIs — so the
 * React-Compiler lint rule is disabled for this line.
 */
export function useDocumentSource(uri?: string, file?: File | Blob): string {
  const [entry, setEntry] = useState<{ file: File | Blob; url: string } | null>(null);

  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- external resource acquisition
    setEntry({ file, url });
    return () => URL.revokeObjectURL(url);
  }, [file]);

  return file && entry?.file === file ? entry.url : uri || "";
}
