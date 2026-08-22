"""CLI smoke tests against the bundled tasks (read-only commands)."""

import pytest

from legal_agent_bench.cli import main


def test_tasks_list(capsys):
    assert main(["tasks", "list"]) == 0
    out = capsys.readouterr().out
    for task_id in ("nda-review-001", "data-room-dd-001", "lease-abstraction-001", "msa-playbook-001"):
        assert task_id in out
    assert "WORKFLOW" in out


def test_tasks_show(capsys):
    assert main(["tasks", "show", "nda-review-001"]) == 0
    out = capsys.readouterr().out
    assert "Instructions" in out and "Rubric" in out
    assert "NDA-1" in out and "sources/nda.txt" in out
    assert "task digest:" in out


def test_tasks_show_with_documents(capsys):
    assert main(["tasks", "show", "data-room-dd-001", "--documents"]) == 0
    out = capsys.readouterr().out
    assert "MUTUAL" not in out  # different task's document must not appear
    assert "CAPITALIZATION TABLE" in out


def test_unknown_task_fails_cleanly(capsys):
    assert main(["tasks", "show", "nope-001"]) == 2
    assert "error:" in capsys.readouterr().err


def test_run_requires_known_agent():
    with pytest.raises(SystemExit):  # argparse rejects invalid --agent choice
        main(["run", "--agent", "hal9000"])
