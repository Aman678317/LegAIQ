"""Scoring engine and agent tests — hermetic: no network, no API key."""

import sys
import types

import pytest

from legal_agent_bench import scoring
from legal_agent_bench.agents import keyword_agent, mock_agent, resolve_agent
from legal_agent_bench.core import list_tasks, load_task
from legal_agent_bench.report import build_report


def _task(task_id: str):
    return load_task(task_id)


def test_check_items_binary_credit():
    task = _task("lease-abstraction-001")
    good = "Rent $6,850 with 3% escalation and $40,000 deposit; 150% holdover; $85,000 TI; 12,400 RSF; commencing October 1, 2026; renewal notice 15 months to 9 months prior."
    bad = "Rent is one thousand dollars."
    good_score = scoring.score_response(task, good, judge="off")
    bad_score = scoring.score_response(task, bad, judge="off")
    assert good_score.awarded == good_score.possible_scored  # every check item passed
    assert bad_score.awarded == 1.0  # only the trivially-satisfied max_words item passes
    assert bad_score.percent < 20
    assert good_score.percent > bad_score.percent


def test_judge_items_skipped_without_judge():
    task = _task("nda-review-001")
    result = scoring.score_response(task, "ten (10) years term flagged", judge="off")
    skipped = [i for i in result.items if i.skipped]
    assert skipped and all(i.mode == "judge" for i in skipped)
    assert result.coverage_percent < 100
    assert result.percent is not None  # programmatic subset still scored


def test_judge_partial_credit_scale(monkeypatch):
    fake_openai = types.ModuleType("openai")  # satisfy the availability probe
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    calls = []

    def fake_judge(task, item, response, model):
        calls.append(item.id)
        return {"NDA-8": (2, "full"), "NDA-9": (1, "partial")}.get(item.id, (0, "fail"))

    monkeypatch.setattr(scoring, "_judge_one", fake_judge)
    task = _task("nda-review-001")
    result = scoring.score_response(task, "The ten (10) years term and lost profits indemnity are problematic.", judge="auto")

    by_id = {i.id: i for i in result.items}
    assert by_id["NDA-8"].credit == 1.0 and "full" in by_id["NDA-8"].note
    assert by_id["NDA-9"].credit == 0.5
    assert result.judge_used and result.coverage_percent == 100
    assert set(calls) == {"NDA-8", "NDA-9"}


def test_mock_agent_scores_in_expected_band():
    """The canned mock answers should be good-but-not-perfect: 40–95% per task."""
    for task in list_tasks():
        output = mock_agent(task)
        result = scoring.score_response(task, output.text, judge="off")
        assert 40.0 <= result.percent <= 95.0, f"{task.id}: mock scored {result.percent}%"


def test_keyword_agent_runs_deterministically():
    task = _task("data-room-dd-001")
    first = keyword_agent(task).text
    second = keyword_agent(task).text
    assert first == second
    floor = scoring.score_response(task, first, judge="off")
    assert floor.percent <= 60.0  # extraction floor should not beat a real work product


def test_unknown_agent_rejected():
    with pytest.raises(ValueError, match="Known agents"):
        resolve_agent("gpt-9-turbo")


def test_build_report_comparisons_and_drift(tmp_path):
    run_a = {
        "run_id": "r1-mock", "task_id": "nda-review-001", "agent": "mock", "model": "mock",
        "task_digest": "old", "scores": {
            "percent": 55.0, "coverage_percent": 73.0,
            "items": [
                {"id": "NDA-1", "criterion": "term", "weight": 2, "mode": "check", "credit": 1.0, "skipped": False},
                {"id": "NDA-8", "criterion": "memo quality", "weight": 2, "mode": "judge", "credit": 0.0, "skipped": True},
            ],
        },
    }
    run_b = {
        "run_id": "r2-openai", "task_id": "nda-review-001", "agent": "openai", "model": "gpt-5.6-terra",
        "task_digest": "current", "scores": {
            "percent": 88.0, "coverage_percent": 100.0,
            "items": [
                {"id": "NDA-1", "criterion": "term", "weight": 2, "mode": "check", "credit": 1.0, "skipped": False},
                {"id": "NDA-8", "criterion": "memo quality", "weight": 2, "mode": "judge", "credit": 1.0, "skipped": False},
            ],
        },
    }
    markdown = build_report([run_a, run_b], current_digests={"nda-review-001": "current"})
    assert "r1-mock" in markdown and "r2-openai" in markdown
    assert "55.0 (73% cov.)" in markdown and "88.0" in markdown
    assert "Task drift" in markdown  # run_a digest != current
    assert "NDA-1" in markdown and "NDA-8" in markdown  # rubric-level comparison
    assert "—" in markdown  # skipped judge cell renders as an em dash
