"""Engine-level behavior tests beyond the spec files."""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from inga_recognizers import available_cultures, recognize  # noqa: E402

REFERENCE = datetime(2026, 8, 22, 12, 0, 0)
SPECS_DIR = Path(__file__).resolve().parents[2] / "specs"

EXPECTED_CULTURES = {"en", "zh", "fr", "es", "pt", "de", "it", "tr", "hi", "nl"}


def test_all_cultures_available():
    assert EXPECTED_CULTURES <= set(available_cultures())


def test_unknown_culture_falls_back_to_english():
    results = recognize("walk 3 km", culture="xx-YY", reference=REFERENCE)
    assert len(results) == 1
    assert results[0]["TypeName"] == "dimension"
    assert results[0]["Resolution"]["unit"] == "Kilometer"


def test_type_filter_returns_bare_numbers():
    text = "a 15% rise over 3 km"
    results = recognize(text, "en", types=["number"], reference=REFERENCE)
    assert [r["Text"] for r in results] == ["15", "3"]


def test_empty_and_whitespace_input():
    assert recognize("", "en") == []
    assert recognize("   ", "en") == []


def test_deterministic_output():
    text = "from March 1st, 2026 at 3pm covering 2,500 dollars at 5%"
    a = recognize(text, "en", reference=REFERENCE)
    b = recognize(text, "en", reference=REFERENCE)
    assert json.dumps(a) == json.dumps(b)


def test_spans_always_slice_the_input():
    """Every recognized Text must equal Input[Start:End+1] in every spec case."""
    checked = 0
    for path in SPECS_DIR.glob("*.json"):
        for case in json.loads(path.read_text(encoding="utf-8")):
            for r in recognize(case["Input"], case["Culture"], reference=REFERENCE):
                assert r["Text"] == case["Input"][r["Start"]:r["End"] + 1]
                checked += 1
    assert checked > 150


def test_devanagari_text_preserved_but_value_normalized():
    results = recognize("१२३ रुपये", "hi", reference=REFERENCE)
    assert results[0]["Text"] == "१२३ रुपये"
    assert results[0]["Resolution"]["value"] == "123"


def test_reference_date_drives_relative_resolution():
    assert recognize("tomorrow", "en", reference=REFERENCE)[0]["Resolution"]["value"] == "2026-08-23T00:00:00"
    other = datetime(2030, 1, 1, 9, 30)
    assert recognize("tomorrow", "en", reference=other)[0]["Resolution"]["value"] == "2030-01-02T00:00:00"


def test_number_inside_unit_not_double_reported():
    results = recognize("about 12 km total", "en", reference=REFERENCE)
    assert [r["TypeName"] for r in results] == ["dimension"]
