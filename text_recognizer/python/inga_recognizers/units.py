"""Unit recognition: dimensions, durations, currency, temperature, age.

All families attach a unit token to a previously matched number, then
normalize: dimensions/durations convert to the category base unit
(kilometers -> meters, hours -> seconds), temperatures convert to Kelvin
(including the Fahrenheit offset), and currencies report an ISO code.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .model import Match
from .numbers import _fmt_number

# stop a unit token from matching when glued to a longer word ("3 merger")
_WORD_GUARD = "(?![A-Za-zÀ-ÿ\u0400-\u04ff\u0600-\u06ff\u0900-\u097f])"


def _alt(patterns: List[str]) -> str:
    return "|".join(
        re.escape(p) for p in sorted(set(patterns), key=len, reverse=True)
    )


class _SuffixUnitFamily:
    """Base for "number + unit token" families (dimension/duration/temperature)."""

    type_name = "dimension"
    priority = 50

    def __init__(self, entries: List[Dict[str, Any]]):
        self.entries = entries
        flat: List[str] = []
        for e in entries:
            flat.extend(e.get("patterns", []))
        self._suffix_re = (
            re.compile(rf"\s?({_alt(flat)}){_WORD_GUARD}", re.IGNORECASE) if flat else None
        )

    def extract(self, text: str, numbers: List[Match]) -> List[Match]:
        if self._suffix_re is None:
            return []
        results = []
        for num in numbers:
            m = self._suffix_re.match(text, num.end + 1)
            if not m:
                continue
            entry = self._entry_for(m.group(1))
            if entry is None:
                continue
            results.append(Match(
                text=text[num.start:m.end()], start=num.start, end=m.end() - 1,
                type_name=self.type_name, priority=self.priority,
                resolution=self._resolution(num, entry),
            ))
        return results

    def _entry_for(self, token: str) -> Optional[Dict[str, Any]]:
        low = token.lower()
        for e in self.entries:
            if any(p.lower() == low for p in e.get("patterns", [])):
                return e
        return None

    def _resolution(self, num: Match, entry: Dict[str, Any]) -> Dict[str, Any]:
        value = float(num.resolution["value"])
        res: Dict[str, Any] = {"value": _fmt_number(value), "unit": entry["canonical"]}
        base = entry.get("base")
        factor = entry.get("factor")
        if base and base != entry["canonical"] and factor is not None:
            res["normalizedValue"] = _fmt_number(value * factor)
            res["normalizedUnit"] = base
        return res


class DimensionFamily(_SuffixUnitFamily):
    type_name = "dimension"
    priority = 50

    def __init__(self, cfg: Dict[str, Any]):
        super().__init__(cfg.get("dimension", []))


class DurationFamily(_SuffixUnitFamily):
    type_name = "duration"
    priority = 60

    def __init__(self, cfg: Dict[str, Any]):
        super().__init__(cfg.get("duration", []))


class TemperatureFamily(_SuffixUnitFamily):
    type_name = "temperature"
    priority = 30

    def __init__(self, cfg: Dict[str, Any]):
        super().__init__(cfg.get("temperature", []))

    def _resolution(self, num: Match, entry: Dict[str, Any]) -> Dict[str, Any]:
        value = float(num.resolution["value"])
        kelvin = value * entry.get("factor", 1.0) + entry.get("offset", 0.0)
        return {
            "value": _fmt_number(value),
            "unit": entry["canonical"],
            "normalizedValue": _fmt_number(kelvin),
            "normalizedUnit": "Kelvin",
        }


class CurrencyFamily:
    """Currency symbol adjacent to the number, or currency name with space."""

    type_name = "currency"
    priority = 40

    def __init__(self, cfg: Dict[str, Any]):
        self.entries = cfg.get("currency", [])
        symbols: List[str] = []
        names: List[str] = []
        for e in self.entries:
            symbols.extend(e.get("symbols", []))
            names.extend(e.get("names", []))
        self._sym_after = re.compile(rf"\s?({_alt(symbols)})") if symbols else None
        self._sym_before = re.compile(rf"({_alt(symbols)})\s?$") if symbols else None
        self._name_after = (
            re.compile(rf"\s({_alt(names)}){_WORD_GUARD}", re.IGNORECASE)
            if names else None
        )
        self._name_before = (
            re.compile(rf"({_alt(names)})\s?$", re.IGNORECASE) if names else None
        )

    def extract(self, text: str, numbers: List[Match]) -> List[Match]:
        results = []
        for num in numbers:
            m = self._match_after(text, num) or self._match_before(text, num)
            if m:
                results.append(m)
        return results

    def _match_after(self, text: str, num: Match) -> Optional[Match]:
        if self._sym_after is not None:
            m = self._sym_after.match(text, num.end + 1)
            if m:
                entry = self._entry_for(m.group(1), symbol=True)
                if entry:
                    return self._make(text, num, entry, num.start, m.end() - 1)
        if self._name_after is not None:
            m = self._name_after.match(text, num.end + 1)
            if m:
                entry = self._entry_for(m.group(1), symbol=False)
                if entry:
                    return self._make(text, num, entry, num.start, m.end() - 1)
        return None

    def _match_before(self, text: str, num: Match) -> Optional[Match]:
        before = text[:num.start]
        if self._sym_before is not None:
            m = self._sym_before.search(before)
            if m and m.end() == len(before):
                entry = self._entry_for(m.group(1), symbol=True)
                if entry:
                    return self._make(text, num, entry, m.start(), num.end)
        if self._name_before is not None:
            m = self._name_before.search(before)
            if m and m.end() == len(before):
                entry = self._entry_for(m.group(1), symbol=False)
                if entry:
                    return self._make(text, num, entry, m.start(), num.end)
        return None

    def _entry_for(self, token: str, symbol: bool) -> Optional[Dict[str, Any]]:
        if symbol:
            for e in self.entries:
                if token in e.get("symbols", []):
                    return e
            return None
        low = token.lower()
        for e in self.entries:
            if any(p.lower() == low for p in e.get("names", [])):
                return e
        return None

    def _make(self, text: str, num: Match, entry: Dict[str, Any], start: int, end: int) -> Match:
        res: Dict[str, Any] = {"value": num.resolution["value"], "unit": entry["canonical"]}
        if entry.get("iso"):
            res["iso"] = entry["iso"]
        return Match(
            text=text[start:end + 1], start=start, end=end,
            type_name=self.type_name, priority=self.priority,
            resolution=res,
        )


class AgeFamily:
    """Age expressions: "3 years old", "3 Jahre alt", "3 años", "3岁"."""

    type_name = "age"
    priority = 25

    def __init__(self, cfg: Dict[str, Any]):
        age = cfg.get("age", {})
        self.unit = age.get("unit", "Year")
        patterns = age.get("patterns", [])
        # patterns are regex fragments so cultures can write "years? old"
        self._re = (
            re.compile(rf"\s?({'|'.join(patterns)}){_WORD_GUARD}", re.IGNORECASE) if patterns else None
        )

    def extract(self, text: str, numbers: List[Match]) -> List[Match]:
        if self._re is None:
            return []
        results = []
        for num in numbers:
            m = self._re.match(text, num.end + 1)
            if not m:
                continue
            results.append(Match(
                text=text[num.start:m.end()], start=num.start, end=m.end() - 1,
                type_name=self.type_name, priority=self.priority,
                resolution={"value": num.resolution["value"], "unit": self.unit},
            ))
        return results
