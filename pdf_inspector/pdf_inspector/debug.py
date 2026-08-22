"""Visual debugging — see what the inspector thinks is on the page.

Two complementary renderers:

* :func:`overlay_png` — renders the page to PNG with colored boxes drawn
  around every selected object (words, rects, curves, images, annots, …).
* :func:`ascii_layout` — a terminal-only density map, one letter per object
  kind, useful over SSH or in CI logs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import pymupdf

from .page import KINDS, Page

# Per-kind overlay colors (RGB floats) and ASCII letters.
STYLE: dict[str, tuple[tuple[float, float, float], str]] = {
    "char": ((0.55, 0.55, 0.55), "c"),
    "word": ((0.10, 0.70, 0.25), "w"),
    "textline": ((0.95, 0.55, 0.10), "L"),
    "rect": ((0.15, 0.45, 0.95), "R"),
    "stroke": ((0.60, 0.25, 0.85), "s"),
    "curve": ((0.05, 0.65, 0.65), "k"),
    "image": ((0.90, 0.15, 0.15), "i"),
    "annot": ((0.90, 0.80, 0.10), "A"),
}


def _resolve_kinds(kinds: "str | Iterable[str] | None") -> list[str]:
    if kinds is None:
        return ["word", "textline", "rect", "stroke", "curve", "image", "annot"]
    if isinstance(kinds, str):
        return [k.strip() for k in kinds.split(",") if k.strip()]
    return [k for k in kinds if k]


def overlay_png(
    page: Page,
    out_path: "str | Path",
    kinds: "str | Iterable[str] | None" = None,
    dpi: int = 150,
) -> Path:
    """Render `page` to PNG with colored boxes around each selected object.

    Works on crops too: only the visible area is rendered, and the boxes are
    the exact bboxes the accessors reported — so what you see is what the
    filters matched.
    """
    wanted = _resolve_kinds(kinds)
    invalid = [k for k in wanted if k not in STYLE]
    if invalid:
        raise ValueError(f"no debug style for kinds {invalid}; valid: {', '.join(STYLE)}")

    clip = page.clip if page.clip is not None else page.full_rect

    # Copy just this page into a scratch doc so the original is never touched.
    scratch = pymupdf.open()
    scratch.insert_pdf(page.document._doc, from_page=page.number, to_page=page.number)
    scratch_page = scratch[0]

    shape = scratch_page.new_shape()
    drawn = 0
    for kind in wanted:
        objects = page.objects(kinds={kind}) if kind != "table" else []
        color, _letter = STYLE[kind]
        for obj in objects:
            box = pymupdf.Rect(*obj["bbox"])
            if box.is_empty or box.is_infinite:
                continue
            shape.draw_rect(box)
            shape.finish(color=color, width=max(0.6, 150 / dpi), fill=None)
            drawn += 1
    if page.clip is not None:
        shape.draw_rect(page.clip)
        shape.finish(color=(0, 0, 0), width=1.2, dashes="[3 3] 0")
    shape.commit()

    pixmap = scratch_page.get_pixmap(dpi=dpi, clip=clip)
    pixmap.save(str(out_path))
    scratch.close()
    return Path(out_path)


def ascii_layout(page: Page, width: int = 100) -> str:
    """Terminal map of the page: one character per cell, by dominant kind."""
    if width < 20:
        raise ValueError("ascii_layout width must be at least 20")
    page_w, page_h = page.size
    cell_w = page_w / width
    rows = max(3, round((page_h / cell_w) / 2))  # terminal cells are ~2x tall
    grid = [[" "] * width for _ in range(rows)]

    def mark(bbox: Sequence[float], letter: str) -> None:
        x0 = max(0, int(bbox[0] / page_w * width))
        x1 = min(width - 1, int(bbox[2] / page_w * width))
        y0 = max(0, int(bbox[1] / page_h * rows))
        y1 = min(rows - 1, int(bbox[3] / page_h * rows))
        if x1 < x0:
            x1 = x0
        if y1 < y0:
            y1 = y0
        for row in range(y0, y1 + 1):
            for col in range(x0, x1 + 1):
                grid[row][col] = letter

    # Order matters: fine-grained first, structural kinds overwrite.
    for kind in ("char", "word", "textline", "rect", "stroke", "curve", "image", "annot"):
        letter = STYLE[kind][1]
        for obj in page.objects(kinds={kind}):
            mark(obj["bbox"], letter)

    legend = " | ".join(f"{letter} {kind}" for kind, (_color, letter) in STYLE.items())
    header = f"page {page.number} · {page_w:.0f}x{page_h:.0f}pt · grid {width}x{rows}"
    return header + "\n" + "\n".join("".join(row) for row in grid) + "\nlegend: " + legend


def page_summary(page: Page) -> dict[str, object]:
    """Compact per-page counts — the `pages` CLI command and quick sanity checks."""
    summary: dict[str, object] = {
        "page": page.number,
        "width": page.size[0],
        "height": page.size[1],
        "rotation": page.rotation,
    }
    for kind in KINDS:
        if kind == "table":
            summary["tables"] = len(page.tables())
        else:
            summary[{"char": "chars", "word": "words", "textline": "text_lines", "rect": "rects",
                     "stroke": "line_segments", "curve": "curves", "image": "images", "annot": "annots"}[kind]] = len(page.objects(kinds={kind}))
    return summary
