"""Page — detailed, normalized access to everything on one PDF page.

Every accessor returns plain JSON-able dicts with a uniform shape::

    {"kind": "char|word|textline|rect|stroke|curve|image|annot|table",
     "page": 0, "bbox": [x0, y0, x1, y1], ...kind-specific fields}

A *crop* is another Page scoped to a rectangle: the same accessors return only
objects that intersect the crop, and text/table extraction uses the clip.

Works best on generated (vector) PDFs: text runs, drawn shapes, embedded
images, and standard annotations all come from the page content streams.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Sequence

import pymupdf

# find_tables() otherwise prints a one-time pymupdf_layout recommendation to
# stdout, which corrupts machine-readable CLI output. Official opt-out.
if hasattr(pymupdf, "no_recommend_layout"):
    pymupdf.no_recommend_layout()

if TYPE_CHECKING:  # pragma: no cover — avoids a circular runtime import
    from .document import PDFDocument

KINDS = ("char", "word", "textline", "rect", "stroke", "curve", "image", "annot", "table")

Color = "int | None"


def color_hex(value: "int | float | tuple | list | None") -> "str | None":
    """Render PyMuPDF colors as #rrggbb.

    Text span colors are ints; drawing colors are float (r, g, b) tuples.
    """
    if value is None:
        return None
    if isinstance(value, int):
        return f"#{value:06x}"
    if isinstance(value, (tuple, list)) and len(value) == 3:
        try:
            return "#" + "".join(f"{round(float(part) * 255):02x}" for part in value)
        except (TypeError, ValueError):
            pass
    return str(value)


def bbox_list(rect: Sequence[float]) -> list[float]:
    return [round(float(rect[0]), 2), round(float(rect[1]), 2), round(float(rect[2]), 2), round(float(rect[3]), 2)]


def _shape_coords(value: Any) -> "list[float] | None":
    """Normalize one drawing-item argument (Point, Rect, or scalar to skip).

    Current PyMuPDF appends sequence integers to some items (e.g. ``("re",
    rect, 1)``); anything without geometry is dropped.
    """
    if hasattr(value, "width"):  # Rect-like
        return bbox_list((value.x0, value.y0, value.x1, value.y1))
    if hasattr(value, "x") and hasattr(value, "y"):  # Point-like
        return [round(float(value.x), 2), round(float(value.y), 2)]
    return None


def _intersects(a: Sequence[float], b: Sequence[float]) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def _contained(inner: Sequence[float], outer: Sequence[float]) -> bool:
    return (inner[0] >= outer[0] and inner[1] >= outer[1] and inner[2] <= outer[2] and inner[3] <= outer[3])


class Page:
    """One page — or a cropped view of one (see :meth:`crop`)."""

    def __init__(self, document: PDFDocument, page: "pymupdf.Page", clip: "pymupdf.Rect | None" = None) -> None:
        self.document = document
        self._page = page
        self.clip = clip

    # -- identity --------------------------------------------------------- #

    @property
    def number(self) -> int:
        """0-based page number in the document."""
        return self._page.number

    @property
    def size(self) -> tuple[float, float]:
        """(width, height) of the visible area — the crop if this is a view."""
        rect = self.clip if self.clip is not None else self._page.rect
        return (round(rect.width, 2), round(rect.height, 2))

    @property
    def rotation(self) -> int:
        return self._page.rotation

    @property
    def is_crop(self) -> bool:
        return self.clip is not None

    @property
    def full_rect(self) -> "pymupdf.Rect":
        return self._page.rect

    def __repr__(self) -> str:  # pragma: no cover
        crop = f" crop={tuple(round(v, 1) for v in self.clip)}" if self.clip else ""
        return f"<Page {self.number} {self.size[0]:.0f}x{self.size[1]:.0f}{crop}>"

    # -- cropping & filtering --------------------------------------------- #

    def crop(self, rect: "Sequence[float] | pymupdf.Rect | str") -> "Page":
        """Return a Page view limited to `rect` (x0, y0, x1, y1).

        The rect is clamped to the page; crops of crops intersect.
        """
        if isinstance(rect, pymupdf.Rect):
            wanted = pymupdf.Rect(rect)
        elif isinstance(rect, str):
            parts = [float(v) for v in rect.split(",")]
            if len(parts) != 4:
                raise ValueError("crop rect string must be 'x0,y0,x1,y1'")
            wanted = pymupdf.Rect(parts)
        else:
            wanted = pymupdf.Rect(float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3]))
        base = self.clip if self.clip is not None else self._page.rect
        wanted = wanted & base
        if wanted.is_empty:
            raise ValueError(f"crop rect {tuple(wanted)} is empty or outside the page")
        return Page(self.document, self._page, clip=wanted)

    def _keep(self, bbox: Sequence[float], mode: str, bbox_filter: "pymupdf.Rect | None") -> bool:
        if bbox_filter is None:
            return True
        target = [bbox_filter.x0, bbox_filter.y0, bbox_filter.x1, bbox_filter.y1]
        return _contained(bbox, target) if mode == "contains" else _intersects(bbox, target)

    # -- text -------------------------------------------------------------- #

    def chars(self, bbox: "Sequence[float] | None" = None, mode: str = "intersects") -> list[dict[str, Any]]:
        """Every character with its box, font, size, and color."""
        clip = self.clip if self.clip is not None else None
        raw = self._page.get_text("rawdict", clip=clip)
        out: list[dict[str, Any]] = []
        for block in raw.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    for char in span.get("chars", []):
                        entry = {
                            "kind": "char",
                            "page": self.number,
                            "char": char["c"],
                            "bbox": bbox_list(char["bbox"]),
                            "origin": [round(float(v), 2) for v in char["origin"]],
                            "font": span.get("font"),
                            "size": round(float(span.get("size", 0)), 2),
                            "color": color_hex(span.get("color")),
                            "ascender": round(float(span.get("ascender", 0)), 3),
                            "descender": round(float(span.get("descender", 0)), 3),
                        }
                        if self._keep(entry["bbox"], mode, self._filter_rect(bbox)):
                            out.append(entry)
        return out

    def words(self, bbox: "Sequence[float] | None" = None, mode: str = "intersects") -> list[dict[str, Any]]:
        """Words with boxes (from the 'words' extractor — reliable reading pieces)."""
        clip = self.clip if self.clip is not None else None
        out: list[dict[str, Any]] = []
        for x0, y0, x1, y1, word, *_meta in self._page.get_text("words", clip=clip):
            entry = {"kind": "word", "page": self.number, "text": word, "bbox": bbox_list((x0, y0, x1, y1))}
            if self._keep(entry["bbox"], mode, self._filter_rect(bbox)):
                out.append(entry)
        return out

    def text_lines(self, bbox: "Sequence[float] | None" = None, mode: str = "intersects") -> list[dict[str, Any]]:
        """Text lines with their spans (font/size/color per span)."""
        clip = self.clip if self.clip is not None else None
        raw = self._page.get_text("dict", clip=clip)
        out: list[dict[str, Any]] = []
        for block in raw.get("blocks", []):
            for line in block.get("lines", []):
                spans = [
                    {
                        "text": span.get("text", ""),
                        "font": span.get("font"),
                        "size": round(float(span.get("size", 0)), 2),
                        "color": color_hex(span.get("color")),
                    }
                    for span in line.get("spans", [])
                ]
                entry = {
                    "kind": "textline",
                    "page": self.number,
                    "text": "".join(span["text"] for span in spans),
                    "bbox": bbox_list(line["bbox"]),
                    "spans": spans,
                    "writing_mode": line.get("wmode", 0) or 0,
                }
                if self._keep(entry["bbox"], mode, self._filter_rect(bbox)):
                    out.append(entry)
        return out

    def text(self) -> str:
        """Plain text of the page (respecting any crop)."""
        return self._page.get_text("text", clip=self.clip)

    # -- vector graphics --------------------------------------------------- #

    def _drawings(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for path in self._page.get_drawings():
            items = path.get("items", [])
            kinds = {item[0] for item in items}
            if not items:
                continue
            if "c" in kinds or "qu" in kinds:
                kind = "curve"
            elif kinds == {"re"}:
                kind = "rect"
            else:
                kind = "stroke"
            out.append({
                "kind": kind,
                "page": self.number,
                "bbox": bbox_list(path["rect"]),
                "stroke": color_hex(path.get("color")),
                "fill": color_hex(path.get("fill")),
                "width": round(float(path.get("width") or 0), 2),
                "opacity": path.get("fill_opacity") if path.get("fill_opacity") is not None else path.get("stroke_opacity"),
                "segments": [
                    {"op": item[0], "coords": [c for c in (_shape_coords(v) for v in item[1:]) if c is not None]}
                    for item in items[:50]
                ],
            })
        return out

    def rectangles(self, bbox: "Sequence[float] | None" = None, mode: str = "intersects") -> list[dict[str, Any]]:
        return self._filtered_drawings("rect", bbox, mode)

    def lines(self, bbox: "Sequence[float] | None" = None, mode: str = "intersects") -> list[dict[str, Any]]:
        return self._filtered_drawings("stroke", bbox, mode)

    def curves(self, bbox: "Sequence[float] | None" = None, mode: str = "intersects") -> list[dict[str, Any]]:
        return self._filtered_drawings("curve", bbox, mode)

    def _filtered_drawings(self, kind: str, bbox: "Sequence[float] | None", mode: str) -> list[dict[str, Any]]:
        clip = self._filter_rect(bbox)
        base = self.clip
        out = []
        for entry in self._drawings():
            if entry["kind"] != kind:
                continue
            if base is not None and not self._keep(entry["bbox"], "intersects", base):
                continue
            if clip is not None and not self._keep(entry["bbox"], mode, clip):
                continue
            out.append(entry)
        return out

    # -- images ------------------------------------------------------------ #

    def images(self, bbox: "Sequence[float] | None" = None, mode: str = "intersects") -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for info in self._page.get_image_info(xrefs=True):
            box = info.get("bbox")
            if not box:
                continue
            entry = {
                "kind": "image",
                "page": self.number,
                "bbox": bbox_list(box),
                "pixel_width": info.get("width"),
                "pixel_height": info.get("height"),
                "xref": info.get("xref"),
                "colorspace": info.get("colorspace"),
                "has_alpha": bool(info.get("has-alpha", info.get("has_alpha", False))),
                "transform": [round(float(v), 2) for v in info.get("transform", [])],
            }
            if self.clip is not None and not self._keep(entry["bbox"], "intersects", self.clip):
                continue
            if not self._keep(entry["bbox"], mode, self._filter_rect(bbox)):
                continue
            out.append(entry)
        return out

    # -- annotations ------------------------------------------------------- #

    def annotations(self, bbox: "Sequence[float] | None" = None, mode: str = "intersects") -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for annot in self._page.annots() or []:
            rect = annot.rect
            entry = {
                "kind": "annot",
                "page": self.number,
                "annot_type": annot.type[1],
                "bbox": bbox_list((rect.x0, rect.y0, rect.x1, rect.y1)),
                "contents": annot.info.get("content", "") or "",
                "title": annot.info.get("title", "") or "",
                "subject": annot.info.get("subject", "") or "",
            }
            if self.clip is not None and not self._keep(entry["bbox"], "intersects", self.clip):
                continue
            if not self._keep(entry["bbox"], mode, self._filter_rect(bbox)):
                continue
            out.append(entry)
        return out

    # -- tables ------------------------------------------------------------ #

    def tables(self) -> list[dict[str, Any]]:
        """Tables detected on the page (or within the crop), with cell contents."""
        finder = self._page.find_tables(clip=self.clip)
        out: list[dict[str, Any]] = []
        for table in finder.tables:
            out.append({
                "kind": "table",
                "page": self.number,
                "bbox": bbox_list(table.bbox),
                "rows": table.row_count,
                "cols": table.col_count,
                "cells": table.extract(),
                "header": list(getattr(table.header, "names", None) or []),
            })
        return out

    # -- everything, filtered ---------------------------------------------- #

    def objects(
        self,
        kinds: "str | Iterable[str] | None" = None,
        bbox: "Sequence[float] | None" = None,
        mode: str = "intersects",
    ) -> list[dict[str, Any]]:
        """Unified, filtered, position-sorted object list across all kinds."""
        wanted = set(KINDS) if kinds is None else {k.strip() for k in str(kinds).split(",")} if isinstance(kinds, str) else set(kinds)
        unknown = wanted - set(KINDS)
        if unknown:
            raise ValueError(f"unknown kinds {sorted(unknown)}; valid: {', '.join(KINDS)}")

        gathered: list[dict[str, Any]] = []
        getters = {
            "char": self.chars, "word": self.words, "textline": self.text_lines,
            "rect": self.rectangles, "stroke": self.lines, "curve": self.curves,
            "image": self.images, "annot": self.annotations,
        }
        for kind in wanted:
            if kind == "table":
                continue  # tables are structural, not positional; use tables()
            gathered.extend(getters[kind](bbox=bbox, mode=mode))
        gathered.sort(key=lambda obj: (round(obj["bbox"][1], 1), round(obj["bbox"][0], 1), obj["kind"]))
        return gathered

    # -- helpers ------------------------------------------------------------ #

    def _filter_rect(self, bbox: "Sequence[float] | None") -> "pymupdf.Rect | None":
        if bbox is None:
            return None
        return pymupdf.Rect(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))


# Readable alias: crops return this same class, but the name documents intent.
Region = Page
