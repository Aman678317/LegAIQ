"""Command line interface.

    pdfinspect info FILE
    pdfinspect pages FILE
    pdfinspect objects FILE [--page N] [--kinds word,rect,...] [--bbox x0,y0,x1,y1]
                            [--crop x0,y0,x1,y1] [--mode intersects|contains]
                            [--format table|json|csv] [--out FILE] [--limit N]
    pdfinspect text FILE [--page N] [--crop x0,y0,x1,y1] [--out FILE]
    pdfinspect tables FILE [--page N] [--format json|csv] [--out FILE]
    pdfinspect debug FILE --page N [--out FILE.png] [--kinds ...] [--dpi 150]
                          [--ascii] [--width 100] [--crop ...]
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import pymupdf

from .debug import ascii_layout, overlay_png, page_summary
from .document import PDFDocument
from .page import KINDS, Page

# Scalar fields promoted to CSV columns / table output, per kind.
SALIENT: dict[str, tuple[str, ...]] = {
    "char": ("char", "font", "size", "color"),
    "word": ("text",),
    "textline": ("text",),
    "rect": ("stroke", "fill", "width"),
    "stroke": ("stroke", "fill", "width"),
    "curve": ("stroke", "fill", "width"),
    "image": ("pixel_width", "pixel_height", "xref"),
    "annot": ("annot_type", "contents", "title"),
    "table": ("rows", "cols"),
}

COMMON_COLUMNS = ["kind", "page", "x0", "y0", "x1", "y1"]


def _parse_bbox(value: "str | None") -> "list[float] | None":
    if not value:
        return None
    parts = [float(v) for v in value.split(",")]
    if len(parts) != 4:
        raise SystemExit(f"error: bbox must be 'x0,y0,x1,y1' (got {value!r})")
    return parts


def _resolve_page(doc: PDFDocument, number: int) -> Page:
    if not 0 <= number < doc.page_count:
        raise SystemExit(f"error: page {number} out of range (document has {doc.page_count} pages, 0-based)")
    return doc.page(number)


def _shorten(value: Any, limit: int = 60) -> str:
    text = str(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _flatten(obj: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "kind": obj["kind"], "page": obj["page"],
        "x0": obj["bbox"][0], "y0": obj["bbox"][1], "x1": obj["bbox"][2], "y1": obj["bbox"][3],
    }
    for field in SALIENT.get(obj["kind"], ()):
        if field in obj:
            row[field] = _shorten(obj[field]) if isinstance(obj[field], str) else obj[field]
    included = {"kind", "page", "bbox", *SALIENT.get(obj["kind"], ())}
    extra = {
        key: value for key, value in obj.items()
        if key not in included and (isinstance(value, (str, int, float, bool)) or key in ("spans", "segments"))
    }
    if extra:
        row["extra"] = _shorten(json.dumps(extra, ensure_ascii=False, default=str), 300)
    return row


def _format_table(objects: list[dict[str, Any]]) -> str:
    lines = [f"{len(objects)} object(s)", "", f"{'kind':<9} {'bbox':<34} detail"]
    for obj in objects:
        bbox = "[" + ", ".join(f"{v:g}" for v in obj["bbox"]) + "]"
        detail = " ".join(
            f"{field}={_shorten(obj.get(field, ''), 40)}"
            for field in SALIENT.get(obj["kind"], ())
            if obj.get(field) not in (None, "")
        )
        lines.append(f"{obj['kind']:<9} {bbox:<34} {detail}")
    return "\n".join(lines)


def _emit(text: str, out: "str | None", ext: str) -> None:
    if out:
        path = Path(out)
        if path.suffix.lower() != f".{ext}":
            path = path.with_suffix(f".{ext}")
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path}")
    else:
        print(text)


def _write_json(payload: dict[str, Any], out: "str | None") -> None:
    _emit(json.dumps(payload, indent=2, ensure_ascii=False, default=str), out, "json")


def _write_csv(objects: list[dict[str, Any]], out: "str | None", *, flattened: bool = False) -> None:
    """Write objects (or already-flat rows, `flattened=True`) as CSV."""
    rows = objects if flattened else [_flatten(obj) for obj in objects]
    columns = list(COMMON_COLUMNS)
    for row in rows:  # union of salient columns, stable order
        for key in row:
            if key not in columns and key != "extra":
                columns.append(key)
    if any("extra" in row for row in rows):
        columns.append("extra")
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    _emit(buffer.getvalue(), out, "csv")


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #

def cmd_info(args: argparse.Namespace) -> int:
    with PDFDocument.open(args.file) as doc:
        if args.format == "json":
            _write_json({"file": str(args.file), "page_count": doc.page_count, "metadata": doc.metadata}, args.out)
        else:
            print(f"{args.file} — {doc.page_count} page(s)")
            for key, value in doc.metadata.items():
                print(f"  {key:<12} {_shorten(value, 90)}")
    return 0


def cmd_pages(args: argparse.Namespace) -> int:
    with PDFDocument.open(args.file) as doc:
        summaries = [dict(page_summary(page)) for page in doc.pages]
        if args.format == "json":
            _write_json({"file": str(args.file), "pages": summaries}, args.out)
        elif args.format == "csv":
            _write_csv(summaries, args.out, flattened=True)  # summaries are already flat rows
        else:
            print(f"{'page':>4} {'size':<14} chars words lines rects curves images annots tables")
            for s in summaries:
                size = f"{s['width']:g}x{s['height']:g}"
                print(f"{s['page']:>4} {size:<14} {s['chars']:>5} {s['words']:>5} {s['text_lines']:>5} "
                      f"{s['rects']:>5} {s['curves']:>6} {s['images']:>6} {s['annots']:>6} {s['tables']:>5}")
    return 0


def cmd_objects(args: argparse.Namespace) -> int:
    with PDFDocument.open(args.file) as doc:
        page = _resolve_page(doc, args.page)
        if args.crop:
            page = page.crop(args.crop)
        objects = page.objects(kinds=args.kinds, bbox=_parse_bbox(args.bbox), mode=args.mode)
        if args.limit:
            objects = objects[: args.limit]
        if args.format == "json":
            _write_json({
                "file": str(args.file), "page": args.page, "crop": args.crop,
                "kinds": args.kinds, "bbox": _parse_bbox(args.bbox), "mode": args.mode,
                "count": len(objects), "objects": objects,
            }, args.out)
        elif args.format == "csv":
            _write_csv(objects, args.out)
        else:
            print(_format_table(objects))
    return 0


def cmd_text(args: argparse.Namespace) -> int:
    with PDFDocument.open(args.file) as doc:
        pages = [doc.page(args.page)] if args.page is not None else doc.pages
        chunks = []
        for page in pages:
            view = page.crop(args.crop) if args.crop else page
            chunks.append(f"--- page {page.number} ---\n{view.text().rstrip()}")
        text = "\n\n".join(chunks) + "\n"
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"wrote {args.out}")
        else:
            print(text, end="")
    return 0


def cmd_tables(args: argparse.Namespace) -> int:
    with PDFDocument.open(args.file) as doc:
        page = _resolve_page(doc, args.page)
        tables = page.tables()
        if args.format == "json":
            _write_json({"file": str(args.file), "page": args.page, "count": len(tables), "tables": tables}, args.out)
        else:
            flat = [
                {"kind": "table", "page": args.page, "table": i, "row": r, "col": c,
                 "x0": entry["bbox"][0], "y0": entry["bbox"][1], "x1": entry["bbox"][2], "y1": entry["bbox"][3],
                 "cell": cell or ""}
                for i, entry in enumerate(tables)
                for r, row in enumerate(entry["cells"])
                for c, cell in enumerate(row)
            ]
            _write_csv(flat, args.out, flattened=True)
    return 0


def cmd_debug(args: argparse.Namespace) -> int:
    with PDFDocument.open(args.file) as doc:
        page = _resolve_page(doc, args.page)
        if args.crop:
            page = page.crop(args.crop)
        if args.ascii:
            print(ascii_layout(page, width=args.width))
        else:
            out = args.out or f"page{args.page}-debug.png"
            print(f"wrote {overlay_png(page, out, kinds=args.kinds, dpi=args.dpi)}")
    return 0


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdfinspect",
        description="Inspect generated PDFs in detail: chars, lines, rects, curves, images, annots, tables.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_file(p: argparse.ArgumentParser, formats: tuple[str, ...] = ("table",)) -> None:
        p.add_argument("file", help="PDF file path")
        if formats:
            p.add_argument("--format", default=formats[0], choices=formats, help="output format")
            p.add_argument("--out", help="write to this file instead of stdout")

    add_file(sub.add_parser("info", help="document metadata"), ("table", "json"))
    add_file(sub.add_parser("pages", help="per-page object counts"), ("table", "json", "csv"))

    objects = sub.add_parser("objects", help="list page objects, filtered")
    add_file(objects, ("table", "json", "csv"))
    objects.add_argument("--page", type=int, default=0, help="0-based page number (default 0)")
    objects.add_argument("--kinds", help=f"comma list from: {','.join(KINDS)} (default: all positional kinds)")
    objects.add_argument("--bbox", help="filter box 'x0,y0,x1,y1' in PDF points")
    objects.add_argument("--crop", help="crop the page to 'x0,y0,x1,y1' before extracting")
    objects.add_argument("--mode", default="intersects", choices=["intersects", "contains"],
                         help="bbox filter mode (default intersects)")
    objects.add_argument("--limit", type=int, help="stop after N objects")

    text = sub.add_parser("text", help="plain text extraction")
    add_file(text, ())
    text.add_argument("--page", type=int, help="0-based page (default: all pages)")
    text.add_argument("--crop", help="crop to 'x0,y0,x1,y1' first")
    text.add_argument("--out", help="write to this file instead of stdout")

    tables = sub.add_parser("tables", help="table detection and extraction")
    add_file(tables, ("json", "csv"))
    tables.add_argument("--page", type=int, default=0)

    debug = sub.add_parser("debug", help="visual debugging output")
    debug.add_argument("file")
    debug.add_argument("--page", type=int, default=0)
    debug.add_argument("--crop", help="crop to 'x0,y0,x1,y1' first")
    debug.add_argument("--kinds", help="comma list to highlight (default: word,textline,rect,stroke,curve,image,annot)")
    debug.add_argument("--dpi", type=int, default=150)
    debug.add_argument("--out", help="output PNG path (default page<N>-debug.png)")
    debug.add_argument("--ascii", action="store_true", help="print an ASCII layout map instead of PNG")
    debug.add_argument("--width", type=int, default=100, help="ASCII map width in characters")

    return parser


def main(argv: "Sequence[str] | None" = None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {"info": cmd_info, "pages": cmd_pages, "objects": cmd_objects,
                "text": cmd_text, "tables": cmd_tables, "debug": cmd_debug}
    try:
        return handlers[args.command](args)
    except (FileNotFoundError, pymupdf.FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
