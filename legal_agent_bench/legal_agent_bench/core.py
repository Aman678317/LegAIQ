"""Task model, loading, and validation for the legal agent benchmark.

A task lives in ``tasks/<task-id>/`` with a ``task.yaml`` (instructions,
metadata, rubric) and its source documents in ``sources/``. See
``tasks/TASKS.md`` for the authoring guide.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = ROOT / "tasks"
RUNS_DIR = ROOT / "runs"

WORKFLOWS = {"document_review", "data_room", "abstraction", "comparison"}


class TaskError(Exception):
    """Raised when a task definition is missing or invalid."""


@dataclass
class Document:
    """One source document attached to a task."""

    file: str
    role: str = ""

    def read(self, task_dir: Path) -> str:
        path = task_dir / "sources" / self.file
        if not path.exists():
            raise TaskError(f"Document not found: {path}")
        return path.read_text(encoding="utf-8")


@dataclass
class RubricItem:
    """One scoring criterion.

    Exactly one scoring mode applies:
      * ``check``  — deterministic programmatic check (see checks.py).
      * ``judge``  — LLM-as-judge against ``criterion`` on an anchored 0/1/2 scale.
    """

    id: str
    criterion: str
    weight: float = 1.0
    check: dict[str, Any] | None = None
    judge: bool = False
    hint: str = ""  # extra anchor guidance for the judge

    @property
    def mode(self) -> str:
        return "judge" if self.judge else "check"


@dataclass
class Task:
    id: str
    name: str
    workflow: str
    practice_area: str
    difficulty: str
    version: int
    instructions: str
    documents: list[Document] = field(default_factory=list)
    rubric: list[RubricItem] = field(default_factory=list)
    dir: Path = Path()

    def read_documents(self) -> list[tuple[Document, str]]:
        return [(doc, doc.read(self.dir)) for doc in self.documents]

    def digest(self) -> str:
        """Stable hash of the task definition and all source documents."""
        hasher = hashlib.sha256()
        hasher.update((self.dir / "task.yaml").read_bytes())
        for doc, text in sorted(self.read_documents(), key=lambda pair: pair[0].file):
            hasher.update(doc.file.encode("utf-8"))
            hasher.update(text.encode("utf-8"))
        return hasher.hexdigest()[:16]

    @property
    def max_points(self) -> float:
        return sum(item.weight for item in self.rubric)


def _validate(raw: dict[str, Any], task_dir: Path) -> Task:
    task_id = raw.get("id")
    if task_id != task_dir.name:
        raise TaskError(f"{task_dir}/task.yaml: 'id' ({task_id!r}) must match directory name {task_dir.name!r}")
    for field_name in ("name", "workflow", "practice_area", "difficulty", "instructions"):
        if not raw.get(field_name):
            raise TaskError(f"{task_dir.name}: missing required field '{field_name}'")
    if raw["workflow"] not in WORKFLOWS:
        raise TaskError(f"{task_dir.name}: workflow must be one of {sorted(WORKFLOWS)}")

    documents = [Document(file=d["file"], role=d.get("role", "")) for d in raw.get("documents", [])]
    for doc in documents:
        if not (task_dir / "sources" / doc.file).exists():
            raise TaskError(f"{task_dir.name}: source document 'sources/{doc.file}' not found")

    rubric_raw = raw.get("rubric") or []
    if not rubric_raw:
        raise TaskError(f"{task_dir.name}: rubric must contain at least one item")
    rubric: list[RubricItem] = []
    seen_ids: set[str] = set()
    for item in rubric_raw:
        item_id = item.get("id")
        if not item_id or item_id in seen_ids:
            raise TaskError(f"{task_dir.name}: rubric ids must be unique and non-empty (got {item_id!r})")
        seen_ids.add(item_id)
        weight = float(item.get("weight", 1))
        if weight <= 0:
            raise TaskError(f"{task_dir.name}: rubric item {item_id} weight must be > 0")
        has_check, wants_judge = bool(item.get("check")), bool(item.get("judge"))
        if has_check == wants_judge:
            raise TaskError(f"{task_dir.name}: rubric item {item_id} needs exactly one of 'check' or 'judge'")
        rubric.append(
            RubricItem(
                id=item_id,
                criterion=item.get("criterion", ""),
                weight=weight,
                check=item.get("check"),
                judge=wants_judge,
                hint=item.get("hint", ""),
            )
        )

    return Task(
        id=task_id,
        name=raw["name"],
        workflow=raw["workflow"],
        practice_area=raw["practice_area"],
        difficulty=raw["difficulty"],
        version=int(raw.get("version", 1)),
        instructions=raw["instructions"],
        documents=documents,
        rubric=rubric,
        dir=task_dir,
    )


def load_task(task_id: str, tasks_dir: Path | None = None) -> Task:
    tasks_dir = tasks_dir or TASKS_DIR
    task_file = tasks_dir / task_id / "task.yaml"
    if not task_file.exists():
        known = ", ".join(sorted(t.name for t in tasks_dir.iterdir() if t.is_dir())) if tasks_dir.exists() else ""
        raise TaskError(f"Unknown task {task_id!r}. Known tasks: {known}")
    try:
        raw = yaml.safe_load(task_file.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TaskError(f"{task_id}: invalid YAML — {exc}") from exc
    if not isinstance(raw, dict):
        raise TaskError(f"{task_id}: task.yaml must be a mapping")
    return _validate(raw, tasks_dir / task_id)


def list_tasks(tasks_dir: Path | None = None) -> list[Task]:
    tasks_dir = tasks_dir or TASKS_DIR
    if not tasks_dir.exists():
        return []
    tasks = []
    for task_dir in sorted(tasks_dir.iterdir()):
        if (task_dir / "task.yaml").exists():
            tasks.append(load_task(task_dir.name, tasks_dir))
    return tasks
