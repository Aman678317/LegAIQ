"""PDFDocument — open a PDF, iterate pages, close cleanly.

This is the entry point of the Python API::

    from pdf_inspector import PDFDocument

    with PDFDocument.open("report.pdf") as doc:
        for page in doc.pages:
            print(page.number, len(page.chars()), len(page.images()))
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

import pymupdf

from .page import Page  # runtime import is fine: page.py has no runtime import of this module


class PDFDocument:
    """A handle around a PyMuPDF document with a small, inspectable API."""

    def __init__(self, source: "pymupdf.Document | str | Path") -> None:
        self._doc = source if isinstance(source, pymupdf.Document) else pymupdf.open(source)
        self.path = Path(getattr(self._doc, "name", "") or "")
        self._closed = False

    # -- construction ----------------------------------------------------- #

    @classmethod
    def open(cls, path: "str | Path") -> "PDFDocument":
        return cls(path)

    @classmethod
    def from_bytes(cls, data: bytes) -> "PDFDocument":
        return cls(pymupdf.open(stream=data, filetype="pdf"))

    # -- lifecycle -------------------------------------------------------- #

    @property
    def is_closed(self) -> bool:
        return self._closed or self._doc.is_closed

    def close(self) -> None:
        if not self.is_closed:
            self._doc.close()
        self._closed = True

    def __enter__(self) -> "PDFDocument":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # -- structure -------------------------------------------------------- #

    @property
    def page_count(self) -> int:
        return self._doc.page_count

    @property
    def metadata(self) -> dict[str, str]:
        raw = self._doc.metadata or {}
        return {key: str(value) for key, value in raw.items() if value}

    @property
    def pages(self) -> list[Page]:
        return [Page(self, self._doc[i]) for i in range(self.page_count)]

    def page(self, number: int) -> Page:
        """0-based page accessor. Negative numbers count from the end."""
        if self.page_count == 0:
            raise IndexError("The document has no pages")
        return Page(self, self._doc[number])

    def __len__(self) -> int:
        return self.page_count

    def __iter__(self) -> Iterator[Page]:
        return iter(self.pages)

    def __repr__(self) -> str:  # pragma: no cover
        state = "closed" if self.is_closed else f"{self.page_count} pages"
        return f"<PDFDocument {self.path or '(stream)'} — {state}>"


def sniff_pdf(path: "str | Path") -> bool:
    """Cheap check that a file looks like a PDF (name or magic bytes)."""
    path = Path(path)
    if path.suffix and mimetypes.guess_type(path.name)[0] == "application/pdf":
        return True
    try:
        with path.open("rb") as handle:
            return handle.read(5) == b"%PDF-"
    except OSError:
        return False
