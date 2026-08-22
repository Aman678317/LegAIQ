# BigLaw Bench examples — a runnable scorer

Dependency-free (Python 3.10+, standard library only). The tasks in `tasks/`
are the same fictional examples shown on the
[explorer site](../): one JSON per task with instructions, inputs, a
two-dimension rubric, and programmatic checks.

## Run

From this directory:

```bash
# score the bundled mock agent on every task (no API key needed)
python run_eval.py --agent mock

# one task, printing the full rubric scorecard
python run_eval.py --task wf-spa-deal-points

# inspect a task and its rubric without scoring
python run_eval.py --task core-drafting-indemnity --show-task

# evaluate a real model (pip install openai; export OPENAI_API_KEY=...)
python run_eval.py --agent openai --model gpt-5.6-terra
```

## Scoring semantics

Each rubric item carries signed points on one of two dimensions —
`answer_quality` (is the work right and complete?) or `source_reliability`
(is it grounded in verifiable citations?), mirroring the official
benchmark's rubric design:

- **Positive items** award points when their check passes.
- **Negative items** (penalties) apply when their check *fails* — a
  `not_contains_any` guard fails because the forbidden, error-prone content
  showed up (e.g. a hallucinated citation).
- **Task score** = earned ÷ available-positive points, reported as the
  percent of a lawyer-quality work product.

Check operators: `contains_any` (alias `any_of`), `contains_all`
(alias `all_of`), `not_contains_any`, `regex`. All phrase matching is
case-insensitive with collapsed whitespace.

## Adding a task

Copy an existing JSON, change `id`, and edit instructions, inputs, and
rubric. Every item needs `id`, `dimension`, `criterion`, `points`, and a
`check`. The mock agent uses the optional `sample_answer` field as its
canned response — omit it and the agent returns a generic placeholder.

## Relation to the official benchmark

BigLaw Bench is a Harvey initiative; the official tasks, rubrics, and
samples live at [harveyai/biglaw-bench](https://github.com/harveyai/biglaw-bench)
(`blb-core`, `blb-workflows`, `blb-retrieval`). These examples are fictional
and independently authored for learning and scaffolding.
