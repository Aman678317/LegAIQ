# PDF Inspector

A small, open-source command-line and Python API for examining the low-level
structure of regular, digitally generated PDFs — every character, text line,
rectangle, stroke, curve, image, and annotation, plus text and table
extraction. Built for **generated (vector) PDFs**: reports, exports, invoices,
filings. Scanned pages need OCR first; this tool will happily show you there
is no text layer (a debug view is one command away).

Powered by [PyMuPDF](https://pymupdf.readthedocs.io/) (`import pymupdf` — the
modern module name). Note PyMuPDF is AGPL-licensed; see LICENSE for what that
does and doesn't mean for using this tool.

## Setup

Python 3.10+ (3.13 recommended):

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## The five-minute walkthrough

Generate a sample PDF to poke at (text, shapes, a curve, an image, an
annotation, and a table):

```powershell
.\.venv\Scripts\python.exe tests\make_sample.py --out sample.pdf
```

Then:

```powershell
.\.venv\Scripts\pdfinspect.exe info sample.pdf
.\.venv\Scripts\pdfinspect.exe pages sample.pdf
.\.venv\Scripts\pdfinspect.exe objects sample.pdf --page 0 --kinds word,rect
.\.venv\Scripts\pdfinspect.exe objects sample.pdf --page 0 --format csv --out words.csv
.\.venv\Scripts\pdfinspect.exe tables sample.pdf --page 1 --format json
.\.venv\Scripts\pdfinspect.exe debug sample.pdf --page 0 --out overlay.png
.\.venv\Scripts\pdfinspect.exe debug sample.pdf --page 0 --ascii
```

`debug` renders the page with colored boxes drawn around exactly the objects
the accessors reported — green words, orange text lines, blue rectangles,
purple strokes, teal curves, red images, yellow annotations. The ASCII mode
prints the same map in the terminal. Extraction looking wrong? Look at the
overlay before reading any spec.

## Python API

```python
from pdf_inspector import PDFDocument

with PDFDocument.open("sample.pdf") as doc:
    print(doc.page_count, doc.metadata)

    page = doc.page(0)              # 0-based; doc.pages for all
    page.chars()                    # every char: bbox, font, size, color
    page.words()                    # words with boxes
    page.text_lines()               # lines with per-span font info
    page.rectangles()               # drawn rects (stroke/fill/width)
    page.lines()                    # line segments
    page.curves()                   # bezier paths
    page.images()                   # embedded images with pixel size + xref
    page.annotations()              # highlights, notes, stamps…
    page.tables()                   # detected tables with cell contents
    page.text()                     # plain text

    # Crop a region — every accessor works on the view:
    left = page.crop((0, 0, 297.5, 842))       # PDF points (A4 left half)
    left.words(), left.tables(), left.text()

    # Or filter without cropping:
    page.objects(kinds="word,rect", bbox=(0, 0, 200, 100), mode="intersects")
# closed cleanly on exit; doc.close() works too
```

Every object is a plain JSON-able dict:

```json
{"kind": "word", "page": 0, "bbox": [72.0, 90.1, 118.4, 104.2], "text": "Hello"}
```

Object kinds: `char`, `word`, `textline`, `rect`, `stroke`, `curve`, `image`,
`annot` (positional, filterable, position-sorted) and `table` (structural, via
`page.tables()`).

## CLI reference

| Command | What it does |
|---|---|
| `info FILE` | metadata + page count |
| `pages FILE` | per-page counts of every object kind |
| `objects FILE [--page N] [--kinds …] [--bbox x0,y0,x1,y1] [--crop …] [--mode intersects\|contains] [--limit N]` | filtered object list as `table` (default), `json`, or `csv` (`--out FILE` to save) |
| `text FILE [--page N] [--crop …]` | plain text |
| `tables FILE --page N --format json\|csv` | detected tables; CSV is one row per cell |
| `debug FILE --page N` | `--out overlay.png` colored-box overlay, or `--ascii` terminal map |

Coordinates are PDF points from the top-left (PyMuPDF convention), pages are
0-based.

## Extending

- New object kind: add an accessor on `Page` (normalize to the
  `kind/page/bbox` shape), register it in `KINDS` and `objects()`, add a
  style in `debug.STYLE`, and a row in `cli.SALIENT` for CSV columns.
- The tests build their fixtures from scratch with PyMuPDF (`tests/conftest.py`),
  so new behavior gets a deterministic PDF for free.

## License

MIT for this code; PyMuPDF is AGPL (see LICENSE).
