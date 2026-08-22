"""Number recognition: digit numbers, word numbers, ordinals, Chinese numerals.

Digit numbers honor per-culture decimal marks, group separators and
grouping style (western 1,234,567 vs Indian 1,23,45,678). Word numbers
are matched from a per-culture atom/scale table and composed with a
sequence algorithm. Chinese cultures additionally support hanzi numerals
(三千五百) and digit-hanzi mixes (3万).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from .model import Match

_DIGIT_MAPS: Dict[str, Dict[str, str]] = {
    "hi": {
        "०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
        "५": "5", "६": "6", "७": "7", "८": "8", "९": "9",
    },
}

ZH_NUMERAL_CHARS = "〇零一二三四五六七八九两十百千万萬亿億壹贰叁肆伍陆柒捌玖拾佰仟"
# hanzi allowed to directly follow a numeral run (unit starters like 天/岁);
# other following hanzi mean the run is part of a longer word (统一, 一下)
_ZH_RIGHT_OK = set("天周岁个月次倍元亩万億亿點点")
_ZH_VALUE = {
    "〇": 0, "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "百": 100, "千": 1000,
    "万": 10000, "萬": 10000, "亿": 100000000, "億": 100000000,
    "壹": 1, "贰": 2, "叁": 3, "肆": 4, "伍": 5, "陆": 6, "柒": 7,
    "捌": 8, "玖": 9, "拾": 10, "佰": 100, "仟": 1000,
}
_ZH_SCALE = {"十": 10, "拾": 10, "百": 100, "佰": 100, "千": 1000, "仟": 1000}


def word_boundaries(culture: str) -> tuple[str, str]:
    """Boundary guards for word tokens.

    ``\\b`` assumes \\w-class characters on both sides, which fails for
    Hindi (Devanagari matras like दो/रुपये end with combining marks) and is
    meaningless for hanzi. Return (prefix, suffix) guards per culture.
    """
    if culture == "hi":
        return (r"(?<![\u0900-\u097F])", r"(?![\u0900-\u097F])")
    if culture in ("zh", "zh-cn", "zh-tw"):
        return ("", "")
    return (r"\b", r"\b")


def translate_digits(text: str, culture: str) -> str:
    """Map culture-specific digits (e.g. Devanagari) to ASCII, 1:1 length."""
    table = _DIGIT_MAPS.get(culture)
    if not table:
        return text
    return "".join(table.get(ch, ch) for ch in text)


def _esc(ch: str) -> str:
    return re.escape(ch)


def _digit_regex(num_cfg: Dict[str, Any], extra_left: str = "", zh_style: bool = False) -> re.Pattern:
    decimal = _esc(num_cfg["decimalMark"])
    group = _esc(num_cfg["groupMark"])
    space_group = "1" if num_cfg.get("spaceGroup") else "0"
    grouping = num_cfg.get("grouping", "western")

    if grouping == "indian":
        grouped = rf"\d{{1,2}}(?:{group}\d{{2}})*{group}\d{{3}}"
    elif num_cfg.get("spaceGroup"):
        grouped = rf"\d{{1,3}}(?:[{group}\u00a0 ]\d{{3}})+"
    else:
        grouped = rf"\d{{1,3}}(?:{group}\d{{3}})+"

    dec = rf"{decimal}\d+"
    core = rf"(?:{grouped}(?:{dec})?|\d+{dec}|\d+)"
    # Sign only binds when clearly standalone (start, whitespace, bracket);
    # guards stop the matcher inside "5-3", "1.5", "1,23", "v2.0".
    # extra_left admits adjacent currency symbols and the degree sign so
    # "$1,200.50" and "30°C" still expose a number to the unit families.
    # zh_style relaxes the left guard: Chinese glues digits to hanzi
    # ("租金为1,234元") without word boundaries.
    if zh_style:
        left = rf"(?:^|(?<=[^\d.,;:A-Za-z%]))"
    else:
        left = rf"(?:^|(?<=[\s(\[{extra_left}]))"
    return re.compile(
        rf"{left}([-+])?{core}(?![\d])(?![{decimal}{group}]\d)",
    )


def _parse_digit_value(raw: str, num_cfg: Dict[str, Any]) -> tuple[str, bool]:
    """Return (value string, is_decimal) for a well-formed digit number."""
    decimal = num_cfg["decimalMark"]
    group = num_cfg["groupMark"]
    body = raw
    negative = body.startswith("-")
    if body[0] in "+-":
        body = body[1:]
    if num_cfg.get("spaceGroup"):
        body = re.sub(rf"[{re.escape(group)}\u00a0 ](?=\d{{3}}(?!\d))", "", body)
    is_decimal = decimal in body
    body = body.replace(group, "") if not num_cfg.get("spaceGroup") else re.sub(rf"[{re.escape(group)}\u00a0 ]", "", body)
    int_part, _, frac_part = body.partition(decimal)
    int_norm = str(int(int_part)) if int_part else "0"
    if is_decimal:
        frac_norm = frac_part.rstrip("0")
        value = f"{int_norm}.{frac_norm}" if frac_norm else int_norm
    else:
        value = int_norm
    if negative and value != "0":
        value = "-" + value
    return value, is_decimal


def _zh_numeral_value(chars: str) -> int:
    total, section, current = 0, 0, 0
    for ch in chars:
        v = _ZH_VALUE[ch]
        if v in (10000, 100000000):
            section = (section + current) * v
            total += section
            section, current = 0, 0
        elif ch in _ZH_SCALE:
            if current == 0:
                current = 1
            section += current * _ZH_VALUE[ch]
            current = 0
        else:
            current = v
    return total + section + current


class NumberFamily:
    """Extracts cardinal and ordinal numbers."""

    type_name = "number"
    priority = 80  # lowest priority: anything containing a number wins

    def __init__(self, culture_key: str, cfg: Dict[str, Any]):
        self.culture_key = culture_key
        self.num = cfg.get("number", {})
        self.decimal = self.num.get("decimalMark", ".")
        self.group = self.num.get("groupMark", ",")
        # single-char currency symbols + degree sign may precede a number
        # "%" admits Turkish-style "%30" as a number context
        extra = "°%"
        for e in cfg.get("currency", []):
            for s in e.get("symbols", []):
                if len(s) == 1 and s not in extra:
                    extra += re.escape(s)
        self._is_zh = culture_key in ("zh", "zh-cn", "zh-tw")
        self._digit_re = _digit_regex(self.num, extra, zh_style=self._is_zh)
        self._compile_words()
        self._compile_zh()

    # ---------------------------------------------------------------- setup
    def _compile_words(self) -> None:
        self._ordinal_digit_re = None
        atoms: Dict[str, int] = dict(self.num.get("atoms", {}))
        scales: Dict[str, int] = dict(self.num.get("scales", {}))
        self._word_values = {**atoms, **scales}
        self._article_numerals = set(self.num.get("articleNumerals", []))
        self._negative_words = list(self.num.get("negativeWords", []))
        self._connectors = list(self.num.get("connectors", []))
        self._ordinal_words = dict(self.num.get("ordinalWords", {}))
        vocab = sorted(
            set(self._word_values) | set(self._negative_words)
            | set(self._connectors) | set(self._ordinal_words),
            key=len, reverse=True,
        )
        if not vocab:
            self._token_re = None
            return
        alt = "|".join(re.escape(w) for w in vocab)
        pre, post = word_boundaries(self.culture_key)
        self._token_re = re.compile(rf"{pre}(?:{alt}){post}", re.IGNORECASE)

        suffixes = self.num.get("ordinalSuffixes", [])
        if suffixes:
            alt_s = "|".join(re.escape(s) for s in sorted(suffixes, key=len, reverse=True))
            if any(s.strip() == "." for s in suffixes):
                # Bare-dot ordinals (de/tr "1.") must not swallow decimals
                # or the leading day of "5. Januar" (datetime wins by priority).
                body = rf"(?<![\w.])(\d+)(?:{alt_s}|\.)(?![\d])"
            else:
                body = rf"(?<![\w])(\d+)(?:{alt_s})(?![A-Za-z])"
            self._ordinal_digit_re = re.compile(body)
        else:
            self._ordinal_digit_re = None

    def _compile_zh(self) -> None:
        self._is_zh = self.culture_key in ("zh", "zh-cn", "zh-tw")
        if not self._is_zh:
            self._zh_run_re = None
            return
        self._zh_run_re = re.compile(
            rf"[{ZH_NUMERAL_CHARS}]+(?:点[{ZH_NUMERAL_CHARS}]+)?"
        )
        self._zh_mixed_re = re.compile(rf"(\d+(?:\.\d+)?)([万亿萬億])")
        self._zh_ordinal_re = re.compile(
            rf"第(\d+|[{ZH_NUMERAL_CHARS}]+)"
        )

    @staticmethod
    def _is_hanzi(ch: str) -> bool:
        return "\u4e00" <= ch <= "\u9fff"

    # ------------------------------------------------------------ extraction
    def extract(self, text: str) -> List[Match]:
        out: List[Match] = []
        out.extend(self._extract_digit_numbers(text))
        out.extend(self._extract_word_numbers(text))
        out.extend(self._extract_ordinals(text))
        if self._is_zh:
            out.extend(self._extract_zh_numerals(text))
            out.extend(self._extract_zh_mixed(text))
        return out

    def _extract_digit_numbers(self, text: str) -> List[Match]:
        results = []
        for m in self._digit_re.finditer(text):
            raw = m.group()
            # the optional leading separator class of (?:^|(?<=[\s(\[]))
            # is zero-width, so the match itself starts at the sign/digit
            raw = raw.lstrip(" ([")
            value, is_decimal = _parse_digit_value(raw, self.num)
            subtype = "decimal" if is_decimal else "integer"
            results.append(Match(
                text=raw, start=m.start(), end=m.start() + len(raw) - 1,
                type_name=self.type_name, priority=self.priority,
                resolution={"subtype": subtype, "value": value},
            ))
        return results

    def _extract_word_numbers(self, text: str) -> List[Match]:
        if self._token_re is None:
            return []
        tokens = list(self._token_re.finditer(text))
        results = []
        i = 0
        while i < len(tokens):
            run_start = i
            negative = False
            first_word = tokens[i].group().lower()
            if first_word in self._negative_words:
                negative = True
                i += 1
                if i >= len(tokens):
                    i = run_start + 1
                    continue
            values: List[int] = []
            spans = []
            j = i
            last_end = None
            while j < len(tokens):
                word = tokens[j].group().lower()
                if word in self._word_values:
                    if last_end is not None:
                        # only continue the run when tokens are adjacent
                        # ("twenty-three"); a long gap means unrelated words
                        # ("un 15 ... ciento")
                        gap = text[last_end:tokens[j].start()]
                        if re.fullmatch(r"[\s\-]*", gap) is None:
                            break
                    values.append(self._word_values[word])
                    spans.append(tokens[j])
                    last_end = tokens[j].end()
                    j += 1
                    continue
                # one connector ("and"/"y"/"e") may sit between value words
                if (
                    word in self._connectors
                    and last_end is not None
                    and j + 1 < len(tokens)
                    and tokens[j + 1].group().lower() in self._word_values
                ):
                    g1 = text[last_end:tokens[j].start()]
                    g2 = text[tokens[j].end():tokens[j + 1].start()]
                    if re.fullmatch(r"[\s\-]*", g1) and re.fullmatch(r"[\s\-]*", g2):
                        last_end = tokens[j].end()
                        j += 1
                        continue
                break
            if values and not (len(values) == 1 and spans[0].group().lower() in self._article_numerals):
                value = self._compose(values)
                if negative:
                    value = -value
                raw = text[spans[0].start():spans[-1].end()]
                # avoid hyphen/space edge like "twenty -one"
                results.append(Match(
                    text=raw, start=spans[0].start(), end=spans[-1].end() - 1,
                    type_name=self.type_name, priority=self.priority,
                    resolution={"subtype": "integer", "value": str(value)},
                ))
                i = j
            else:
                i = run_start + 1
                if negative:
                    i = run_start + 2
        return results

    @staticmethod
    def _compose(values: List[int]) -> int:
        total, current = 0, 0
        for v in values:
            if v >= 1000:
                total += (current or 1) * v
                current = 0
            elif v >= 100:
                current = (current or 1) * v if current < 100 else current + v
            else:
                current += v
        return total + current

    def _extract_ordinals(self, text: str) -> List[Match]:
        results = []
        if self._ordinal_digit_re is not None:
            for m in self._ordinal_digit_re.finditer(text):
                results.append(Match(
                    text=m.group(), start=m.start(), end=m.end() - 1,
                    type_name=self.type_name, priority=self.priority,
                    resolution={"subtype": "ordinal", "value": m.group(1)},
                ))
        if self._ordinal_words:
            vocab = sorted(self._ordinal_words, key=len, reverse=True)
            alt = "|".join(re.escape(w) for w in vocab)
            for m in re.finditer(rf"\b(?:{alt})\b", text, re.IGNORECASE):
                results.append(Match(
                    text=m.group(), start=m.start(), end=m.end() - 1,
                    type_name=self.type_name, priority=self.priority,
                    resolution={
                        "subtype": "ordinal",
                        "value": str(self._ordinal_words[m.group().lower()]),
                    },
                ))
        if self._is_zh and self._zh_ordinal_re is not None:
            for m in self._zh_ordinal_re.finditer(text):
                body = m.group(1)
                if body.isdigit():
                    value = body
                else:
                    value = str(_zh_numeral_value(body))
                results.append(Match(
                    text=m.group(), start=m.start(), end=m.end() - 1,
                    type_name=self.type_name, priority=self.priority,
                    resolution={"subtype": "ordinal", "value": value},
                ))
        return results

    def _extract_zh_numerals(self, text: str) -> List[Match]:
        results = []
        for m in self._zh_run_re.finditer(text):
            s, e = m.span()
            raw = m.group()
            if raw in ("万一",):  # adverb, never a number
                continue
            nxt = text[e] if e < len(text) else ""
            is_minutes = text[e:e + 2] == "分钟"
            # "十分钟" is a duration; bare "十分" is the adverb "very"
            if nxt == "分" and not is_minutes:
                continue
            # a single hanzi numeral directly after another hanzi is usually
            # part of a word (统一, 一下); longer runs are legitimate (今年三十岁)
            if s > 0 and self._is_hanzi(text[s - 1]) and len(raw) < 2 and not is_minutes:
                continue
            if nxt and self._is_hanzi(nxt) and nxt not in _ZH_RIGHT_OK and nxt != "分":
                continue
            if "点" in raw:
                int_part, frac_part = raw.split("点", 1)
                int_val = _zh_numeral_value(int_part) if int_part else 0
                frac_digits = "".join(
                    str(_ZH_VALUE[c]) for c in frac_part
                )
                value = f"{int_val}.{frac_digits}".rstrip("0").rstrip(".")
                subtype = "decimal"
            else:
                value = str(_zh_numeral_value(raw))
                subtype = "integer"
            if value in ("", "0") and raw not in ("零", "〇"):
                continue
            results.append(Match(
                text=raw, start=s, end=e - 1,
                type_name=self.type_name, priority=self.priority,
                resolution={"subtype": subtype, "value": value},
            ))
        return results

    def _extract_zh_mixed(self, text: str) -> List[Match]:
        results = []
        for m in self._zh_mixed_re.finditer(text):
            num = float(m.group(1))
            scale = _ZH_VALUE[m.group(2)]
            value = num * scale
            results.append(Match(
                text=m.group(), start=m.start(), end=m.end() - 1,
                type_name=self.type_name, priority=self.priority,
                resolution={"subtype": "integer", "value": _fmt_number(value)},
            ))
        return results


def _fmt_number(value: float) -> str:
    if value == int(value):
        return str(int(value))
    s = f"{value:.10f}".rstrip("0").rstrip(".")
    return s
