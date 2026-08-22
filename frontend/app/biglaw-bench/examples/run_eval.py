#!/usr/bin/env python3
"""BigLaw Bench example evaluator — score an agent on sample benchmark tasks.

Self-contained: Python 3.10+ standard library only. Install the optional
`openai` package and set OPENAI_API_KEY to evaluate a real model; otherwise
run the bundled mock agent (a deliberately imperfect canned answer per task)
to see the scoring machinery with zero setup.

Usage:
    python run_eval.py --agent mock                  # score all tasks
    python run_eval.py --task wf-spa-deal-points     # one task
    python run_eval.py --agent openai --model gpt-5.6-terra
    python run_eval.py --task core-drafting-indemnity --show-task

Scoring semantics (mirrors the site's explainer):
  * Rubric items carry signed points on two dimensions:
    answer_quality (is the work right and complete?) and
    source_reliability (is it grounded in verifiable citations?).
  * Positive items award their points when their check passes.
  * Negative items (penalties) apply their points when their check FAILS —
    e.g. a not_contains_any check fails because the forbidden, error-prone
    content was found.
  * Task score = earned / available-positive points, reported as the
    percent of a lawyer-quality work product.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parent / "tasks"
DEFAULT_MODEL = "gpt-5.6-terra"


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #

def load_tasks() -> dict[str, dict]:
    tasks: dict[str, dict] = {}
    for path in sorted(TASKS_DIR.glob("*.json")):
        task = json.loads(path.read_text(encoding="utf-8"))
        if task["id"] in tasks:
            raise SystemExit(f"error: duplicate task id {task['id']!r}")
        tasks[task["id"]] = task
    if not tasks:
        raise SystemExit(f"error: no task files found under {TASKS_DIR}")
    return tasks


# --------------------------------------------------------------------------- #
# Checks (same shape as the explorer's rubric checks; intentionally tiny)
# --------------------------------------------------------------------------- #

def _norm(text: str) -> str:
    return " ".join(text.casefold().split())


def check_passes(check: dict, response: str) -> bool:
    """Evaluate one check spec. Operators:
    contains_any / any_of, contains_all / all_of, not_contains_any, regex."""
    normalized = _norm(response)
    (operator, operand), = check.items()

    if operator in {"contains_any", "any_of"}:
        return any(_norm(str(p)) in normalized for p in operand)
    if operator in {"contains_all", "all_of"}:
        return all(_norm(str(p)) in normalized for p in operand)
    if operator == "not_contains_any":
        return not any(_norm(str(p)) in normalized for p in operand)
    if operator == "regex":
        return re.search(str(operand), response, flags=re.IGNORECASE | re.DOTALL) is not None
    raise ValueError(f"unknown check operator {operator!r}")


# --------------------------------------------------------------------------- #
# Agents
# --------------------------------------------------------------------------- #

def mock_agent(task: dict) -> str:
    """The bundled canned answers: good but imperfect, so partial credit shows."""
    answer = task.get("sample_answer")
    if answer:
        return answer
    return (
        f"# Response — {task['title']}\n\n"
        "(generic mock response: this task has no scripted sample answer)\n"
    )


def openai_agent(task: dict, model: str) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        raise SystemExit("error: --agent openai requires the openai package (pip install openai)")
    prompt = (
        "You are a senior associate producing first-draft work product. Follow the "
        "instructions exactly, cite your sources, and do not invent facts.\n\n"
        f"# Assignment: {task['title']}\n\n{task['instructions']}\n\n"
        f"# Inputs\n{json.dumps(task.get('inputs', []), indent=2)}\n\n# Your response"
    )
    client = OpenAI(timeout=600)
    response = client.responses.create(
        model=model,
        instructions="You are a careful legal AI being evaluated on a benchmark. Format answers in clean markdown.",
        input=prompt,
    )
    return response.output_text or ""


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #

def score_task(task: dict, response: str) -> dict:
    available = sum(item["points"] for item in task["rubric"] if item["points"] > 0)
    earned = 0.0
    lines: list[str] = []
    for item in task["rubric"]:
        points = float(item["points"])
        check = item.get("check", {})
        passed = check_passes(check, response) if check else False
        if points > 0:
            awarded = points if passed else 0.0
            mark = "✓" if passed else "✗"
            note = f"+{points:g}" if passed else "unearned"
        else:
            triggered = not passed  # penalty applies when the guard FAILS
            awarded = points if triggered else 0.0
            mark = "—" if not triggered else "✗"
            note = f"{points:g} applied" if triggered else "no penalty"
        earned += awarded
        lines.append((item["id"], mark, item["criterion"], note, item["dimension"]))

    percent = 100.0 * earned / available if available else 0.0
    return {"available": available, "earned": earned, "percent": percent, "lines": lines}


def print_scorecard(task: dict, result: dict) -> None:
    print(f"\n{task['title']}  [{task['part']} / {task['category']}]")
    for item_id, mark, criterion, note, dimension in result["lines"]:
        print(f"  {item_id:<4} {mark}  {criterion[:74]:<74} {note:>8}   ({dimension})")
    print(f"\n  score: {result['earned']:g} / {result['available']} available "
          f"→ {result['percent']:.1f}% of lawyer-quality work product")


def show_task(task: dict) -> None:
    print(f"\n# {task['title']}  [{task['part']} / {task['category']}]")
    print(f"\n## Instructions\n{task['instructions']}")
    print("\n## Inputs")
    for item in task.get("inputs", []):
        print(f"  - {item['name']} ({item['kind']}) — {item['description']}")
    print("\n## Rubric")
    for item in task["rubric"]:
        sign = f"+{item['points']}" if item["points"] > 0 else str(item["points"])
        print(f"  {item['id']:<4} [{sign:>3}] ({item['dimension']}) {item['criterion']}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Score an agent on BigLaw Bench example tasks.")
    parser.add_argument("--task", help="single task id (default: all tasks)")
    parser.add_argument("--agent", default="mock", choices=["mock", "openai"])
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"model for the openai agent (default {DEFAULT_MODEL})")
    parser.add_argument("--show-task", action="store_true", help="print the task + rubric instead of scoring")
    args = parser.parse_args(argv)

    tasks = load_tasks()
    selected = [args.task] if args.task else list(tasks)
    unknown = [t for t in selected if t not in tasks]
    if unknown:
        print(f"error: unknown task(s) {unknown}. Known: {', '.join(tasks)}", file=sys.stderr)
        return 2

    summary: list[tuple[str, float]] = []
    for task_id in selected:
        task = tasks[task_id]
        if args.show_task:
            show_task(task)
            continue
        response = mock_agent(task) if args.agent == "mock" else openai_agent(task, args.model)
        result = score_task(task, response)
        print_scorecard(task, result)
        summary.append((task_id, result["percent"]))

    if summary and len(summary) > 1:
        print("\n─" * 62)
        print(f"{'task':<38} {'score':>8}")
        for task_id, percent in summary:
            print(f"{task_id:<38} {percent:>7.1f}%")
        mean = sum(p for _, p in summary) / len(summary)
        print(f"{'mean':<38} {mean:>7.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
