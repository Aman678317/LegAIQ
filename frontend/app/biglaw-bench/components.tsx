"use client";

import { useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  ArrowDownRight, ArrowUpRight, CheckCircle2, ChevronDown, Clock, FileText, MinusCircle, Search, X,
} from "lucide-react";
import { PARTS, TASKS, rubricTotals, type ExampleTask, type Part } from "./data";

/* ------------------------------------------------------------------ */
/* Part badge                                                          */
/* ------------------------------------------------------------------ */

const PART_STYLES: Record<Part, string> = {
  core: "border-sky-400/25 bg-sky-400/10 text-sky-300",
  workflows: "border-violet-400/25 bg-violet-400/10 text-violet-300",
  retrieval: "border-emerald-400/25 bg-emerald-400/10 text-emerald-300",
};

export function PartBadge({ part }: { part: Part }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-wide uppercase ${PART_STYLES[part]}`}>
      {PARTS[part].name}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Task explorer: filter + browse tasks and their rubrics              */
/* ------------------------------------------------------------------ */

const FILTERS: { key: Part | "all"; label: string }[] = [
  { key: "all", label: "All parts" },
  { key: "core", label: "Core" },
  { key: "workflows", label: "Workflows" },
  { key: "retrieval", label: "Retrieval" },
];

const KIND_QUERY: [string, RegExp][] = [
  ["drafting", /draft/i], ["research", /research/i], ["due diligence", /diligence/i],
  ["deal work", /deal|negotiation|spa/i], ["document retrieval", /retriev|corpus/i],
  ["risk & compliance", /risk|compliance/i], ["litigation analysis", /litigat|transcript|privilege|review/i],
];

export function TaskExplorer() {
  const [part, setPart] = useState<Part | "all">("all");
  const [query, setQuery] = useState("");
  const [openId, setOpenId] = useState<string | null>(TASKS[0]?.id ?? null);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return TASKS.filter((task) => {
      if (part !== "all" && task.part !== part) return false;
      if (!q) return true;
      return (
        task.title.toLowerCase().includes(q) ||
        task.category.toLowerCase().includes(q) ||
        task.summary.toLowerCase().includes(q) ||
        task.instructions.toLowerCase().includes(q)
      );
    });
  }, [part, query]);

  return (
    <div>
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-wrap gap-1.5">
          {FILTERS.map((filter) => (
            <button
              key={filter.key}
              type="button"
              onClick={() => setPart(filter.key)}
              className={`rounded-lg px-3.5 py-2 text-sm font-medium transition ${
                part === filter.key ? "bg-white text-slate-950" : "border border-white/10 text-slate-300 hover:bg-white/5"
              }`}
            >
              {filter.label}
            </button>
          ))}
        </div>
        <label className="relative">
          <Search size={15} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-slate-500" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search tasks, categories, instructions…"
            className="w-full rounded-lg border border-white/10 bg-white/[0.04] py-2 pr-8 pl-9 text-sm text-slate-100 placeholder:text-slate-500 focus:border-sky-400/50 focus:outline-none md:w-80"
          />
          {query && (
            <button type="button" onClick={() => setQuery("")} aria-label="Clear search" className="absolute top-1/2 right-2.5 -translate-y-1/2 text-slate-500 hover:text-slate-200">
              <X size={14} />
            </button>
          )}
        </label>
      </div>

      <p className="mt-4 text-xs text-slate-500">
        {visible.length} of {TASKS.length} sample tasks · click a task to read its instructions and full grading rubric
      </p>

      <div className="mt-6 space-y-3">
        {visible.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            open={openId === task.id}
            onToggle={() => setOpenId(openId === task.id ? null : task.id)}
          />
        ))}
        {visible.length === 0 && (
          <div className="rounded-xl border border-dashed border-white/15 p-10 text-center text-sm text-slate-400">
            No tasks match that filter.
          </div>
        )}
      </div>
    </div>
  );
}

function TaskCard({ task, open, onToggle }: { task: ExampleTask; open: boolean; onToggle: () => void }) {
  const totals = rubricTotals(task.rubric);
  const kinds = KIND_QUERY.filter(([, pattern]) => pattern.test(task.category + " " + task.title)).map(([label]) => label);

  return (
    <article className="overflow-hidden rounded-xl border border-white/10 bg-white/[0.025] transition hover:border-white/20">
      <button type="button" onClick={onToggle} aria-expanded={open} className="flex w-full items-start justify-between gap-4 p-5 text-left">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <PartBadge part={task.part} />
            <span className="text-xs text-slate-500">{task.category}</span>
            {kinds.slice(0, 2).map((kind) => (
              <span key={kind} className="rounded-full bg-white/5 px-2 py-0.5 text-[11px] text-slate-400">{kind}</span>
            ))}
          </div>
          <h3 className="mt-2.5 text-lg font-semibold tracking-tight">{task.title}</h3>
          {!open && <p className="mt-1.5 line-clamp-2 text-sm leading-relaxed text-slate-400">{task.summary}</p>}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2">
          <span className="flex items-center gap-1 text-xs text-slate-500"><Clock size={13} /> ~{task.minutes} min</span>
          <ChevronDown size={17} className={`text-slate-500 transition-transform ${open ? "rotate-180" : ""}`} />
        </div>
      </button>

      {open && (
        <div className="border-t border-white/10 p-5 pt-6">
          <div className="grid gap-6 lg:grid-cols-[1.35fr_1fr]">
            <div>
              <SectionLabel>Instructions</SectionLabel>
              <p className="mt-2 text-sm leading-relaxed text-slate-300">{task.instructions}</p>
              <SectionLabel className="mt-6">What the agent receives</SectionLabel>
              <ul className="mt-2 space-y-2">
                {task.inputs.map((input) => (
                  <li key={input.name} className="flex gap-2.5 text-sm">
                    <FileText size={15} className="mt-0.5 shrink-0 text-slate-500" />
                    <span>
                      <span className="font-mono text-[13px] text-slate-200">{input.name}</span>
                      <span className="text-slate-500"> — {input.kind}. {input.description}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-lg border border-white/10 bg-[#0b1728] p-4">
              <div className="flex items-baseline justify-between">
                <SectionLabel>Grading rubric</SectionLabel>
                <span className="text-[11px] text-slate-500">+{totals.positive} pts · −{totals.penalties} risk</span>
              </div>
              <p className="mt-1.5 text-[11px] leading-relaxed text-slate-500">
                Two dimensions, mirroring the real benchmark: Answer Quality (is the work right and complete?) and Source
                Reliability (is it grounded in verifiable citations?). Penalties subtract for errors and hallucinations.
              </p>
              <RubricList title="Answer Quality" items={task.rubric.answerQuality} />
              <RubricList title="Source Reliability" items={task.rubric.sourceReliability} />
            </div>
          </div>
        </div>
      )}
    </article>
  );
}

function RubricList({ title, items }: { title: string; items: ExampleTask["rubric"]["answerQuality"] }) {
  return (
    <div className="mt-4">
      <p className="text-[11px] font-semibold tracking-wider text-slate-400 uppercase">{title}</p>
      <ul className="mt-2 space-y-2">
        {items.map((item) => (
          <li key={item.id} className="flex items-start gap-2 text-[13px] leading-relaxed">
            {item.points >= 0 ? (
              <CheckCircle2 size={14} className="mt-0.5 shrink-0 text-emerald-400" />
            ) : (
              <MinusCircle size={14} className="mt-0.5 shrink-0 text-rose-400" />
            )}
            <span className="text-slate-300">{item.criterion}</span>
            <span className={`ml-auto shrink-0 font-mono text-xs ${item.points >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
              {item.points >= 0 ? `+${item.points}` : item.points}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SectionLabel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <p className={`text-[11px] font-semibold tracking-wider text-slate-400 uppercase ${className}`}>{children}</p>;
}

/* ------------------------------------------------------------------ */
/* Nav with active-route highlighting (needs the pathname)             */
/* ------------------------------------------------------------------ */

const NAV = [
  { href: "/biglaw-bench", label: "Overview" },
  { href: "/biglaw-bench/tasks", label: "Tasks & rubrics" },
  { href: "/biglaw-bench/datasets", label: "Sample datasets" },
  { href: "/biglaw-bench/scoring", label: "Scoring" },
];

export function NavLinks() {
  const pathname = usePathname();
  return (
    <>
      {NAV.map((item) => {
        const active = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`rounded-lg px-3 py-2 whitespace-nowrap transition hover:bg-white/5 hover:text-white ${
              active ? "bg-white/[0.07] font-semibold text-white" : "text-slate-400"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </>
  );
}

/* Scoring-math helpers reused on the scoring page. */

export function ScoreBar({ earned, possible }: { earned: number; possible: number }) {
  const pct = Math.max(0, Math.min(100, (earned / possible) * 100));
  return (
    <div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-white/10">
        <div className="h-full rounded-full bg-gradient-to-r from-sky-400 to-violet-400" style={{ width: `${pct}%` }} />
      </div>
      <div className="mt-2 flex justify-between text-xs text-slate-400">
        <span className="font-mono">{earned.toFixed(1)} / {possible} pts</span>
        <span className="font-mono">{pct.toFixed(1)}% of lawyer-quality work product</span>
      </div>
    </div>
  );
}

export function PointArrows({ points }: { points: number }) {
  return points >= 0 ? (
    <span className="inline-flex items-center gap-0.5 font-mono text-emerald-300"><ArrowUpRight size={13} />+{points}</span>
  ) : (
    <span className="inline-flex items-center gap-0.5 font-mono text-rose-300"><ArrowDownRight size={13} />{points}</span>
  );
}
