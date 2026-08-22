"""Scoring engine: deterministic checks plus an optional LLM-as-judge pass.

Rubric scoring model
--------------------
Each rubric item carries a weight. Credit per item:
  * check items: 0 or 1 (binary, deterministic)
  * judge items: 0, 0.5, or 1 (judge returns 0=fail / 1=partial / 2=pass)

Task score = awarded points / possible points, reported as a percentage.
If judge scoring is off (no API key, or ``--judge off``), judge items are
marked *skipped* and the score covers only the programmatic subset — the
report always shows coverage so scores with different coverage are never
silently compared.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from . import checks
from .core import RubricItem, Task

JUDGE_MODEL = "gpt-5.6-terra"

JUDGE_SYSTEM_PROMPT = """\
You are grading a legal professional's work product against one rubric criterion.

Score on this anchored scale:
  2 — PASS: the response fully satisfies the criterion.
  1 — PARTIAL: the response addresses the criterion but incompletely, imprecisely, \
or with material caveats.
  0 — FAIL: the criterion is not addressed, or the response gets it wrong.

Be a strict but fair grader. Judge only the criterion, not the rest of the response. \
Reply with ONLY a JSON object: {"score": 0|1|2, "rationale": "one or two sentences"}.
"""

MAX_DOCS_CHARS = 30_000
MAX_RESPONSE_CHARS = 12_000


@dataclass
class ItemScore:
    id: str
    criterion: str
    weight: float
    mode: str                 # "check" | "judge"
    credit: float             # 0..1
    awarded: float
    passed: bool | None       # for check items; None for judge items
    note: str
    skipped: bool = False


@dataclass
class ScoreResult:
    task_id: str
    items: list[ItemScore] = field(default_factory=list)
    awarded: float = 0.0
    possible: float = 0.0
    possible_scored: float = 0.0   # weight of items actually scored (not skipped)
    percent: float | None = None   # over scored items
    coverage_percent: float = 0.0  # scored weight / total weight
    judge_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "awarded": self.awarded,
            "possible": self.possible,
            "percent": self.percent,
            "coverage_percent": self.coverage_percent,
            "judge_used": self.judge_used,
            "items": [item.__dict__ for item in self.items],
        }


def _judge_one(task: Task, item: RubricItem, response: str, model: str) -> tuple[int, str]:
    """Call the LLM judge for one rubric item; returns (score 0..2, rationale)."""
    from openai import OpenAI  # lazy: judge is optional

    docs = "\n\n".join(f"### {doc.file}\n{text}" for doc, text in task.read_documents())[:MAX_DOCS_CHARS]
    criterion = f"{item.criterion}" + (f"\nJudge guidance: {item.hint}" if item.hint else "")
    prompt = (
        f"# Assignment instructions\n{task.instructions.strip()}\n\n"
        f"# Source documents\n{docs}\n\n"
        f"# Rubric criterion to grade\n{criterion}\n\n"
        f"# Response to grade\n{response[:MAX_RESPONSE_CHARS]}\n\n"
        "Return the JSON object now."
    )
    client = OpenAI(timeout=300)
    reply = client.responses.create(
        model=model,
        instructions=JUDGE_SYSTEM_PROMPT,
        input=prompt,
    ).output_text or ""
    match = re.search(r"\{.*\}", reply, flags=re.DOTALL)
    if not match:
        return 0, f"judge returned unparseable output: {reply[:120]!r}"
    try:
        payload = json.loads(match.group(0))
        score = max(0, min(2, int(payload.get("score", 0))))
        rationale = str(payload.get("rationale", ""))[:400]
        return score, rationale
    except (ValueError, TypeError) as exc:
        return 0, f"judge output error: {exc}"


def score_response(
    task: Task,
    response: str,
    judge: str = "auto",
    judge_model: str = JUDGE_MODEL,
) -> ScoreResult:
    """Score one response against the task rubric.

    ``judge``: "off" — programmatic checks only; "llm" — require the judge
    (raises if unavailable); "auto" — use the judge if OPENAI_API_KEY is set.
    """
    import os

    judge_active = judge == "llm" or (judge == "auto" and bool(os.getenv("OPENAI_API_KEY")))
    if judge_active:
        try:
            import openai  # noqa: F401
        except ImportError:
            if judge == "llm":
                raise RuntimeError("LLM judge requested but the 'openai' package is not installed.")
            judge_active = False

    result = ScoreResult(task_id=task.id, judge_used=judge_active)
    for item in task.rubric:
        result.possible += item.weight
        if item.mode == "check":
            outcome = checks.evaluate_check(item.check or {}, response)
            credit = 1.0 if outcome.passed else 0.0
            result.items.append(ItemScore(
                id=item.id, criterion=item.criterion, weight=item.weight, mode="check",
                credit=credit, awarded=credit * item.weight, passed=outcome.passed,
                note=outcome.reason,
            ))
            result.awarded += credit * item.weight
            result.possible_scored += item.weight
        else:
            if not judge_active:
                result.items.append(ItemScore(
                    id=item.id, criterion=item.criterion, weight=item.weight, mode="judge",
                    credit=0.0, awarded=0.0, passed=None, note="skipped (LLM judge off)", skipped=True,
                ))
                continue
            raw_score, rationale = _judge_one(task, item, response, judge_model)
            credit = raw_score / 2.0
            result.items.append(ItemScore(
                id=item.id, criterion=item.criterion, weight=item.weight, mode="judge",
                credit=credit, awarded=credit * item.weight, passed=(raw_score == 2),
                note=f"judge {raw_score}/2 — {rationale}",
            ))
            result.awarded += credit * item.weight
            result.possible_scored += item.weight

    if result.possible_scored > 0:
        result.percent = round(100.0 * result.awarded / result.possible_scored, 1)
    result.coverage_percent = round(100.0 * result.possible_scored / result.possible, 1) if result.possible else 0.0
    return result
