import type { Metadata } from "next";
import { TaskExplorer } from "../components";

export const metadata: Metadata = {
  title: "Tasks & rubrics — BigLaw Bench Explorer",
  description:
    "Browse example legal AI benchmark tasks with their instructions, inputs, and grading rubrics across Core, Workflows, and Retrieval.",
};

export default function TasksPage() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-16">
      <p className="text-sm font-semibold tracking-[0.18em] text-sky-300 uppercase">Task explorer</p>
      <h1 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight md:text-4xl">
        Open a task. Read the assignment. See exactly what earns credit.
      </h1>
      <p className="mt-4 max-w-2xl leading-relaxed text-slate-400">
        Every task shows the instructions an agent receives, the source pack it works from, and the full rubric used to
        grade the answer — separated into Answer Quality and Source Reliability, with penalties for errors and
        hallucinated citations. Filter by benchmark part, or search for the kind of legal work you care about.
      </p>
      <div className="mt-10">
        <TaskExplorer />
      </div>
    </main>
  );
}
