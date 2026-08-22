import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Calculator, Scale, ShieldAlert, ShieldCheck } from "lucide-react";
import { taskById } from "../data";
import { PointArrows, ScoreBar } from "../components";

export const metadata: Metadata = {
  title: "How scoring works — BigLaw Bench Explorer",
  description:
    "How BigLaw Bench-style scoring works: two-dimension rubrics, positive credit minus penalties, and a score expressed as percent of lawyer-quality work product.",
};

const WORKED_TASK_ID = "core-research-limitations";

/* A plausible partial-credit run of the worked task, used in the arithmetic below. */
const WORKED: { earned: number; items: string[] } = {
  earned: 11,
  items: ["AQ1", "AQ2", "AQ4", "SR1"],
};

export default function ScoringPage() {
  const task = taskById(WORKED_TASK_ID)!;
  const allItems = [...task.rubric.answerQuality, ...task.rubric.sourceReliability];
  const positive = allItems.filter((i) => i.points > 0).reduce((sum, i) => sum + i.points, 0);
  const missed = allItems.filter((i) => i.points > 0 && !WORKED.items.includes(i.id));
  const missedPoints = missed.reduce((sum, i) => sum + i.points, 0);
  const netPercent = (WORKED.earned / positive) * 100;

  return (
    <main className="mx-auto max-w-6xl px-6 py-16">
      <p className="text-sm font-semibold tracking-[0.18em] text-violet-300 uppercase">Scoring</p>
      <h1 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight md:text-4xl">
        A score you can audit line by line.
      </h1>
      <p className="mt-4 max-w-2xl leading-relaxed text-slate-400">
        BigLaw Bench grades every task against a custom rubric with two dimensions, and reports the result as the
        percentage of a lawyer-quality work product the model actually completed. Nothing is averaged away: each rubric
        line records its own evidence, so you can see not just <em>how much</em> was earned, but <em>what</em>.
      </p>

      {/* Two dimensions */}
      <section className="mt-12 grid gap-5 md:grid-cols-2">
        <div className="rounded-2xl border border-sky-400/25 bg-sky-400/5 p-6">
          <div className="flex items-center gap-3 text-sky-300"><Scale size={18} /><span className="text-sm font-semibold">Answer Quality</span></div>
          <p className="mt-3 text-sm leading-relaxed text-slate-300">
            Is the work right and complete? Criteria track the substantive requirements of the assignment — the issues
            found, the clauses changed, the rules applied — and award positive points for each one met.
          </p>
          <ul className="mt-4 space-y-1.5 text-xs text-slate-400">
            <li>· Completeness — were all required elements produced?</li>
            <li>· Accuracy — is each element substantively correct?</li>
            <li>· Appropriateness — is it usable as legal work product?</li>
          </ul>
        </div>
        <div className="rounded-2xl border border-emerald-400/25 bg-emerald-400/5 p-6">
          <div className="flex items-center gap-3 text-emerald-300"><ShieldCheck size={18} /><span className="text-sm font-semibold">Source Reliability</span></div>
          <p className="mt-3 text-sm leading-relaxed text-slate-300">
            Is the work grounded? Citations must be verifiable and actually support the propositions they are attached
            to. Unsupported assertions lose points; fabricated citations lose badly.
          </p>
          <ul className="mt-4 space-y-1.5 text-xs text-slate-400">
            <li>· Verifiable — can a checker locate every cited source?</li>
            <li>· Correctly cited — does the source say what is claimed?</li>
            <li>· Penalties — hallucinated authorities or misquotes subtract.</li>
          </ul>
        </div>
      </section>

      {/* The arithmetic */}
      <section className="mt-14">
        <div className="flex items-center gap-3 text-violet-300"><Calculator size={18} /><span className="text-sm font-semibold tracking-[0.18em] uppercase">The arithmetic</span></div>
        <h2 className="mt-4 text-2xl font-semibold tracking-tight md:text-3xl">Positive credit, minus penalties, over the task total.</h2>
        <div className="mt-6 overflow-x-auto rounded-2xl border border-white/10 bg-[#0b1728]">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-white/10 text-xs text-slate-400 uppercase">
                <th className="px-5 py-3 font-semibold">Rule</th>
                <th className="px-5 py-3 font-semibold">Criterion</th>
                <th className="px-5 py-3 font-semibold">Points</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {allItems.map((item) => {
                const earned = WORKED.items.includes(item.id);
                const missedPositive = item.points > 0 && !earned;
                return (
                  <tr key={item.id} className={missedPositive ? "opacity-45" : ""}>
                    <td className="px-5 py-3 font-mono text-xs text-slate-500">{item.id}</td>
                    <td className="px-5 py-3 text-slate-300">
                      {item.criterion}
                      {missedPositive && <span className="ml-2 rounded bg-white/10 px-1.5 py-0.5 text-[10px] text-slate-400">not earned</span>}
                    </td>
                    <td className="px-5 py-3">
                      <span className={item.points >= 0 ? "text-emerald-300" : "text-rose-300"}>
                        {item.points >= 0 ? `+${item.points}` : item.points}
                      </span>
                      {earned && item.points > 0 && <span className="ml-2 text-[11px] text-emerald-400">✓ earned</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-6 grid gap-5 lg:grid-cols-[1fr_1fr]">
          <div className="space-y-3 rounded-2xl border border-white/10 bg-white/[0.025] p-6 text-sm">
            <p className="text-[11px] font-semibold tracking-wider text-slate-400 uppercase">Worked example — {task.title}</p>
            <div className="flex justify-between text-slate-300"><span>Rubric credit available</span><span className="font-mono">{positive} pts</span></div>
            <div className="flex justify-between text-emerald-300"><span>Earned ({WORKED.items.length} criteria met)</span><span className="font-mono">+{WORKED.earned}</span></div>
            <div className="flex justify-between text-slate-500"><span>Unearned ({missed.length} criteria missed)</span><span className="font-mono">−{missedPoints} (no penalty — just unearned)</span></div>
            <div className="flex justify-between text-rose-300"><span>Penalties incurred (hallucination, misquote)</span><span className="font-mono">0</span></div>
            <div className="border-t border-white/10 pt-3">
              <ScoreBar earned={WORKED.earned} possible={positive} />
              <p className="mt-3 text-xs leading-relaxed text-slate-500">
                The model earned {WORKED.earned} of {positive} available points: {netPercent.toFixed(1)}% of a
                lawyer-quality work product on this task. Had it also fabricated an authority (SR3, −4), its net would
                have dropped to {(((WORKED.earned - 4) / positive) * 100).toFixed(1)}% — penalties bite.
              </p>
            </div>
          </div>
          <div className="space-y-4">
            <div className="rounded-2xl border border-white/10 p-6">
              <div className="flex items-center gap-2.5 text-rose-300"><ShieldAlert size={16} /><span className="text-sm font-semibold">Why penalties, not just unearned credit?</span></div>
              <p className="mt-2.5 text-sm leading-relaxed text-slate-400">
                A wrong answer is worse than a missing one: a hallucinated citation or an invented deal term creates
                real-world risk. Negative points let a benchmark distinguish “didn’t finish the work” from “finished it
                incorrectly” — the same distinction a supervising partner would make.
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 p-6">
              <div className="flex items-center gap-2.5 text-sky-300"><PointArrows points={1} /><span className="text-sm font-semibold">Reading a benchmark score</span></div>
              <p className="mt-2.5 text-sm leading-relaxed text-slate-400">
                Scores aggregate per task and per category, so you can see where a model is strong (e.g., extraction)
                and where it fails (e.g., grounded citation). The bundled runner prints this per-rubric-line breakdown
                for every task it scores.
              </p>
              <Link href="/biglaw-bench/tasks" className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-sky-300 hover:text-sky-200">
                See full rubrics on real tasks <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Runner output */}
      <section className="mt-14">
        <h2 className="text-2xl font-semibold tracking-tight">The same math, as the runner reports it</h2>
        <pre className="mt-5 overflow-x-auto rounded-2xl border border-white/10 bg-[#060d18] p-6 text-[13px] leading-7 text-slate-200">
          <code>{`$ python examples/run_eval.py --task ${WORKED_TASK_ID} --agent mock

${task.title}  [core / ${task.category}]
  AQ1  ✓  States the four-year limitation period and its statutory source   +3
  AQ2  ✓  Applies the discovery-of-breach accrual rule to the timeline     +3
  AQ3  ✗  Notes the contractual-reduction boundary (cannot go below one year)
  AQ4  ✓  Concludes clearly on viability with the decisive fact identified  +2
  AQ5  ✗  Relies on a rule not supported by any cited authority
  SR1  ✓  Authority table present with citation, rule, and use              +3
  SR2  ✗  Citations are verifiable and matched to propositions
  SR3  —  No fabricated authority detected (−4 if present)

  score: 11 / 14 available → 78.6% of lawyer-quality work product`}</code>
        </pre>
      </section>
    </main>
  );
}
