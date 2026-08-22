# Legal Agent Bench

An open, local-first benchmark for testing AI agents on real legal work.

Each task is a realistic assignment — an instruction memo, source documents
(a contract, a data room excerpt, a lease, a playbook), and a transparent
scoring rubric. The harness runs an agent over the tasks, scores the work
product against the rubric, and produces a markdown report that compares
runs so you can see which agent (or model, or prompt) actually performs
better.

```text
┌──────────┐   instructions + documents   ┌─────────┐   response.md   ┌──────────┐
│  tasks/  │ ───────────────────────────▶ │  agent  │ ──────────────▶ │  rubric  │
│ yaml+src │                              │ runner  │                 │  score   │──▶ runs/report.md
└──────────┘                              └─────────┘                 └──────────┘
```

- **Realistic workflows** — document review, data-room diligence assignments,
  lease abstraction, review against a negotiation playbook.
- **Hybrid scoring** — deterministic programmatic checks (exact values,
  phrases, word limits) plus an optional LLM-as-judge pass for judgment
  criteria on an anchored 0/1/2 scale.
- **Comparable runs** — every run is stored on disk with the task digest, so
  the report can compare agents rubric-item by rubric-item and warn when a
  task changed under a run.

The design follows the direction of the field: away from static Q&A
([LegalBench](https://hazyresearch.stanford.edu/legalbench/)) and toward
realistic document-driven agent work ([Harvey LAB](https://www.harvey.ai/blog/introducing-harveys-legal-agent-benchmark)),
with rubric best practices (anchored integer scales, explicit weights,
judge coverage reporting) from the LLM-as-judge literature.

## Setup

Python 3.10+ (3.13 recommended). From this directory:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,openai]"
```

- Everything except the `openai` agent and LLM-judge scoring works offline
  with no API key.
- To use real models: set `OPENAI_API_KEY` in your environment. Defaults to
  `gpt-5.6-terra`; override with `--model` / `--judge-model`.

## The 10-minute walkthrough

### 1 — Inspect the benchmark

```powershell
.\.venv\Scripts\labench tasks list
.\.venv\Scripts\labench tasks show nda-review-001
.\.venv\Scripts\labench tasks show data-room-dd-001 --documents
```

`tasks show` prints the instructions, the document list (or full documents
with `--documents`), and the complete rubric — every scoring criterion is
public before you run anything.

### 2 — Run an agent (no API key needed)

```powershell
.\.venv\Scripts\labench run --agent mock
```

This runs the bundled **mock** agent — canned, deliberately imperfect
answers — on every task and scores them. It exists so you can verify the
harness end-to-end offline and see partial credit working. The **keyword**
agent is a naive extractive baseline (returns document lines matching
instruction keywords) — a meaningful floor for comparisons.

### 3 — Run a real model

```powershell
$env:OPENAI_API_KEY = "sk-..."
.\.venv\Scripts\labench run --agent openai --model gpt-5.6-terra
```

Each run writes a directory under `runs/`:

```text
runs/20260822T143002Z-openai-nda-review-001/
  ├── run.json      # task id + digest, agent, model, duration
  ├── response.md   # the agent's work product
  └── scores.json   # rubric-item results (with judge rationales)
```

### 4 — Score (or re-score) a run

Runs are scored automatically, but you can re-score any run — for example
with the LLM judge enabled after adding a key, or with a different judge
model:

```powershell
.\.venv\Scripts\labench score runs\20260822T143002Z-mock-nda-review-001 --judge llm
```

Judge items are graded 0 = fail / 1 = partial / 2 = pass against the
criterion, with a written rationale stored in `scores.json`. With the judge
off, those items are reported as *skipped* and the score covers only the
programmatic portion — the report always shows coverage so you never compare
percentages measured on different ground.

### 5 — Review and compare runs

```powershell
.\.venv\Scripts\labench report
```

Writes `runs/report.md` (and prints it): a summary table of every run,
mean scores by agent, and — the interesting part — a per-task table with one
column per run and one row per rubric item, so you can see exactly *where*
agents differ (e.g., both catch the liability cap, only one catches the
governing-law/forum mismatch). If a task's documents changed after a run was
recorded, the report flags task drift.

## Adding a new task

Create `tasks/<task-id>/` with `task.yaml` and a `sources/` folder — no code
required:

```text
tasks/my-task-001/
  ├── task.yaml        # instructions, metadata, rubric
  └── sources/         # the documents
```

Full schema and authoring guide: [`tasks/TASKS.md`](tasks/TASKS.md). The
short version: write the assignment like a memo to an associate, attach
realistic documents with a few planted, verifiable facts, then express the
grading key as rubric items — `check:` items for anything mechanically
verifiable (values, dates, phrases, length limits) and `judge: true` items
for judgment calls. Verify your rubric with the mock and keyword agents
before spending API budget on real models.

## Improving the evaluation over time

- **Tighten checks into judges gradually.** Start with judge items where
  you're unsure how answers will phrase things; once you see stable phrasings
  across runs, convert them to deterministic checks.
- **Bump `version` and rely on digests.** Every run records the task digest;
  the report warns when scores predate a rubric change, so you can't
  accidentally mix generations of a benchmark.
- **Keep a floor.** Always keep the `keyword` baseline in your reports; an
  agent should beat extraction to justify its cost.
- **Audit the judge.** Judge rationales live in `scores.json`. When a judged
  score looks wrong, tighten the item's `hint` (anchor guidance) rather than
  editing scores by hand.

## Design notes

- **Why hybrid scoring?** Deterministic checks make scores reproducible and
  CI-friendly; judged items capture what checks can't (organization,
  restraint, non-hallucination). Weights let you emphasize what matters.
- **Why one-shot agents without tools?** The bundled `openai` agent does the
  task in a single pass over the documents — a controlled comparison of
  *capability*. The agent registry (`legal_agent_bench/agents.py`) is a
  natural place to register tool-using, multi-step, or your own agents while
  reusing the same tasks and scoring.
- **Why runs on disk instead of a database?** Each run directory is
  self-contained (prompt inputs via digest, raw response, scores), easy to
  diff, archive, and attach to bug reports.

## Repository layout

```text
tasks/                  the benchmark: one folder per task
  nda-review-001/         mutual NDA red-flag review (document review)
  data-room-dd-001/       M&A data room diligence assignment (data room)
  lease-abstraction-001/  commercial lease abstraction (abstraction)
  msa-playbook-001/       MSA vs. buyer playbook deviation chart (comparison)
legal_agent_bench/      the harness (core, agents, checks, scoring, report, cli)
tests/                  pytest suite (hermetic — no network, no API key)
runs/                   run outputs (gitignored except the folder itself)
```

## License

MIT — see [LICENSE](LICENSE). Tasks, documents, and the harness are all
fictional/sample data for benchmarking; they are not legal advice.
