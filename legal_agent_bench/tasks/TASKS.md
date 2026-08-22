# Authoring guide: writing a benchmark task

A task is a folder under `tasks/`:

```text
tasks/<task-id>/
  ├── task.yaml     # required — metadata, instructions, documents, rubric
  └── sources/      # required if documents are listed — the source documents
```

The task id must equal the folder name (`nda-review-001`, `my-task-002`, …).
Loaders validate the schema and fail loudly (`labench tasks list` re-validates
everything) so a broken task can't silently produce bogus scores.

## task.yaml schema

```yaml
id: my-task-001                  # must match the folder name
name: "Short human title"        # shown in listings and reports
workflow: document_review        # document_review | data_room | abstraction | comparison
practice_area: corporate         # free text: m&a, real_estate, litigation, ...
difficulty: intermediate         # free text: beginner | intermediate | advanced
version: 1                       # bump when you change instructions or rubric

instructions: |
  Write this like a memo from a senior associate to the agent: role, client,
  the assignment, the expected output format, and any ground rules
  ("use only the attached documents", "cite section references", word limits).

documents:
  - file: contract.txt           # file under sources/
    role: Draft agreement under review

rubric:                          # at least one item; ids unique
  - id: T-1
    criterion: What a correct answer must contain or do, in one sentence.
    weight: 2                    # relative importance (default 1)
    check:                       # OPTION A: deterministic check (see below)
      contains_any: ["$4.2 million", "4.2 million"]
  - id: T-2
    criterion: A judgment criterion (organization, restraint, no hallucination).
    weight: 1
    judge: true                  # OPTION B: LLM-as-judge, anchored 0/1/2
    hint: Score 2 if ...; 1 if ...; 0 if ...   # anchor guidance for the judge
```

Every rubric item needs exactly one of `check` or `judge`.

## Check operators

Checks are composable and case-insensitive (whitespace-collapsed):

| Operator           | Example                                   | Passes when…                     |
|--------------------|-------------------------------------------|----------------------------------|
| `contains_any`     | `["$42,000", "$42,000.00"]`               | any phrase appears               |
| `contains_all`     | `["nine (9) months", "renewal"]`          | every phrase appears             |
| `not_contains_any` | `["not applicable"]`                      | no phrase appears                |
| `regex`            | `"\b1[,.]700[,.]000\b"`                   | pattern matches                  |
| `max_words`        | `600`                                     | response is at most N words      |
| `all` / `any` / `none` | `[spec, spec]`                        | every / at-least-one / no sub-spec passes |

(`any_of` / `all_of` / `none_of` are accepted as readable aliases of the
combinators.)

List several phrasings in `contains_any` — you are writing a matcher against
*correct answers*, not against one gold string. Run the mock agent to see
whether your checks fire on reasonable phrasings.

## Writing good tasks

1. **Plant verifiable facts.** The documents should contain specific values,
   dates, and defects (an expired policy, a missing signature, an off-market
   term). Those become `check` items — objective, free to score, stable
   across model versions.
2. **Write instructions like a real assignment.** Role, client, deliverable
   format, and ground rules. Ambiguity belongs in the *facts*, not in what
   you asked for.
3. **Use judge items for what checks can't see.** Organization of an index,
   defensible severity ratings, absence of hallucination, restraint from
   flagging non-issues. Always add an anchored `hint` describing what earns
   2 vs 1 vs 0 — anchored integer scales measurably improve judge agreement.
4. **Weight by consequence.** Catching an undisclosed litigation reference
   is worth more than restating a rent number.
5. **Calibrate before spending API budget.** `labench run --agent mock` and
   `--agent keyword` should score in a sane band (mock ≈ 50–90%, keyword
   low). If mock scores 100%, your checks are trivial; if it scores 0%,
   your phrasings are too narrow.
6. **Bump `version` on any change.** Runs record the task digest; the
   report flags drift so stale runs are never silently compared.

## Testing a new task

```powershell
labench tasks show my-task-001 --documents   # read it like a reviewer
labench run --task my-task-001 --agent mock  # harness smoke test
labench run --task my-task-001 --agent keyword
labench run --task my-task-001 --agent openai --judge llm
labench report                                # compare all of the above
```

Then add the task id to any comparisons and PR the whole folder — tasks are
just data.
