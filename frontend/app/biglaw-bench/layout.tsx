import type { Metadata } from "next";
import Link from "next/link";
import { Scale } from "lucide-react";
import { NavLinks } from "./components";

export const metadata: Metadata = {
  title: "BigLaw Bench Explorer — understand and run the legal AI benchmark",
  description:
    "An open explorer for BigLaw Bench: browse example tasks and grading rubrics across Core, Workflows, and Retrieval, see sample datasets, and learn how scoring works.",
};

export default function BigLawBenchLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="blb min-h-screen bg-[#08111f] text-slate-100">
      <header className="sticky top-0 z-30 border-b border-white/10 bg-[#08111f]/85 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-6">
          <Link href="/biglaw-bench" className="flex shrink-0 items-center gap-2.5 font-semibold tracking-tight">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-sky-400 to-violet-500">
              <Scale size={17} />
            </span>
            BigLaw <span className="text-sky-300">Bench</span>
          </Link>
          <nav className="flex gap-1 overflow-x-auto text-sm md:gap-2" aria-label="BigLaw Bench sections">
            <NavLinks />
          </nav>
          <a
            href="https://github.com/harveyai/biglaw-bench"
            target="_blank"
            rel="noreferrer"
            className="hidden shrink-0 rounded-lg bg-white px-3.5 py-2 text-sm font-medium text-slate-950 transition hover:bg-slate-200 sm:block"
          >
            Official repo
          </a>
        </div>
      </header>

      {children}

      <footer className="border-t border-white/10 px-6 py-10">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 text-xs leading-relaxed text-slate-500 md:flex-row md:items-center md:justify-between">
          <p>
            BigLaw Bench is a Harvey initiative — see the official{" "}
            <a className="text-slate-300 underline decoration-slate-600 hover:text-white" href="https://github.com/harveyai/biglaw-bench" target="_blank" rel="noreferrer">
              harveyai/biglaw-bench
            </a>{" "}
            repository.
          </p>
          <p>This explorer ships fictional sample tasks for learning and scaffolding. It is not affiliated with, nor an official distribution of, the benchmark.</p>
        </div>
      </footer>
    </div>
  );
}
