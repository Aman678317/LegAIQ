"""Recognition engine: orchestrates all families and resolves overlaps."""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional

from .cultures import load_culture
from .datetimes import DateTimeFamily
from .model import Match
from .numbers import NumberFamily, translate_digits
from .units import AgeFamily, CurrencyFamily, DimensionFamily, DurationFamily, TemperatureFamily
from .percentages import PercentageFamily

ALL_TYPES = (
    "number", "percentage", "dimension", "duration",
    "currency", "temperature", "age", "datetime",
)


@lru_cache(maxsize=None)
def _families(culture_key: str):
    cfg = load_culture(culture_key)
    return {
        "number": NumberFamily(culture_key, cfg),
        "percentage": PercentageFamily(culture_key, cfg),
        "dimension": DimensionFamily(cfg),
        "duration": DurationFamily(cfg),
        "currency": CurrencyFamily(cfg),
        "temperature": TemperatureFamily(cfg),
        "age": AgeFamily(cfg),
        "datetime": DateTimeFamily(culture_key, cfg),
    }


def recognize(
    text: str,
    culture: str = "en",
    types: Optional[List[str]] = None,
    reference: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Recognize numbers, percentages, units, dates and times in ``text``.

    Args:
        text: input text (any language supported by the culture files).
        culture: BCP-47-ish culture code ("en", "de", "zh", "hi", ...).
            Unknown cultures fall back to English.
        types: restrict output to these type names (subset of ALL_TYPES).
        reference: reference instant for relative date/time resolution;
            defaults to now.
    Returns:
        A list of result dicts with Text/TypeName/Start/End/Resolution,
        sorted by position.
    """
    if not text:
        return []
    reference = reference or datetime.now()
    culture_key = (culture or "en").lower()
    fam = _families(culture_key)

    transformed = translate_digits(text, culture_key)
    numbers = fam["number"].extract(transformed)

    candidates: List[Match] = []
    if types is None or "datetime" in types:
        candidates.extend(fam["datetime"].extract(transformed, reference))
    if types is None or "percentage" in types:
        candidates.extend(fam["percentage"].extract(transformed, numbers))
    if types is None or "age" in types:
        candidates.extend(fam["age"].extract(transformed, numbers))
    if types is None or "temperature" in types:
        candidates.extend(fam["temperature"].extract(transformed, numbers))
    if types is None or "currency" in types:
        candidates.extend(fam["currency"].extract(transformed, numbers))
    if types is None or "dimension" in types:
        candidates.extend(fam["dimension"].extract(transformed, numbers))
    if types is None or "duration" in types:
        candidates.extend(fam["duration"].extract(transformed, numbers))
    if types is None or "number" in types:
        candidates.extend(numbers)

    resolved = _resolve_overlaps(candidates)

    out = []
    for m in resolved:
        out.append({
            "Text": text[m.start:m.end + 1],
            "TypeName": m.type_name,
            "Start": m.start,
            "End": m.end,
            "Resolution": m.resolution,
        })
    return out


def _resolve_overlaps(candidates: List[Match]) -> List[Match]:
    """Drop matches fully contained inside a higher-precedence match.

    Equal spans across families also resolve by precedence ("2 uur" is the
    Dutch duration, not "2 o'clock"; "trois ans" is an age, not a duration).
    """
    ordered = sorted(
        candidates, key=lambda m: (m.priority, m.start, -(m.end - m.start))
    )
    kept: List[Match] = []
    for m in ordered:
        contained = False
        for k in kept:
            if k.start <= m.start and m.end <= k.end:
                if k.priority < m.priority:
                    contained = True
                elif k.priority == m.priority and (k.start, k.end) != (m.start, m.end):
                    contained = True
            if contained:
                break
        if not contained:
            kept.append(m)
    kept.sort(key=lambda m: (m.start, m.end))
    return kept
