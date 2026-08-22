"""Spec-driven tests: the same JSON spec files drive every language port.

Each case runs the full recognition pipeline (all families) and compares
the complete output - Text, TypeName, Start, End and Resolution - against
the expected results in the spec.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from inga_recognizers import recognize  # noqa: E402

SPECS_DIR = Path(__file__).resolve().parents[2] / "specs"
REFERENCE = datetime(2026, 8, 22, 12, 0, 0)  # a Saturday; weeks start Monday

SPECS = {}
for path in sorted(SPECS_DIR.glob("*.json")):
    SPECS[path.stem] = json.loads(path.read_text(encoding="utf-8"))


def spec_cases():
    for family, cases in SPECS.items():
        for idx, case in enumerate(cases):
            yield pytest.param(case, id=f"{family}-{case['Culture']}-{idx:02d}")


@pytest.mark.parametrize("case", list(spec_cases()))
def test_spec(case):
    actual = recognize(case["Input"], case["Culture"], reference=REFERENCE)
    expected = case["Results"]
    assert len(actual) == len(expected), (
        f"count mismatch\ninput: {case['Input']!r}\n"
        f"expected: {[e['Text'] for e in expected]}\n"
        f"actual:   {[a['Text'] for a in actual]}"
    )
    for exp, act in zip(expected, actual):
        assert act["Text"] == exp["Text"], f"text mismatch in {case['Input']!r}: {act['Text']!r} != {exp['Text']!r}"
        assert act["TypeName"] == exp["TypeName"], (
            f"type mismatch for {exp['Text']!r}: {act['TypeName']} != {exp['TypeName']}"
        )
        assert (act["Start"], act["End"]) == (exp["Start"], exp["End"]), (
            f"span mismatch for {exp['Text']!r}: "
            f"({act['Start']},{act['End']}) != ({exp['Start']},{exp['End']})"
        )
        assert act["Resolution"] == exp["Resolution"], (
            f"resolution mismatch for {exp['Text']!r}: "
            f"{act['Resolution']} != {exp['Resolution']}"
        )


def test_spec_volume():
    total = sum(len(cases) for cases in SPECS.values())
    assert total >= 100, f"expected a solid spec suite, found {total} cases"
