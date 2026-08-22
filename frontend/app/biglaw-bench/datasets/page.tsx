import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Database, ExternalLink, FileJson, FileText, FolderTree } from "lucide-react";
import { PARTS, type Part } from "../data";
import { PartBadge } from "../components";

export const metadata: Metadata = {
  title: "Sample datasets — BigLaw Bench Explorer",
  description:
    "Sample datasets for exploring legal AI benchmark tasks: JSONL task definitions, rubrics, source documents, and pointers to the official BigLaw Bench data.",
};

const SAMPLE_PACKS: {
  part: Part;
  folder: string;
  contents: { name: string; description: string }[];
}[] = [
  {
    part: "core",
    folder: "examples/tasks/",
    contents: [
      { name: "core-drafting-indemnity.json", description: "Drafting task: mutual, capped indemnity redline with playbook rationale." },
      { name: "core-research-limitations.json", description: "Legal research task: UCC § 2-725 limitations memo with authority table." },
      { name: "core-transcript-impeachment.json", description: "Litigation task: impeachment points with page:line citations." },
    ],
  },
  {
    part: "workflows",
    folder: "examples/tasks/",
    contents: [
      { name: "wf-spa-deal-points.json", description: "Composite task: extract every negotiated deal point from a Share Purchase Agreement." },
    ],
  },
  {
    part: "retrieval",
    folder: "examples/tasks/",
    contents: [
      { name: "ret-contracts-defined-terms.json", description: "Corpus task: resolve defined-term cross-references and cite passages." },
      { name: "ret-discovery-emails.json", description: "Corpus task: retrieve a responsive email thread with metadata intact." },
    ],
  },
];

export default function DatasetsPage() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-16">
      <p className="text-sm font-semibold tracking-[0.18em] text-emerald-300 uppercase">Sample datasets</p>
      <h1 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight md:text-4xl">
        Small on purpose: every file is readable in one sitting.
      </h1>
      <p className="mt-4 max-w-2xl leading-relaxed text-slate-400">
        The sample pack mirrors the shape of the official benchmark — one JSON file per task with instructions, inputs,
        and the complete rubric — so you can learn the format, extend it with your own tasks, and score agents against
        it locally. The full official datasets live in the{" "}
        <a className="text-slate-200 underline decoration-slate-600 hover:text-white" href="https://github.com/harveyai/biglaw-bench" target="_blank" rel="noreferrer">
          harveyai/biglaw-bench
        </a>{" "}
        repository under <code className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[13px]">blb-core</code>,{" "}
        <code className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[13px]">blb-workflows</code>, and{" "}
        <code className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[13px]">blb-retrieval</code>.
      </p>

      <div className="mt-10 space-y-5">
        {SAMPLE_PACKS.map((pack) => (
          <section key={pack.part} className="rounded-2xl border border-white/10 bg-white/[0.025] p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <PartBadge part={pack.part} />
                <h2 className="text-xl font-semibold">{PARTS[pack.part].name} samples</h2>
              </div>
              <Link href={`/biglaw-bench/tasks?part=${pack.part}`} className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-300 hover:text-white">
                Browse in the explorer <ArrowRight size={14} />
              </Link>
            </div>
            <p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-400">{PARTS[pack.part].description}</p>
            <div className="mt-5 overflow-hidden rounded-lg border border-white/10">
              <div className="flex items-center gap-2 border-b border-white/10 bg-[#060d18] px-4 py-2.5 text-xs text-slate-400">
                <FolderTree size={13} /> <span className="font-mono">{pack.folder}</span>
              </div>
              <ul className="divide-y divide-white/5">
                {pack.contents.map((file) => (
                  <li key={file.name} className="flex items-start gap-3 px-4 py-3">
                    <FileJson size={15} className="mt-0.5 shrink-0 text-sky-300" />
                    <div>
                      <p className="font-mono text-[13px] text-slate-200">{file.name}</p>
                      <p className="mt-0.5 text-xs leading-relaxed text-slate-500">{file.description}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        ))}
      </div>

      <section className="mt-10 grid gap-5 md:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-[#0b1728] p-6">
          <div className="flex items-center gap-3 text-sky-300"><Database size={18} /><span className="text-sm font-semibold">What a task file contains</span></div>
          <ul className="mt-4 space-y-2.5 text-sm text-slate-300">
            <li className="flex gap-2"><FileText size={15} className="mt-0.5 shrink-0 text-slate-500" /><span><span className="font-mono text-[13px]">instructions</span> — the assignment, written like a memo to an associate.</span></li>
            <li className="flex gap-2"><FileText size={15} className="mt-0.5 shrink-0 text-slate-500" /><span><span className="font-mono text-[13px]">inputs</span> — the source pack: agreements, facts memos, corpora descriptors.</span></li>
            <li className="flex gap-2"><FileText size={15} className="mt-0.5 shrink-0 text-slate-500" /><span><span className="font-mono text-[13px]">rubric</span> — Answer Quality and Source Reliability items with +points for credit and −points for errors.</span></li>
            <li className="flex gap-2"><FileText size={15} className="mt-0.5 shrink-0 text-slate-500" /><span><span className="font-mono text-[13px]">checks</span> — programmatic matchers the bundled runner uses to score answers deterministically.</span></li>
          </ul>
        </div>
        <div className="rounded-2xl border border-white/10 bg-[#0b1728] p-6">
          <div className="flex items-center gap-3 text-violet-300"><ExternalLink size={18} /><span className="text-sm font-semibold">The official data</span></div>
          <p className="mt-4 text-sm leading-relaxed text-slate-400">
            The official benchmark publishes task and rubric samples in its repository, organized by part. Access to
            the full datasets and additional resources is available by contacting Harvey directly. This explorer is a
            companion, not a mirror: everything here is fictional and safe to fork.
          </p>
          <a href="https://github.com/harveyai/biglaw-bench" target="_blank" rel="noreferrer" className="mt-5 inline-flex items-center gap-2 rounded-lg border border-white/15 px-4 py-2 text-sm font-medium hover:bg-white/5">
            Visit harveyai/biglaw-bench <ArrowRight size={14} />
          </a>
        </div>
      </section>
    </main>
  );
}
