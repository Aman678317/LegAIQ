"""Markdown report generation and run comparison.

A *run* directory under ``runs/`` contains:
  * ``run.json``     — metadata (task, agent, model, timings, task digest)
  * ``response.md``  — the agent's work product
  * ``scores.json``  — rubric scoring output (written by the score command)

``build_report`` turns one or more scored runs into a markdown report with a
summary table, per-agent aggregates, and per-task rubric-level comparisons.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core import RUNS_DIR


def load_run(run_dir: Path) -> dict[str, Any]:
    """Load one run directory into a merged run+score dict."""
    run_path = run_dir / "run.json"
    if not run_path.exists():
        raise FileNotFoundError(f"Not a run directory (missing run.json): {run_dir}")
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["dir"] = str(run_dir)
    scores_path = run_dir / "scores.json"
    run["scores"] = (
        json.loads(scores_path.read_text(encoding="utf-8")) if scores_path.exists() else None
    )
    return run


def discover_runs(runs_dir: Path = RUNS_DIR) -> list[dict[str, Any]]:
    if not runs_dir.exists():
        return []
    runs = []
    for run_dir in sorted(runs_dir.iterdir()):
        if (run_dir / "run.json").exists():
            runs.append(load_run(run_dir))
    return runs


def _fmt_score(run: dict[str, Any]) -> str:
    scores = run.get("scores")
    if not scores or scores.get("percent") is None:
        return "—"
    mark = "" if scores.get("coverage_percent", 0) >= 99.9 else f" ({scores['coverage_percent']:.0f}% cov.)"
    return f"{scores['percent']:.1f}{mark}"


def _agent_label(run: dict[str, Any]) -> str:
    label = run.get("agent", "?")
    model = run.get("model") or ""
    return f"{label} ({model})" if model and model not in {"mock", "keyword-extractive"} else label


def _rubric_table(task_id: str, runs: list[dict[str, Any]]) -> str:
    """Per-rubric-item credit for every run of one task, side by side."""
    scored = [r for r in runs if r.get("scores")]
    if not scored:
        return "_No scored runs._"
    items = scored[0]["scores"]["items"]
    by_run = {r["run_id"]: {i["id"]: i for i in r["scores"]["items"]} for r in scored}
    labels = {r["run_id"]: _agent_label(r) for r in scored}

    lines = ["| Rubric item | Weight | Mode | " + " | ".join(labels[r["run_id"]] for r in scored) + " |",
             "|---|---:|---|" + "---:|" * len(scored)]
    for item in items:
        cells = []
        for run in scored:
            entry = by_run[run["run_id"]].get(item["id"], {})
            cells.append("—" if entry.get("skipped") else f"{entry.get('credit', 0):.1f}")
        lines.append(f"| {item['id']}: {item['criterion']} | {item['weight']:g} | {item['mode']} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def build_report(runs: list[dict[str, Any]], current_digests: dict[str, str] | None = None) -> str:
    """Build the full markdown report for a set of runs."""
    current_digests = current_digests or {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# Legal Agent Benchmark — Run Report", "", f"_Generated {now} · {len(runs)} run(s)_", ""]

    scored = [r for r in runs if r.get("scores")]
    lines += ["## Summary", "",
              "| Run | Agent | Task | Score | Coverage |",
              "|---|---|---|---:|---:|"]
    for run in runs:
        scores = run.get("scores")
        score = _fmt_score(run)
        coverage = f"{scores['coverage_percent']:.0f}%" if scores else "unscored"
        lines.append(f"| `{run['run_id']}` | {_agent_label(run)} | {run['task_id']} | {score} | {coverage} |")

    if scored:
        agents: dict[str, list[float]] = {}
        for run in scored:
            percent = run["scores"].get("percent")
            if percent is not None:
                agents.setdefault(_agent_label(run), []).append(percent)
        lines += ["", "## Agent averages (per-run mean)", "", "| Agent | Runs | Mean score |", "|---|---:|---:|"]
        for label, values in sorted(agents.items()):
            lines.append(f"| {label} | {len(values)} | {sum(values) / len(values):.1f} |")

    stale = [r for r in runs if current_digests.get(r["task_id"], r.get("task_digest")) != r.get("task_digest")]
    if stale:
        lines += ["", "> ⚠️ **Task drift:** " + ", ".join(f"`{r['run_id']}`" for r in stale)
                  + " were recorded against a different version of their task. Re-run them before drawing conclusions."]

    by_task: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        by_task.setdefault(run["task_id"], []).append(run)

    for task_id, task_runs in sorted(by_task.items()):
        lines += ["", f"## Task: {task_id}", ""]
        for run in task_runs:
            scores = run.get("scores")
            note = f"{scores['percent']:.1f}% ({scores['coverage_percent']:.0f}% coverage)" if scores else "unscored"
            lines.append(f"* `{run['run_id']}` — {_agent_label(run)} — {note}")
        lines += ["", _rubric_table(task_id, task_runs)]

    return "\n".join(lines) + "\n"
