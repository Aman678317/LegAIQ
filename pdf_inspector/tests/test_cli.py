"""CLI tests — exercise every command against the generated sample PDF."""

import csv
import json
from pathlib import Path

import pytest

from pdf_inspector.cli import main


def test_info_table(sample_pdf: Path, capsys):
    assert main(["info", str(sample_pdf)]) == 0
    out = capsys.readouterr().out
    assert "2 page(s)" in out and "Sample inspection PDF" in out


def test_pages_table(sample_pdf: Path, capsys):
    assert main(["pages", str(sample_pdf)]) == 0
    out = capsys.readouterr().out
    assert "chars" in out and "tables" in out


def test_objects_table_and_limit(sample_pdf: Path, capsys):
    assert main(["objects", str(sample_pdf), "--page", "0", "--kinds", "word", "--limit", "3"]) == 0
    out = capsys.readouterr().out
    assert "3 object(s)" in out and "Hello" in out


def test_objects_json_out(sample_pdf: Path, tmp_path: Path, capsys):
    out_file = tmp_path / "objs.json"
    assert main(["objects", str(sample_pdf), "--page", "0", "--kinds", "word,rect",
                 "--format", "json", "--out", str(out_file)]) == 0
    payload = json.loads(out_file.read_text(encoding="utf-8"))
    kinds = {o["kind"] for o in payload["objects"]}
    assert kinds == {"word", "rect"} and payload["count"] == len(payload["objects"])
    assert "wrote" in capsys.readouterr().out


def test_objects_csv_out_and_bbox_filter(sample_pdf: Path, tmp_path: Path):
    out_file = tmp_path / "objs.csv"
    assert main(["objects", str(sample_pdf), "--page", "0", "--kinds", "word",
                 "--bbox", "0,0,250,792", "--format", "csv", "--out", str(out_file)]) == 0
    rows = list(csv.DictReader(out_file.read_text(encoding="utf-8").splitlines()))
    assert rows and all(float(r["x0"]) < 250 for r in rows)
    assert {"kind", "page", "x0", "y0", "x1", "y1", "text"} <= set(rows[0])


def test_crop_flag(sample_pdf: Path, tmp_path: Path):
    out_file = tmp_path / "crop.json"
    assert main(["objects", str(sample_pdf), "--page", "0", "--kinds", "word",
                 "--crop", "306,0,612,792", "--format", "json", "--out", str(out_file)]) == 0
    payload = json.loads(out_file.read_text(encoding="utf-8"))
    assert "Hello" not in " ".join(o.get("text", "") for o in payload["objects"])


def test_text_command_all_pages(sample_pdf: Path, capsys):
    assert main(["text", str(sample_pdf)]) == 0
    out = capsys.readouterr().out
    assert "--- page 0 ---" in out and "--- page 1 ---" in out
    assert "Hello generated world" in out and "Board approval" in out


def test_text_page_and_crop(sample_pdf: Path, capsys):
    assert main(["text", str(sample_pdf), "--page", "0", "--crop", "0,0,200,792"]) == 0
    out = capsys.readouterr().out
    assert "Hello" in out and "--- page 1" not in out


def test_tables_json_and_csv(sample_pdf: Path, tmp_path: Path):
    json_out = tmp_path / "tables.json"
    assert main(["tables", str(sample_pdf), "--page", "1", "--format", "json", "--out", str(json_out)]) == 0
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    cells = {cell for table in payload["tables"] for row in table["cells"] for cell in row if cell}
    assert "Board approval" in cells

    csv_out = tmp_path / "tables.csv"
    assert main(["tables", str(sample_pdf), "--page", "1", "--format", "csv", "--out", str(csv_out)]) == 0
    rows = list(csv.DictReader(csv_out.read_text(encoding="utf-8").splitlines()))
    assert any(r["cell"] == "Board approval" for r in rows)
    assert {"table", "row", "col", "cell"} <= set(rows[0])


def test_debug_png_and_ascii(sample_pdf: Path, tmp_path: Path, capsys):
    png = tmp_path / "overlay.png"
    assert main(["debug", str(sample_pdf), "--page", "0", "--out", str(png), "--dpi", "72"]) == 0
    assert png.exists() and png.stat().st_size > 5_000

    assert main(["debug", str(sample_pdf), "--page", "0", "--ascii", "--width", "60"]) == 0
    out = capsys.readouterr().out
    assert "legend" in out


def test_missing_file_fails_cleanly(capsys):
    assert main(["info", "does-not-exist.pdf"]) == 2
    assert "error" in capsys.readouterr().err


def test_page_out_of_range_fails_cleanly(sample_pdf: Path, capsys):
    with pytest.raises(SystemExit):
        main(["objects", str(sample_pdf), "--page", "17"])
