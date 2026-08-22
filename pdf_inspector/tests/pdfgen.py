"""Deterministic sample PDF builder — used by tests and make_sample.py.

Page 0: a line of text, a rectangle, a stroke, a bezier curve, an embedded
image, and a highlight annotation over "Hello".
Page 1: a 3x4 grid table with text in every cell.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf


def build_sample_pdf(path: "str | Path") -> Path:
    path = Path(path)
    doc = pymupdf.open()

    # ---------------- page 0: mixed objects ---------------- #
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 96), "Hello generated world", fontsize=14, fontname="helv")
    page.insert_text((72, 130), "Body text for cropping tests.", fontsize=11, fontname="helv")

    shape = page.new_shape()
    shape.draw_rect(pymupdf.Rect(72, 200, 240, 280))
    shape.finish(color=(0, 0, 1), width=2)
    shape.draw_line(pymupdf.Point(300, 200), pymupdf.Point(500, 280))
    shape.finish(color=(1, 0, 0), width=1.5)
    shape.draw_bezier(pymupdf.Point(300, 320), pymupdf.Point(380, 260),
                      pymupdf.Point(460, 380), pymupdf.Point(540, 320))
    shape.finish(color=(0, 0.5, 0), width=1)
    shape.commit()

    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 16, 16))
    for y in range(16):
        for x in range(16):
            pixmap.set_pixel(x, y, (int(40 + x * 12), 90, int(200 - y * 10)))
    page.insert_image(pymupdf.Rect(72, 330, 200, 458), pixmap=pixmap)

    hits = page.search_for("Hello")
    if hits:
        page.add_highlight_annot(hits[0])

    # ---------------- page 1: table ---------------- #
    table_page = doc.new_page(width=612, height=792)
    x0, y0, x1, y1 = 72, 120, 500, 300
    rows, cols = 3, 4
    data = [
        ["Item", "Owner", "Status", "Notes"],
        ["Board approval", "Legal", "Open", "Need minutes"],
        ["IP assignments", "HR", "Done", "Tab 4"],
    ]
    grid = table_page.new_shape()
    for i in range(rows + 1):
        y = y0 + (y1 - y0) * i / rows
        grid.draw_line(pymupdf.Point(x0, y), pymupdf.Point(x1, y))
        grid.finish(color=(0, 0, 0), width=0.8)
    for j in range(cols + 1):
        x = x0 + (x1 - x0) * j / cols
        grid.draw_line(pymupdf.Point(x, y0), pymupdf.Point(x, y1))
        grid.finish(color=(0, 0, 0), width=0.8)
    grid.commit()
    for r, row in enumerate(data):
        for c, value in enumerate(row):
            cell_x = x0 + (x1 - x0) * c / cols + 4
            cell_y = y0 + (y1 - y0) * (r + 1) / rows - 8
            table_page.insert_text((cell_x, cell_y), value, fontsize=10, fontname="helv")

    doc.set_metadata({"title": "Sample inspection PDF", "author": "pdf_inspector tests"})
    doc.save(str(path))
    doc.close()
    return path


if __name__ == "__main__":  # `python tests/make_sample.py --out sample.pdf`
    import argparse

    parser = argparse.ArgumentParser(description="Generate the sample inspection PDF")
    parser.add_argument("--out", default="sample.pdf")
    build_sample_pdf(parser.parse_args().out).resolve()
    print("ok")
