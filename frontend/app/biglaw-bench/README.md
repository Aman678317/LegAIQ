# BigLaw Bench Explorer

An open-source site + sample code for understanding and running
[BigLaw Bench](https://github.com/harveyai/biglaw-bench) — a benchmark for
evaluating AI on realistic legal work.

The site lives at `/biglaw-bench` in this Next.js app:

| Page | What it covers |
|---|---|
| **Overview** | What the benchmark is, its three parts (Core, Workflows, Retrieval), the 16 Core task categories, and the kinds of legal work tested |
| **Tasks & rubrics** | Browse nine fictional example tasks — filter by part, search by practice area — each with its instructions, source pack, and complete two-dimension rubric |
| **Sample datasets** | The shipped task pack, the JSON format, and pointers to the official `blb-*` data |
| **Scoring** | How grading works: Answer Quality + Source Reliability, positive credit minus penalties, "% of lawyer-quality work product," with a fully worked example |

The `examples/` folder contains a dependency-free Python scorer
(`run_eval.py`) and the same tasks as JSON, so the scoring on the site is
reproducible from the command line:

```bash
cd examples
python run_eval.py --agent mock                # no API key needed
python run_eval.py --task wf-spa-deal-points
python run_eval.py --agent openai --model gpt-5.6-terra
```

## Working on the site

Standard Next.js app commands from `frontend/`:

```bash
npm run dev      # http://localhost:3000/biglaw-bench
npm test         # includes data-integrity tests for this folder
npm run build
```

## Structure

```text
biglaw-bench/
├── layout.tsx        # shared shell: nav (with active state) + footer
├── page.tsx          # Overview
├── tasks/            # Task explorer (filters + expandable rubrics)
├── datasets/         # Sample datasets
├── scoring/          # How scoring works, with worked arithmetic
├── data.ts           # the example-task catalog (typed)
├── components.tsx    # client components (explorer, nav, score bar)
├── data.test.ts      # catalog integrity tests
└── examples/         # runnable scorer + task JSONs + README
```

## Attribution

BigLaw Bench is a Harvey initiative. This explorer is an independent,
unaffiliated companion: all tasks, documents, and rubrics here are fictional
and authored for learning and scaffolding. For the official benchmark —
including the full datasets — see
[harveyai/biglaw-bench](https://github.com/harveyai/biglaw-bench) and
Harvey's [BigLaw Bench announcements](https://www.harvey.ai/blog/introducing-biglaw-bench).
