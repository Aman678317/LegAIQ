"""Deterministic rubric checks — small, composable, and side-effect free.

A check spec is a dict with exactly one operator key:

    contains_any:     [str, ...]   pass if ANY phrase appears (case-insensitive)
    contains_all:     [str, ...]   pass if ALL phrases appear (case-insensitive)
    not_contains_any: [str, ...]   pass if NONE of the phrases appear
    regex:            str          pass if the pattern matches anywhere
    max_words:        int          pass if the response is at most N words
    all:              [spec, ...]  pass if every sub-spec passes
    any:              [spec, ...]  pass if at least one sub-spec passes
    none:             [spec, ...]  pass if no sub-spec passes

Phrase matching ignores case and collapses whitespace, so "USD 42,000"
matches "usd 42,000" but NOT "USD42000".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class CheckResult:
    passed: bool
    reason: str


def _normalize(text: str) -> str:
    return " ".join(text.casefold().split())


def _word_count(text: str) -> int:
    return len(text.split())


def evaluate_check(spec: dict[str, Any], response: str) -> CheckResult:
    """Evaluate one check spec against an agent response."""
    if not isinstance(spec, dict) or len(spec) != 1:
        return CheckResult(False, "check spec must be a dict with exactly one operator key")

    (operator, operand), = spec.items()
    operator = {"any_of": "any", "all_of": "all", "none_of": "none"}.get(operator, operator)
    normalized = _normalize(response)

    if operator == "contains_any":
        phrases = [str(p) for p in operand]
        hit = next((p for p in phrases if _normalize(p) in normalized), None)
        return CheckResult(hit is not None, f"found {hit!r}" if hit else f"none of {phrases} found")

    if operator == "contains_all":
        phrases = [str(p) for p in operand]
        missing = [p for p in phrases if _normalize(p) not in normalized]
        return CheckResult(not missing, "all phrases found" if not missing else f"missing {missing}")

    if operator == "not_contains_any":
        phrases = [str(p) for p in operand]
        found = [p for p in phrases if _normalize(p) in normalized]
        return CheckResult(not found, "none present" if not found else f"should not contain {found}")

    if operator == "regex":
        try:
            matched = re.search(str(operand), response, flags=re.IGNORECASE | re.DOTALL)
        except re.error as exc:
            return CheckResult(False, f"invalid regex: {exc}")
        return CheckResult(bool(matched), f"matched {matched.group(0)!r}" if matched else "pattern not found")

    if operator == "max_words":
        count = _word_count(response)
        return CheckResult(count <= int(operand), f"{count} words (limit {operand})")

    if operator in {"all", "any", "none"}:
        # Bare strings inside a combinator are shorthand for a contains_any phrase.
        results = [
            evaluate_check(sub if isinstance(sub, dict) else {"contains_any": [sub]}, response)
            for sub in operand
        ]
        if operator == "all":
            failed = [r.reason for r in results if not r.passed]
            return CheckResult(not failed, "all sub-checks passed" if not failed else f"failed: {failed}")
        if operator == "any":
            return CheckResult(any(r.passed for r in results), "at least one sub-check passed"
                               if any(r.passed for r in results) else "no sub-check passed")
        found = [r.reason for r in results if r.passed]
        return CheckResult(not found, "no forbidden sub-check matched" if not found else f"matched: {found}")

    return CheckResult(False, f"unknown operator {operator!r}")
