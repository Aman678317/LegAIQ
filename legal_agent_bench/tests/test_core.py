"""Task loading and validation tests (uses a temp tasks tree)."""

import pytest

from legal_agent_bench.core import TaskError, load_task, list_tasks

from pathlib import Path

GOOD_TASK = """\
id: demo-001
name: "Demo task"
workflow: abstraction
practice_area: test
difficulty: beginner
version: 1
instructions: |
  Do the thing described here.
documents:
  - file: doc.txt
    role: the document
rubric:
  - id: D-1
    criterion: mentions the value
    weight: 2
    check: { contains_any: ["42"] }
  - id: D-2
    criterion: is organized
    weight: 1
    judge: true
"""


def _make_task(root: Path, yaml_text: str, doc: str = "value is 42\n") -> Path:
    task_dir = root / "demo-001"
    (task_dir / "sources").mkdir(parents=True)
    (task_dir / "task.yaml").write_text(yaml_text, encoding="utf-8")
    (task_dir / "sources" / "doc.txt").write_text(doc, encoding="utf-8")
    return task_dir


def test_load_valid_task(tmp_path):
    _make_task(tmp_path, GOOD_TASK)
    task = load_task("demo-001", tasks_dir=tmp_path)
    assert task.id == "demo-001"
    assert task.workflow == "abstraction"
    assert len(task.documents) == 1 and len(task.rubric) == 2
    assert task.max_points == 3
    assert task.rubric[0].mode == "check" and task.rubric[1].mode == "judge"
    assert "value is 42" in task.documents[0].read(task.dir)


def test_digest_changes_when_document_changes(tmp_path):
    _make_task(tmp_path, GOOD_TASK)
    task = load_task("demo-001", tasks_dir=tmp_path)
    first = task.digest()
    (tmp_path / "demo-001" / "sources" / "doc.txt").write_text("value is 43\n", encoding="utf-8")
    assert task.digest() != first


@pytest.mark.parametrize(
    "mutation, message_bit",
    [
        ('id: wrong-id\n', "must match directory name"),
        ("NO_INSTRUCTIONS", "missing required field 'instructions'"),
    ],
)
def test_invalid_tasks_rejected(tmp_path, mutation, message_bit):
    yaml_text = "x: y\n" if mutation == "id: wrong-id\n" else GOOD_TASK.replace(
        "instructions: |\n  Do the thing described here.\n", ""
    )
    _make_task(tmp_path, yaml_text)
    with pytest.raises(TaskError) as excinfo:
        load_task("demo-001", tasks_dir=tmp_path)
    assert message_bit in str(excinfo.value)


def test_rubric_needs_exactly_one_mode(tmp_path):
    bad = GOOD_TASK.replace("    judge: true", "    check: { contains_any: ['x'] }\n    judge: true")
    _make_task(tmp_path, bad)
    with pytest.raises(TaskError, match="exactly one"):
        load_task("demo-001", tasks_dir=tmp_path)


def test_missing_source_document_rejected(tmp_path):
    _make_task(tmp_path, GOOD_TASK)
    (tmp_path / "demo-001" / "sources" / "doc.txt").unlink()
    with pytest.raises(TaskError, match="not found"):
        load_task("demo-001", tasks_dir=tmp_path)


def test_unknown_task_lists_known_ids(tmp_path):
    _make_task(tmp_path, GOOD_TASK)
    with pytest.raises(TaskError, match="demo-001"):
        load_task("nope", tasks_dir=tmp_path)


def test_list_tasks_skips_non_task_dirs(tmp_path):
    _make_task(tmp_path, GOOD_TASK)
    (tmp_path / "notes").mkdir()
    assert [t.id for t in list_tasks(tasks_dir=tmp_path)] == ["demo-001"]


def test_bundled_tasks_load_and_validate():
    tasks = list_tasks()
    assert len(tasks) >= 4
    assert {t.id for t in tasks} >= {"nda-review-001", "data-room-dd-001", "lease-abstraction-001", "msa-playbook-001"}
    for task in tasks:
        assert task.instructions.strip()
        assert task.rubric and task.max_points > 0
        for doc, text in task.read_documents():
            assert text.strip(), f"{task.id}/{doc.file} is empty"
