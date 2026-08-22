"""Date and time recognition.

Supported expressions (per culture data):
- ISO dates (2026-08-22) and numeric dates in the culture's field order
  (en 05/22/2026, de/fr/es/pt/it/nl/tr/hi 22.08.2026, zh 2026年8月22日)
- Month-name dates ("January 5th, 2026", "5. Januar 2026", "5 de enero de 2026")
- Times: 24h (14:30, 14h30), 12h (3pm, 3 pm), localized hour words
  (de "14:30 Uhr", zh 下午3点30分, hi शाम 3 बजे)
- Relative days (today/tomorrow/yesterday) and "now"
- Weekdays resolve to their date in the reference week (Monday start)
- date + time combinations ("on August 22, 2026 at 3pm")

Results expose a TIMEX-style normalization (language independent)
plus a concrete ISO value resolved against the reference instant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from .model import Match
from .numbers import word_boundaries


@dataclass
class _DateHit:
    start: int
    end: int  # inclusive
    year: Optional[int]
    month: int
    day: int


@dataclass
class _TimeHit:
    start: int
    end: int  # inclusive
    hour: int
    minute: int
    second: int = 0


def _alt(words: List[str]) -> str:
    return "|".join(re.escape(w) for w in sorted(set(words), key=len, reverse=True))


class DateTimeFamily:
    type_name = "datetime"
    priority = 10

    def __init__(self, culture_key: str, cfg: Dict[str, Any]):
        self.culture_key = culture_key
        dt = cfg.get("datetime", {})
        self.dt = dt
        self._is_zh = culture_key in ("zh", "zh-cn", "zh-tw")
        self._is_hi = culture_key == "hi"

        self.month_words: Dict[str, int] = {}
        for idx, names in enumerate(dt.get("months", []), start=1):
            for w in names:
                self.month_words[w.lower()] = idx
        self.weekday_words: Dict[str, int] = {}
        for idx, names in enumerate(dt.get("weekdays", []), start=1):
            for w in names:
                self.weekday_words[w.lower()] = idx

        self._compile_dates(dt)
        self._compile_times(dt)
        self._compile_relative(dt)

    # ------------------------------------------------------------- dates
    def _compile_dates(self, dt: Dict[str, Any]) -> None:
        order = dt.get("dateOrder", "DMY")
        seps = "".join(re.escape(s) for s in dt.get("numericDateSeparators", ["/", "-", "."]))
        # the second separator is mandatory: "5.1.2026" is a date but the
        # German grouped number "1.234" must never match
        if order == "MDY":
            self._numeric_date_re = re.compile(
                rf"(?<![\d/.\-])(\d{{1,2}})[{seps}](\d{{1,2}})[{seps}](\d{{4}}|\d{{2}})(?!\d)"
            )
            self._numeric_groups = ("month", "day", "year")
        elif order == "YMD":
            self._numeric_date_re = None
        else:
            self._numeric_date_re = re.compile(
                rf"(?<![\d/.\-])(\d{{1,2}})[{seps}](\d{{1,2}})[{seps}](\d{{4}}|\d{{2}})(?!\d)"
            )
            self._numeric_groups = ("day", "month", "year")

        self._iso_date_re = re.compile(
            r"(?<![\d])(\d{4})-(\d{2})-(\d{2})(?!\d)"
        )

        month_alt = _alt(list(self.month_words))
        suffix_alt = "|".join(
            re.escape(s) for s in sorted(dt.get("daySuffixes", []), key=len, reverse=True)
        )
        suf = rf"(?:{suffix_alt})?" if suffix_alt else ""
        dconn = dt.get("dayMonthConnector", "")
        yconn = dt.get("yearConnector", "")
        dconn_re = rf"(?:{re.escape(dconn)}\s+)?" if dconn else ""
        yconn_re = rf"(?:{re.escape(yconn)}\s+)?" if yconn else ""
        ci = 0 if self._is_zh or self._is_hi else re.IGNORECASE

        formats = dt.get("monthDayFormats", ["day-first"])
        if "month-first" in formats:
            self._month_first_re = re.compile(
                rf"\b({month_alt})\.?\s+(\d{{1,2}}){suf}(?:\s*,?\s*(\d{{4}}))?",
                ci,
            )
        else:
            self._month_first_re = None
        if "day-first" in formats:
            self._day_first_re = re.compile(
                rf"(?<![\d])(\d{{1,2}}){suf}\.?\s*{dconn_re}({month_alt})\.?"
                rf"(?:\s*,?\s*{yconn_re}(\d{{4}}))?",
                ci,
            )
        else:
            self._day_first_re = None

        if self._is_zh:
            self._zh_full_re = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})[日号]?")
            self._zh_short_re = re.compile(r"(?<![\d年])(\d{1,2})月(\d{1,2})[日号]")

        self._weekday_re = (
            re.compile(rf"\b({_alt(list(self.weekday_words))})\b", re.IGNORECASE)
            if self.weekday_words and not self._is_zh else None
        )
        if self._is_zh:
            zh_wd = "星期一|周一|星期二|周二|星期三|周三|星期四|周四|星期五|周五|星期六|周六|星期日|周日|星期天|礼拜一|礼拜二|礼拜三|礼拜四|礼拜五|礼拜六|礼拜日|礼拜天"
            self._zh_weekday_re = re.compile(zh_wd)
            self._zh_weekday_num = {
                "星期一": 1, "周一": 1, "礼拜一": 1, "星期二": 2, "周二": 2, "礼拜二": 2,
                "星期三": 3, "周三": 3, "礼拜三": 3, "星期四": 4, "周四": 4, "礼拜四": 4,
                "星期五": 5, "周五": 5, "礼拜五": 5, "星期六": 6, "周六": 6, "礼拜六": 6,
                "星期日": 7, "周日": 7, "星期天": 7, "礼拜日": 7, "礼拜天": 7,
            }

    # ------------------------------------------------------------- times
    def _compile_times(self, dt: Dict[str, Any]) -> None:
        # letter separators (French "14 h 30") may carry spaces; symbol
        # separators like ":" stay glued to the digits
        def sep_pattern(s: str) -> str:
            e = re.escape(s)
            return rf"\s?{e}\s?" if s.isalpha() else e
        seps = "|".join(sep_pattern(s) for s in dt.get("timeSeparators", [":"]))
        self._time24_re = re.compile(
            rf"(?<![\d:.\-])(\d{{1,2}})(?:{seps})(\d{{2}})(?:(?:{seps})(\d{{2}}))?(?![\d])"
        )
        am = dt.get("ampm", {}).get("am", [])
        pm = dt.get("ampm", {}).get("pm", [])
        self._am_re = re.compile(rf"\b({_alt(am)})\b", re.IGNORECASE) if am else None
        self._pm_re = re.compile(rf"\b({_alt(pm)})\b", re.IGNORECASE) if pm else None
        if am or pm:
            self._time12_re = re.compile(
                rf"(?<![\d:.])(\d{{1,2}})(?:{seps}(\d{{2}}))?(?:{seps}(\d{{2}}))?"
                rf"\s*({_alt(am + pm)})(?![A-Za-zÀ-ÿ])"
            )
        else:
            self._time12_re = None

        hour_suffixes = dt.get("hourSuffixes", [])
        if hour_suffixes:
            self._hour_only_re = re.compile(
                rf"(?<![\d])(\d{{1,2}})\s?({_alt(hour_suffixes)})", re.IGNORECASE
            )
        else:
            self._hour_only_re = None

        if self._is_zh:
            zh_ampm = dt.get("zhAmpm", {})
            am_words = zh_ampm.get("am", [])
            pm_words = zh_ampm.get("pm", [])
            alt_ampm = "|".join(sorted(am_words + pm_words, key=len, reverse=True))
            self._zh_time_re = re.compile(
                rf"(?:({alt_ampm}))?\s*(\d{{1,2}})[点时](半|(\d{{1,2}})分?|零(\d{{1,2}})分?)?"
            )
            self._zh_am_words = set(am_words)
            self._zh_pm_words = set(pm_words)

        if self._is_hi:
            part = dt.get("hiPartOfDay", {})
            am_words = part.get("am", [])
            pm_words = part.get("pm", [])
            oclk = re.escape(dt.get("hiOClock", "बजे"))
            alt_ampm = "|".join(sorted(am_words + pm_words, key=len, reverse=True))
            self._hi_time_re = re.compile(
                rf"(?:({alt_ampm})\s+)?(\d{{1,2}})(?::(\d{{2}}))?\s*{oclk}"
            )
            self._hi_am_words = set(am_words)
            self._hi_pm_words = set(pm_words)

    def _compile_relative(self, dt: Dict[str, Any]) -> None:
        rel = dt.get("relativeDays", {})
        self._relative = {w: off for w, off in rel.items()}
        pre, post = word_boundaries(self.culture_key)
        self._relative_re = (
            re.compile(rf"{pre}({_alt(list(rel))}){post}", re.IGNORECASE) if rel else None
        )
        now_words = dt.get("now", [])
        self._now_re = (
            re.compile(rf"{pre}({_alt(now_words)}){post}", re.IGNORECASE) if now_words else None
        )
        self._connectors = dt.get("dateTimeConnectors", [])

    # --------------------------------------------------------- extraction
    def extract(self, text: str, reference: datetime) -> List[Match]:
        dates = self._extract_dates(text)
        times = self._extract_times(text)
        combined, plain_dates, plain_times = self._merge_combo(text, dates, times)
        results = [self._date_match(d, reference) for d in plain_dates]
        results += [self._time_match(t, reference) for t in plain_times]
        results += [self._combo_match(c, reference) for c in combined]
        results += self._extract_relative(text, reference)
        return results

    def _extract_dates(self, text: str) -> List[_DateHit]:
        hits: List[_DateHit] = []
        if self._is_zh:
            for m in self._zh_full_re.finditer(text):
                hits.append(_DateHit(m.start(), m.end() - 1, int(m.group(1)), int(m.group(2)), int(m.group(3))))
            for m in self._zh_short_re.finditer(text):
                hits.append(_DateHit(m.start(), m.end() - 1, None, int(m.group(1)), int(m.group(2))))
        for m in self._iso_date_re.finditer(text):
            hits.append(_DateHit(m.start(), m.end() - 1, int(m.group(1)), int(m.group(2)), int(m.group(3))))
        if self._numeric_date_re is not None:
            for m in self._numeric_date_re.finditer(text):
                a, b, y = int(m.group(1)), int(m.group(2)), m.group(3)
                first, second = (
                    (a, b) if self._numeric_groups[0] == "day" else (b, a)
                )
                day, month = (a, b) if self._numeric_groups[0] == "day" else (b, a)
                year = self._expand_year(y)
                if 1 <= month <= 12 and 1 <= day <= 31:
                    hits.append(_DateHit(m.start(), m.end() - 1, year, month, day))
        if self._month_first_re is not None:
            for m in self._month_first_re.finditer(text):
                month = self.month_words.get(m.group(1).lower())
                if month:
                    hits.append(_DateHit(
                        m.start(), m.end() - 1,
                        int(m.group(3)) if m.group(3) else None, month, int(m.group(2)),
                    ))
        if self._day_first_re is not None:
            for m in self._day_first_re.finditer(text):
                month = self.month_words.get(m.group(2).lower())
                if month:
                    hits.append(_DateHit(
                        m.start(), m.end() - 1,
                        int(m.group(3)) if m.group(3) else None, month, int(m.group(1)),
                    ))
        return hits

    def _extract_times(self, text: str) -> List[_TimeHit]:
        hits: List[_TimeHit] = []
        if self._is_zh:
            for m in self._zh_time_re.finditer(text):
                hits.append(self._zh_time_hit(m))
        if self._is_hi:
            for m in self._hi_time_re.finditer(text):
                hits.append(self._hi_time_hit(m))
        for m in self._time24_re.finditer(text):
            h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
            if h <= 23 and mi <= 59 and s <= 59:
                hits.append(_TimeHit(m.start(), m.end() - 1, h, mi, s))
        if self._time12_re is not None:
            for m in self._time12_re.finditer(text):
                h, mi, s = int(m.group(1)), int(m.group(2) or 0), int(m.group(3) or 0)
                token = m.group(4).lower()
                pm = self._pm_re is not None and self._pm_re.fullmatch(token.strip()) is not None
                if h <= 12 and mi <= 59 and s <= 59:
                    hour = h if (h == 12 and pm) or (h < 12 and not pm) else (0 if h == 12 and not pm else h + 12)
                    hits.append(_TimeHit(m.start(), m.end() - 1, hour, mi, s))
        if self._hour_only_re is not None:
            for m in self._hour_only_re.finditer(text):
                h = int(m.group(1))
                if h <= 23:
                    hits.append(_TimeHit(m.start(), m.end() - 1, h, 0, 0))
        return hits

    def _zh_time_hit(self, m: re.Match) -> _TimeHit:
        h = int(m.group(2))
        pm = m.group(1) in getattr(self, "_zh_pm_words", set())
        am = m.group(1) in getattr(self, "_zh_am_words", set())
        if pm and h < 12:
            h += 12
        elif am and h == 12:
            h = 0
        minute = 0
        if m.group(3) == "半":
            minute = 30
        elif m.group(4):
            minute = int(m.group(4))
        elif m.group(5):
            minute = int(m.group(5))
        return _TimeHit(m.start(), m.end() - 1, h, minute, 0)

    def _hi_time_hit(self, m: re.Match) -> _TimeHit:
        h = int(m.group(2))
        pm = m.group(1) in self._hi_pm_words
        if pm and h < 12:
            h += 12
        minute = int(m.group(3) or 0)
        return _TimeHit(m.start(), m.end() - 1, h, minute, 0)

    # ------------------------------------------------------------- merge
    def _merge_combo(
        self, text: str, dates: List[_DateHit], times: List[_TimeHit]
    ):
        conn_alt = _alt(self._connectors) if self._connectors else ""
        conn_re = (
            re.compile(rf"^[\s,;()\-–—]*(?:{conn_alt})[\s,;()\-–—]*$", re.IGNORECASE)
            if conn_alt else None
        )
        plain_gap_re = re.compile(r"^[\s,;()\-–—]*$")

        used_times = set()
        combined = []
        dates = sorted(dates, key=lambda d: d.start)
        for d in dates:
            for i, t in enumerate(times):
                if i in used_times or t.start <= d.end:
                    continue
                gap = text[d.end + 1:t.start]
                ok = plain_gap_re.fullmatch(gap) is not None or (
                    conn_re is not None and conn_re.fullmatch(gap) is not None
                )
                if ok and t.start - d.end <= 30:
                    combined.append((d, t))
                    used_times.add(i)
                    break
        plain_dates = [d for d in dates if not any(d is cd for cd, _ in combined)]
        plain_times = [t for i, t in enumerate(times) if i not in used_times]
        return combined, plain_dates, plain_times

    # --------------------------------------------------------- resolution
    def _date_match(self, d: _DateHit, reference: datetime) -> Match:
        year = d.year if d.year is not None else reference.year
        timex = f"{year:04d}-{d.month:02d}-{d.day:02d}" if d.year is not None else f"XXXX-{d.month:02d}-{d.day:02d}"
        value = f"{year:04d}-{d.month:02d}-{d.day:02d}T00:00:00"
        return Match(
            text=None, start=d.start, end=d.end,  # type: ignore[arg-type]
            type_name=self.type_name, priority=self.priority,
            resolution={"timex": timex, "value": value},
        )

    def _time_match(self, t: _TimeHit, reference: datetime) -> Match:
        timex = f"T{t.hour:02d}:{t.minute:02d}" + (f":{t.second:02d}" if t.second else "")
        value = f"{reference.date().isoformat()}T{t.hour:02d}:{t.minute:02d}:{t.second:02d}"
        return Match(
            text=None, start=t.start, end=t.end,  # type: ignore[arg-type]
            type_name=self.type_name, priority=self.priority,
            resolution={"timex": timex, "value": value},
        )

    def _combo_match(self, combo, reference: datetime) -> Match:
        d, t = combo
        year = d.year if d.year is not None else reference.year
        timex = (
            f"{year:04d}-{d.month:02d}-{d.day:02d}T{t.hour:02d}:{t.minute:02d}"
            + (f":{t.second:02d}" if t.second else "")
        )
        value = (
            f"{year:04d}-{d.month:02d}-{d.day:02d}"
            f"T{t.hour:02d}:{t.minute:02d}:{t.second:02d}"
        )
        return Match(
            text=None, start=d.start, end=t.end,  # type: ignore[arg-type]
            type_name=self.type_name, priority=self.priority,
            resolution={"timex": timex, "value": value},
        )

    def _extract_relative(self, text: str, reference: datetime) -> List[Match]:
        results = []
        if self._now_re is not None:
            for m in self._now_re.finditer(text):
                results.append(Match(
                    text=None, start=m.start(), end=m.end() - 1,  # type: ignore[arg-type]
                    type_name=self.type_name, priority=self.priority,
                    resolution={"timex": "PRESENT", "value": reference.strftime("%Y-%m-%dT%H:%M:%S")},
                ))
        if self._relative_re is not None:
            for m in self._relative_re.finditer(text):
                offset = self._relative[m.group(1).lower()]
                d = reference.date() + timedelta(days=offset)
                results.append(Match(
                    text=None, start=m.start(), end=m.end() - 1,  # type: ignore[arg-type]
                    type_name=self.type_name, priority=self.priority,
                    resolution={
                        "timex": d.isoformat(),
                        "value": f"{d.isoformat()}T00:00:00",
                    },
                ))
        if self._weekday_re is not None:
            for m in self._weekday_re.finditer(text):
                dow = self.weekday_words[m.group(1).lower()]
                monday = reference.date() - timedelta(days=reference.weekday())
                d = monday + timedelta(days=dow - 1)
                results.append(Match(
                    text=None, start=m.start(), end=m.end() - 1,  # type: ignore[arg-type]
                    type_name=self.type_name, priority=self.priority,
                    resolution={
                        "timex": d.isoformat(),
                        "value": f"{d.isoformat()}T00:00:00",
                    },
                ))
        if self._is_zh:
            for m in self._zh_weekday_re.finditer(text):
                dow = self._zh_weekday_num[m.group(0)]
                monday = reference.date() - timedelta(days=reference.weekday())
                d = monday + timedelta(days=dow - 1)
                results.append(Match(
                    text=None, start=m.start(), end=m.end() - 1,  # type: ignore[arg-type]
                    type_name=self.type_name, priority=self.priority,
                    resolution={
                        "timex": d.isoformat(),
                        "value": f"{d.isoformat()}T00:00:00",
                    },
                ))
        return results

    @staticmethod
    def _expand_year(y: str) -> int:
        n = int(y)
        if len(y) == 2:
            return 1900 + n if n >= 70 else 2000 + n
        return n
