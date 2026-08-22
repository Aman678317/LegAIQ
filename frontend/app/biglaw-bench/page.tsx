import Link from "next/link";
import {
  ArrowRight, BookOpen, CheckCircle2, FileSearch, Gavel, Search, Sparkles, Terminal, Workflow,
} from "lucide-react";
import { CATEGORIES_BY_TRACK, PARTS, TASKS, WORK_KINDS, rubricTotals, type Part } from "./data";
import { PartBadge } from "./components";

const PART_ICONS: Record<Part, typeof Gavel> = { core: Gavel, workflows: Workflow, retrieval: Search };
const PART_ACCENT: Record<Part, string> = {
  core: "text-sky-300 border-sky-400/25",
  workflows: "text-violet-300 border-violet-400/25",
  retrieval: "text-emerald-300 border-emerald-400/25",
};
const PART_FILL: Record<Part, string> = {
  core: "from-sky-400/10",
  workflows: "from-violet-500/10",
  retrieval: "from-emerald-400/10",
};

const CORE_CATEGORY_COUNT = CATEGORIES_BY_TRACK.transactional.length + CATEGORIES_BY_TRACK.litigation.length;

const totalPositive = TASKS.reduce((sum, task) => sum + rubricTotals(task.rubric).positive, 0);

export default function BigLawBenchOverview() {
  return (
    <main>
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-white/10">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(56,189,248,0.14),transparent_55%),radial-gradient(ellipse_at_80%_20%,rgba(139,92,246,0.14),transparent_40%)]" />
        <div className="relative mx-auto max-w-6xl px-6 py-20 md:py-28">
          <div className="max-w-3xl">
            <p className="mb-6 inline-flex items-center gap-2 rounded-full border border-sky-300/20 bg-sky-300/10 px-3 py-1 text-xs font-medium text-sky-200">
              <Sparkles size={13} /> An open explorer for the BigLaw Bench legal AI benchmark
            </p>
            <h1 className="text-4xl leading-[1.05] font-semibold tracking-tight md:text-6xl">
              Understand — and run — a benchmark built from real legal work.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-slate-300">
              BigLaw Bench measures how well AI systems do the work lawyers actually bill for: drafting, research, due
              diligence, deal work, and document retrieval. This explorer breaks the benchmark into its three parts,
              lets you browse example tasks with their grading rubrics, and ships a runnable scorer so you can evaluate
              a model yourself.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link href="/biglaw-bench/tasks" className="inline-flex items-center gap-2 rounded-lg bg-sky-400 px-4 py-2.5 font-medium text-slate-950 hover:bg-sky-300">
                Browse tasks & rubrics <ArrowRight size={16} />
              </Link>
              <Link href="/biglaw-bench/scoring" className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-4 py-2.5 font-medium hover:bg-white/5">
                How scoring works
              </Link>
            </div>
          </div>

          <dl className="mt-16 grid grid-cols-2 gap-4 md:grid-cols-4">
            {[
              ["3", "benchmark parts"],
              [`${CORE_CATEGORY_COUNT}`, "Core task categories"],
              [`${TASKS.length}`, "example tasks in this explorer"],
              [`${totalPositive}+`, "rubric points across examples"],
            ].map(([value, label]) => (
              <div key={label} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                <dt className="text-2xl font-semibold text-white md:text-3xl">{value}</dt>
                <dd className="mt-1 text-xs text-slate-400">{label}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* The three parts */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <p className="text-sm font-semibold tracking-[0.18em] text-sky-300 uppercase">The three parts</p>
        <div className="mt-4 flex flex-col justify-between gap-6 md:flex-row md:items-end">
          <h2 className="max-w-2xl text-3xl font-semibold tracking-tight md:text-4xl">
            Reason, complete a workflow, and find the right source.
          </h2>
          <p className="max-w-sm text-sm leading-relaxed text-slate-400">
            A trustworthy legal system needs all three. The official benchmark splits evaluation the same way, so a
            weakness can never hide behind a strength.
          </p>
        </div>

        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {(Object.keys(PARTS) as Part[]).map((part) => {
            const meta = PARTS[part];
            const Icon = PART_ICONS[part];
            const count = TASKS.filter((task) => task.part === part).length;
            return (
              <article key={part} className={`rounded-2xl border bg-gradient-to-b to-transparent p-7 ${PART_ACCENT[part]} ${PART_FILL[part]}`}>
                <div className="flex items-center justify-between">
                  <Icon size={24} aria-hidden />
                  <span className="rounded-full border border-white/10 px-2 py-0.5 text-[11px] text-slate-400">{count} sample tasks</span>
                </div>
                <p className="mt-6 text-sm font-medium">{meta.tagline}</p>
                <h3 className="mt-1.5 text-2xl font-semibold text-white">{meta.name}</h3>
                <p className="mt-3 text-sm leading-relaxed text-slate-400">{meta.description}</p>
                <Link href={`/biglaw-bench/tasks?part=${part}`} className="mt-6 inline-flex items-center gap-1.5 text-sm font-medium text-slate-200 hover:text-white">
                  Explore {meta.name.toLowerCase()} tasks <ArrowRight size={14} />
                </Link>
              </article>
            );
          })}
        </div>
      </section>

      {/* Kinds of legal work */}
      <section className="border-y border-white/10 bg-white/[0.025] py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="flex items-center gap-3 text-emerald-300">
            <FileSearch size={18} />
            <span className="text-sm font-semibold tracking-[0.18em] uppercase">Kinds of legal work</span>
          </div>
          <h2 className="mt-4 max-w-3xl text-3xl font-semibold tracking-tight md:text-4xl">
            The work being tested is the work firms actually do.
          </h2>
          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-[#0b1728] p-6">
              <p className="text-[11px] font-semibold tracking-wider text-slate-500 uppercase">Transactional & litigation categories (Core)</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {[...CATEGORIES_BY_TRACK.transactional, ...CATEGORIES_BY_TRACK.litigation].map(({ label }) => (
                  <span key={label} className="rounded-md bg-white/5 px-2.5 py-1 text-xs text-slate-300">{label}</span>
                ))}
              </div>
              <p className="mt-4 text-xs leading-relaxed text-slate-500">
                The official benchmark groups Core into 9 transactional and 7 litigation categories — from drafting and
                due diligence to transcript analysis and trial preparation.
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-[#0b1728] p-6">
              <p className="text-[11px] font-semibold tracking-wider text-slate-500 uppercase">Workflows & retrieval</p>
              <ul className="mt-3 space-y-3 text-sm text-slate-300">
                <li className="flex gap-2.5">
                  <PartBadge part="workflows" />
                  <span><strong className="font-semibold">SPA Deal Points</strong> — extract every negotiated deal point from a Share Purchase Agreement, cross-references and all.</span>
                </li>
                <li className="flex gap-2.5">
                  <PartBadge part="retrieval" />
                  <span><strong className="font-semibold">Contracts</strong> — long merger agreements and SPAs with dense defined terms.</span>
                </li>
                <li className="flex gap-2.5">
                  <PartBadge part="retrieval" />
                  <span><strong className="font-semibold">Discovery Emails</strong> — high-volume short documents with threading and metadata.</span>
                </li>
              </ul>
            </div>
          </div>
          <div className="mt-6 flex flex-wrap gap-2">
            {WORK_KINDS.map((kind) => (
              <span key={kind} className="flex items-center gap-1.5 rounded-full border border-emerald-400/20 bg-emerald-400/5 px-3 py-1 text-xs text-emerald-200">
                <CheckCircle2 size={12} /> {kind}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Quickstart */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <div className="grid gap-10 lg:grid-cols-[1fr_1.1fr] lg:items-center">
          <div>
            <div className="flex items-center gap-3 text-sky-300">
              <Terminal size={18} />
              <span className="text-sm font-semibold tracking-[0.18em] uppercase">Run it yourself</span>
            </div>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight md:text-4xl">A runnable scorer ships with the explorer.</h2>
            <p className="mt-4 leading-relaxed text-slate-400">
              The <code className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[13px] text-sky-200">examples/</code>{" "}
              folder in this project contains sample tasks as JSON and a dependency-free Python runner. Score the bundled
              mock agent to see the machinery, then point it at a real model with one flag.
            </p>
            <Link href="/biglaw-bench/datasets" className="mt-6 inline-flex items-center gap-2 font-medium text-sky-300 hover:text-sky-200">
              <BookOpen size={16} /> See the sample datasets <ArrowRight size={14} />
            </Link>
          </div>
          <pre className="overflow-x-auto rounded-2xl border border-white/10 bg-[#060d18] p-6 text-[13px] leading-7 text-sky-100">
            <code>{`# score the bundled mock agent (no API key needed)
python examples/run_eval.py --agent mock

# evaluate a real model on the same rubrics
export OPENAI_API_KEY=sk-...
python examples/run_eval.py --agent openai --model gpt-5.6-terra

# browse what the agent was asked and how it was graded
python examples/run_eval.py --task wf-spa-deal-points --show-task`}</code>
          </pre>
        </div>
      </section>
    </main>
  );
}
