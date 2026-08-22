"""Command-line interface.

    labench tasks list / show        inspect the benchmark
    labench run                      run an agent on tasks and score it
    labench score                    (re-)score an existing run
    labench report                   compare runs and write runs/report.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from . import report as report_mod
from .agents import DEFAULT_MODEL, resolve_agent
from .core import RUNS_DIR, TaskError, list_tasks, load_task
from .scoring import score_response

JUDGE_CHOICES = ("auto", "llm", "off")


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# --------------------------------------------------------------------------- #
# tasks
# --------------------------------------------------------------------------- #

def cmd_tasks(args: argparse.Namespace) -> int:
    if args.command2 == "list":
        tasks = list_tasks()
        if not tasks:
            print("No tasks found under tasks/.")
            return 0
        print(f"{'ID':<24} {'WORKFLOW':<18} {'DIFFICULTY':<12} {'DOCS':>4} {'RUBRIC':>6}  NAME")
        for task in tasks:
            print(f"{task.id:<24} {task.workflow:<18} {task.difficulty:<12} {len(task.documents):>4} "
                  f"{len(task.rubric):>6}  {task.name}")
        return 0

    if args.command2 == "show":
        try:
            task = load_task(args.task_id)
        except TaskError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"# {task.id} — {task.name}")
        print(f"workflow: {task.workflow} · practice area: {task.practice_area} · "
              f"difficulty: {task.difficulty} · version: {task.version}")
        print(f"\n## Instructions\n\n{task.instructions.strip()}")
        print("\n## Documents")
        for doc in task.documents:
            print(f"  - sources/{doc.file}" + (f" — {doc.role}" if doc.role else ""))
        if args.documents:
            for doc, text in task.read_documents():
                print(f"\n### sources/{doc.file}\n\n{'~' * 60}\n{text.rstrip()}\n{'~' * 60}")
        print(f"\n## Rubric ({task.max_points:g} points)")
        for item in task.rubric:
            mode = "judge" if item.judge else f"check: {json.dumps(item.check)}"
            print(f"  - {item.id} [{item.weight:g} pts, {mode}] {item.criterion}")
        print(f"\ntask digest: {task.digest()}")
        return 0

    print(f"error: unknown subcommand {args.command2!r}", file=sys.stderr)
    return 2


# --------------------------------------------------------------------------- #
# run / score
# --------------------------------------------------------------------------- #

def _score_run_dir(task, run_dir: Path, response_text: str, judge: str, judge_model: str) -> dict:
    result = score_response(task, response_text, judge=judge, judge_model=judge_model)
    payload = {
        "scored_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "judge_model": judge_model if result.judge_used else None,
        **result.to_dict(),
    }
    _write_json(run_dir / "scores.json", payload)
    return payload


def cmd_run(args: argparse.Namespace) -> int:
    try:
        tasks = [load_task(args.task_id)] if args.task_id else list_tasks()
    except TaskError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not tasks:
        print("error: no tasks found; use --task or add tasks under tasks/", file=sys.stderr)
        return 2

    agent_factory = resolve_agent(args.agent, model=args.model, reasoning=args.reasoning)
    failures = 0
    for task in tasks:
        run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{args.agent}-{task.id}"
        run_dir = RUNS_DIR / run_id
        print(f"▶ {task.id} — agent {args.agent!r}"
              + (f" model {args.model or DEFAULT_MODEL!r}" if args.agent == "openai" else ""))
        started = time.monotonic()
        try:
            output = agent_factory(task)
        except Exception as exc:  # noqa: BLE001 — surface agent failures per task, keep going
            print(f"  ✗ agent failed: {exc}", file=sys.stderr)
            failures += 1
            continue
        duration = time.monotonic() - started

        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "response.md").write_text(output.text, encoding="utf-8")
        _write_json(run_dir / "run.json", {
            "run_id": run_id,
            "task_id": task.id,
            "task_version": task.version,
            "task_digest": task.digest(),
            "agent": args.agent,
            "model": output.model,
            "agent_params": output.params,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "duration_s": round(duration, 2),
            "response_chars": len(output.text),
        })

        if args.no_score:
            print(f"  ✓ {output.model or args.agent} · {len(output.text):,} chars · {duration:.1f}s "
                  f"→ {run_dir} (unscored)")
            continue
        scores = _score_run_dir(task, run_dir, output.text, judge=args.judge, judge_model=args.judge_model)
        coverage = f", {scores['coverage_percent']:.0f}% coverage" if scores["coverage_percent"] < 99.9 else ""
        print(f"  ✓ {output.model or args.agent} · {len(output.text):,} chars · {duration:.1f}s "
              f"→ score {scores['percent']:.1f}%{coverage} · {run_dir}")
    return 1 if failures else 0


def cmd_score(args: argparse.Namespace) -> int:
    run_dirs = [Path(p) for p in args.run_dirs]
    if not run_dirs:
        print("error: pass one or more run directories (e.g. runs/20260101T120000Z-mock-nda-review-001)",
              file=sys.stderr)
        return 2
    exit_code = 0
    for run_dir in run_dirs:
        run_path = run_dir / "run.json"
        if not run_path.exists():
            print(f"error: {run_dir} is not a run directory", file=sys.stderr)
            exit_code = 2
            continue
        meta = json.loads(run_path.read_text(encoding="utf-8"))
        try:
            task = load_task(meta["task_id"])
        except TaskError as exc:
            print(f"error: {exc}", file=sys.stderr)
            exit_code = 2
            continue
        response = (run_dir / "response.md").read_text(encoding="utf-8")
        if task.digest() != meta.get("task_digest"):
            print(f"  ⚠ {meta['run_id']}: task changed since this run — scoring against the current version")
        scores = _score_run_dir(task, run_dir, response, judge=args.judge, judge_model=args.judge_model)
        coverage = f", {scores['coverage_percent']:.0f}% coverage" if scores["coverage_percent"] < 99.9 else ""
        print(f"  ✓ {meta['run_id']}: score {scores['percent']:.1f}%{coverage}")
    return exit_code


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #

def cmd_report(args: argparse.Namespace) -> int:
    if args.runs:
        runs = [report_mod.load_run(Path(p)) for p in args.runs]
    else:
        runs = report_mod.discover_runs(RUNS_DIR)
    if not runs:
        print("error: no runs found under runs/ (or pass directories with --runs)", file=sys.stderr)
        return 2
    current_digests = {}
    for task_id in sorted({r["task_id"] for r in runs}):
        try:
            current_digests[task_id] = load_task(task_id).digest()
        except TaskError:
            current_digests[task_id] = "?"
    markdown = report_mod.build_report(runs, current_digests)
    out_path = RUNS_DIR / "report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"→ written to {out_path}")
    return 0


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="labench",
        description="Open benchmark for AI agents on legal work: inspect tasks, run agents, score, compare.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    tasks = sub.add_parser("tasks", help="inspect benchmark tasks")
    tasks_sub = tasks.add_subparsers(dest="command2", required=True)
    tasks_sub.add_parser("list", help="list tasks")
    show = tasks_sub.add_parser("show", help="show one task in full")
    show.add_argument("task_id")
    show.add_argument("--documents", action="store_true", help="also print the source documents")

    run = sub.add_parser("run", help="run an agent on tasks and score the output")
    run.add_argument("--agent", default="mock", choices=["mock", "keyword", "openai"],
                     help="agent to run (default: mock)")
    run.add_argument("--task", dest="task_id", help="single task id (default: all tasks)")
    run.add_argument("--model", help=f"model for the openai agent (default: {DEFAULT_MODEL})")
    run.add_argument("--reasoning", default="medium", choices=["low", "medium", "high"],
                     help="reasoning effort for the openai agent")
    run.add_argument("--judge", default="auto", choices=JUDGE_CHOICES,
                     help="LLM judge for judge rubric items: auto (key present), llm, off")
    run.add_argument("--judge-model", default="gpt-5.6-terra", help="model used by the judge")
    run.add_argument("--no-score", action="store_true", help="skip scoring (score later with 'score')")
    run.set_defaults(func=cmd_run)

    score = sub.add_parser("score", help="(re-)score existing runs")
    score.add_argument("run_dirs", nargs="*", help="run directories under runs/")
    score.add_argument("--judge", default="auto", choices=JUDGE_CHOICES)
    score.add_argument("--judge-model", default="gpt-5.6-terra")
    score.set_defaults(func=cmd_score)

    rep = sub.add_parser("report", help="compare runs; writes runs/report.md")
    rep.add_argument("--runs", nargs="*", help="specific run directories (default: all under runs/)")
    rep.set_defaults(func=cmd_report)

    tasks.set_defaults(func=lambda a: cmd_tasks(a))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except TaskError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
