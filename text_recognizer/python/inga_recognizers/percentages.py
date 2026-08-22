"""Percentage recognition: "15%", "fünfzehn Prozent", "yüzde 30", "百分之20".

Works on top of the number family: every number match is checked for a
percentage token attached before (prefix) or after (suffix).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from .model import Match
from .numbers import NumberFamily, _zh_numeral_value, ZH_NUMERAL_CHARS, word_boundaries


class PercentageFamily:
    type_name = "percentage"
    priority = 20

    def __init__(self, culture_key: str, cfg: Dict[str, Any]):
        self.culture_key = culture_key
        self.pct = cfg.get("percentage", {})
        self.suffixes = sorted(self.pct.get("suffixes", []), key=len, reverse=True)
        self.prefixes = sorted(self.pct.get("prefixes", []), key=len, reverse=True)
        self._is_zh = culture_key in ("zh", "zh-cn", "zh-tw")
        # Chinese "百分之X" needs the hanzi-numeral parser, handled separately
        if self._is_zh:
            self.prefixes = [p for p in self.prefixes if p != "百分之"]
        self._pre, self._post = word_boundaries(culture_key)

    def extract(self, text: str, numbers: List[Match]) -> List[Match]:
        results: List[Match] = []
        taken: set = set()
        for num in numbers:
            m = self._match_suffix(text, num)
            if m:
                results.append(m)
                taken.add((num.start, num.end))
                continue
            m = self._match_prefix(text, num)
            if m:
                results.append(m)
                taken.add((num.start, num.end))
        if self._is_zh:
            results.extend(self._match_zh_prefix(text))
        return results

    def _match_suffix(self, text: str, num: Match) -> Match | None:
        after = text[num.end + 1:]
        for token in self.suffixes:
            if token == "%":
                pat = re.escape(token)
            elif self._is_zh:
                pat = re.escape(token)
            else:
                pat = rf"{self._pre}{re.escape(token)}{self._post}"
            m = re.match(rf"\s*{pat}", after, re.IGNORECASE)
            if m:
                end = num.end + 1 + m.end()
                return Match(
                    text=text[num.start:end], start=num.start, end=end - 1,
                    type_name=self.type_name, priority=self.priority,
                    resolution={"value": num.resolution["value"], "unit": "%"},
                )
        return None

    def _match_prefix(self, text: str, num: Match) -> Match | None:
        before = text[:num.start]
        for token in self.prefixes:
            if not token[0].isalpha() or self._is_zh:
                pat = re.escape(token)
            else:
                pat = rf"{self._pre}{re.escape(token)}{self._post}"
            m = re.search(rf"{pat}\s*$", before, re.IGNORECASE)
            if m:
                start = m.start()
                return Match(
                    text=text[start:num.end + 1], start=start, end=num.end,
                    type_name=self.type_name, priority=self.priority,
                    resolution={"value": num.resolution["value"], "unit": "%"},
                )
        return None

    def _match_zh_prefix(self, text: str) -> List[Match]:
        """Chinese "百分之X" where X is digits or hanzi numerals."""
        results = []
        for m in re.finditer(rf"百分之(\d+(?:\.\d+)?|[{ZH_NUMERAL_CHARS}]+)", text):
            body = m.group(1)
            if body.isdigit() or "." in body:
                value = body
            else:
                value = str(_zh_numeral_value(body))
            results.append(Match(
                text=m.group(), start=m.start(), end=m.end() - 1,
                type_name=self.type_name, priority=self.priority,
                resolution={"value": value, "unit": "%"},
            ))
        return results
