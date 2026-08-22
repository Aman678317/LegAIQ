"""API tests against a deterministically generated sample PDF."""

from pathlib import Path

import pytest

from pdf_inspector import KINDS, PDFDocument, ascii_layout, overlay_png, page_summary


@pytest.fixture()
def doc(sample_pdf: Path):
    with PDFDocument.open(sample_pdf) as document:
        yield document


# -- text ------------------------------------------------------------------ #

def test_chars_are_individual_and_positioned(doc):
    chars = doc.page(0).chars()
    joined = "".join(c["char"] for c in chars)
    assert "Hello generated world" in joined
    hello = next(c for c in chars if c["char"] == "H")
    assert hello["bbox"][0] < 100 and hello["bbox"][1] < 120
    assert hello["font"] == "Helvetica"
    assert hello["size"] == pytest.approx(14, abs=1.5)
    assert hello["color"].startswith("#")


def test_words_and_text_lines(doc):
    words = [w["text"] for w in doc.page(0).words()]
    assert "Hello" in words and "generated" in words
    lines = doc.page(0).text_lines()
    assert any("Hello generated world" in line["text"] for line in lines)
    assert doc.page(0).text().strip().startswith("Hello")


# -- vector graphics -------------------------------------------------------- #

def test_drawings_are_classified(doc):
    page = doc.page(0)
    assert len(page.rectangles()) >= 1
    assert len(page.lines()) >= 1
    assert len(page.curves()) >= 1
    rect = page.rectangles()[0]
    assert rect["stroke"] == "#0000ff" and rect["fill"] is None
    assert 100 < rect["bbox"][2] - rect["bbox"][0] < 300  # the drawn box, not a border artifact


# -- images & annotations --------------------------------------------------- #

def test_images(doc):
    images = doc.page(0).images()
    assert len(images) >= 1
    image = images[0]
    assert image["pixel_width"] == 16 and image["pixel_height"] == 16
    assert image["xref"] and image["bbox"][2] > image["bbox"][0]


def test_annotations(doc):
    annots = doc.page(0).annotations()
    assert len(annots) >= 1
    assert annots[0]["annot_type"] == "Highlight"
    assert annots[0]["bbox"][2] > annots[0]["bbox"][0]


# -- tables ----------------------------------------------------------------- #

def test_tables_extract_cells(doc):
    tables = doc.page(1).tables()
    assert len(tables) >= 1
    table = max(tables, key=lambda t: t["rows"] * t["cols"])
    flat = {cell for row in table["cells"] for cell in row if cell}
    assert {"Item", "Owner", "Status", "Notes"} <= flat
    assert "Board approval" in flat


# -- crops & filters --------------------------------------------------------- #

def test_crop_filters_by_geometry(doc):
    page = doc.page(0)
    words = page.words()
    top_word = min(words, key=lambda w: w["bbox"][1])  # "Hello" line, near top
    left = page.crop((0, 0, 306, 792))
    right = page.crop((306, 0, 612, 792))
    assert left.is_crop and left.size == (306, 792)
    assert any(w["text"] == top_word["text"] for w in left.words())
    assert "Hello" not in [w["text"] for w in right.words()]  # it lives at x≈72
    # the drawn rect at x 72–240 is fully inside the left half
    assert len(left.rectangles()) == len(page.rectangles())


def test_crop_of_crop_intersects(doc):
    page = doc.page(0)
    quarter = page.crop((0, 0, 306, 396)).crop((200, 200, 612, 792))
    assert quarter.size == (306 - 200, 396 - 200)


def test_crop_text_respects_clip(doc):
    page = doc.page(0)
    left = page.crop((0, 0, 200, 792)).text()
    assert "Hello" in left


def test_crop_rejects_empty_rect(doc):
    with pytest.raises(ValueError):
        doc.page(0).crop((5000, 5000, 6000, 6000))


def test_objects_filtering(doc):
    page = doc.page(0)
    both = page.objects(kinds="word,rect")
    assert {o["kind"] for o in both} == {"word", "rect"}
    assert all(o["bbox"][0] < 250 for o in page.objects(kinds="word", bbox=(0, 0, 250, 792)))
    contained = page.objects(kinds="word", bbox=(60, 80, 260, 140), mode="contains")
    assert contained and all(60 <= o["bbox"][0] and o["bbox"][2] <= 260 for o in contained)
    # position-sorted
    bboxes = [o["bbox"] for o in page.objects()]
    assert bboxes == sorted(bboxes, key=lambda b: (round(b[1], 1), round(b[0], 1)))
    with pytest.raises(ValueError, match="unknown kinds"):
        page.objects(kinds="unicorn")


def test_objects_covers_all_kinds(doc):
    for kind in KINDS:
        page = doc.page(0) if kind != "table" else doc.page(1)
        if kind == "table":
            assert page.tables()
        else:
            assert isinstance(page.objects(kinds={kind}), list)


# -- document lifecycle ------------------------------------------------------ #

def test_document_lifecycle(sample_pdf: Path):
    doc = PDFDocument.open(sample_pdf)
    assert len(doc) == 2 and doc.page_count == 2
    assert doc.page(-1).number == 1  # negative indexing
    assert doc.metadata["title"] == "Sample inspection PDF"
    doc.close()
    assert doc.is_closed
    doc.close()  # idempotent


def test_document_context_manager_and_bytes(sample_pdf: Path):
    with PDFDocument.open(sample_pdf) as doc:
        assert not doc.is_closed
    assert doc.is_closed
    from_bytes = PDFDocument.from_bytes(sample_pdf.read_bytes())
    assert from_bytes.page_count == 2
    from_bytes.close()


def test_page_out_of_range_fails_cleanly(doc):
    with pytest.raises(IndexError):
        doc.page(99)


# -- debug helpers ------------------------------------------------------------ #

def test_overlay_png_writes_file(doc, tmp_path: Path):
    out = tmp_path / "overlay.png"
    overlay_png(doc.page(0), out, kinds="word,rect,curve,image,annot", dpi=72)
    assert out.exists() and out.stat().st_size > 5_000  # a real rendered PNG


def test_overlay_on_crop(doc, tmp_path: Path):
    out = tmp_path / "crop.png"
    overlay_png(doc.page(0).crop((0, 0, 300, 400)), out, dpi=72)
    assert out.exists()


def test_ascii_layout(doc, capsys):
    text = ascii_layout(doc.page(0), width=80)
    assert "legend" in text and "word" in text
    assert set(text.splitlines()[1]) <= set(" wLiska") | {" "}  # letters only


def test_page_summary_counts(doc):
    summary = page_summary(doc.page(0))
    assert summary["words"] > 0 and summary["rects"] >= 1 and summary["images"] >= 1
    assert summary["annots"] >= 1
    assert page_summary(doc.page(1))["tables"] >= 1
