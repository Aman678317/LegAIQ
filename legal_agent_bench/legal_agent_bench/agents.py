"""Agent runners. An agent is a callable ``(Task) -> AgentOutput``.

Bundled agents:
  * ``mock``    — deterministic, deliberately imperfect canned answers. Use it to
                  smoke-test the harness and see partial credit without an API key.
  * ``keyword`` — a naive extractive baseline: returns document lines that match
                  instruction keywords. A meaningful floor for comparisons.
  * ``openai``  — calls a real model through the OpenAI Responses API
                  (requires ``openai`` package and ``OPENAI_API_KEY``).

To add your own agent, write a callable and register it in ``AGENTS``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from .core import Task

DEFAULT_MODEL = "gpt-5.6-terra"  # balanced GPT-5.6 tier; see https://developers.openai.com/api/docs/models

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "your", "you", "are", "any",
    "all", "each", "list", "must", "should", "will", "which", "into", "have", "has",
    "what", "when", "where", "who", "how", "does", "not", "may", "can", "its", "their",
}


@dataclass
class AgentOutput:
    text: str
    model: str = ""
    params: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Mock agent — canned, plausible-but-imperfect answers for the bundled tasks.
# It hits the easy rubric items and misses the subtle ones on purpose, so the
# harness can be exercised (and partial credit seen) with zero API calls.
# --------------------------------------------------------------------------- #

MOCK_RESPONSES: dict[str, str] = {
    "nda-review-001": """\
# NDA Review — Northwind Robotics / Vantage Analytics

**Reviewed:** Mutual Non-Disclosure Agreement (draft v2)

**Red flags identified:**

1. **Term (Section 3):** The confidentiality obligations run for **ten (10) years** after \
disclosure. That is far beyond the 2–5 year market standard for a commercial mutual NDA and \
locks both parties out of using general knowledge for a decade. Recommend reducing to 3 years \
for general business information (trade secrets may run longer).

2. **Non-solicitation (Section 9):** A 3-year non-solicit with no carve-out for employees who \
respond to general solicitations or are recruited independently. Recommend adding a general-\
solicitation carve-out.

3. **Indemnification (Section 7):** Receiving Party indemnifies Disclosing Party for breach, \
including lost profits, with no cap. Recommend deleting the indemnity or capping it.

**Recommendation:** Do not sign as drafted; the above items need negotiation.
""",
    "data-room-dd-001": """\
# Project Lighthouse — Data Room Summary

**Answers:**

1. CFO base salary: **$285,000** per year (employment agreement).
2. Fully diluted share count: **1,700,000** shares (cap table).
3. HQ base rent: **$42,000 per month** with 3% annual escalation (lease abstract).
4. HQ lease renewal: one 5-year option, written notice **9 months** before expiry.
5. Ferris Cartage acquisition price approved by the board: **$4.2 million**.
6. General liability insurance: $2M per occurrence / $4M aggregate.
7. Net working capital peg: **$1.5 million** with a 90-day true-up.

**Open questions:** Request an updated insurance certificate and confirmation on whether \
any employment agreements remain unexecuted.
""",
    "lease-abstraction-001": """\
# Lease Abstraction — 88 Beacon Street, Suite 400

| Field | Value |
|---|---|
| Premises | Suite 400, approx. 12,400 rentable square feet |
| Term | 84 months, commencing October 1, 2026 |
| Base rent (Year 1) | $6,850 per month |
| Escalation | 3% annually |
| Security deposit | $40,000 |
| Renewal option | One 5-year option; notice no earlier than 15 months and no later than 9 months before expiration |
| Holdover | 150% of base rent |
| Permitted use | General office use |

Prepared from the lease dated August 12, 2026.
""",
    "msa-playbook-001": """\
# MSA Deviation Review — Kestrel Systems / Draco Cloud

| Clause | Proposed | Severity | Recommended counter |
|---|---|---|---|
| Liability cap | 12 months of fees | High | Raise to 2x annual fees, floor $500,000 |
| Auto-renewal | 3-year term auto-renews unless we opt out 90 days prior | High | Replace with affirmative renewal on mutual agreement |
| Payment terms | Net 90 | Medium | Net 30 per playbook |
| IP indemnity | Capped at 12 months of fees | High | IP infringement indemnity should be uncapped (or excluded from the cap) |
| Data breach notice | 10 business days | Medium | 48 hours per playbook |
""",
}

FALLBACK_TEMPLATE = """\
# Response — {task_name}

I reviewed the attached documents ({doc_list}) against the instructions.

**Summary of key points from the documents:**

{snippets}

**Note:** This is a generic mock response for tasks without a scripted answer; \
it is not a substantive work product.
"""


def mock_agent(task: Task) -> AgentOutput:
    canned = MOCK_RESPONSES.get(task.id)
    if canned:
        return AgentOutput(text=canned, model="mock")
    docs = task.read_documents()
    snippets = "\n\n".join(
        f"*From {doc.file}:* {text.splitlines()[0][:200]}..." if text.strip() else f"*{doc.file}: (empty)*"
        for doc, text in docs
    ) or "(no documents attached)"
    return AgentOutput(
        text=FALLBACK_TEMPLATE.format(
            task_name=task.name,
            doc_list=", ".join(doc.file for doc, _ in docs) or "none",
            snippets=snippets,
        ),
        model="mock",
    )


# --------------------------------------------------------------------------- #
# Keyword agent — naive extractive baseline. Pulls document lines that share
# keywords with the instructions. Deterministic, no LLM, deliberately weak.
# --------------------------------------------------------------------------- #

def keyword_agent(task: Task) -> AgentOutput:
    keywords = {
        word for word in re.findall(r"[a-zA-Z]{4,}", task.instructions.casefold())
        if word not in STOPWORDS
    }
    selected: list[str] = [f"# Extracted excerpts — {task.name}", ""]
    for doc, text in task.read_documents():
        hits = []
        for line in text.splitlines():
            if not line.strip():
                continue
            line_words = {w for w in re.findall(r"[a-zA-Z]{4,}", line.casefold())}
            # A line must share at least two distinct instruction keywords to be
            # pulled in — this keeps the baseline naive and the floor low.
            if len(line_words & keywords) >= 2:
                hits.append(line.strip())
        if hits:
            selected.append(f"## {doc.file}")
            selected.extend(hits[:8])
            selected.append("")
    if len(selected) == 2:
        selected.append("(No document lines matched instruction keywords.)")
    return AgentOutput(text="\n".join(selected), model="keyword-extractive")


# --------------------------------------------------------------------------- #
# OpenAI agent — a real model doing the task in one shot, no tools.
# --------------------------------------------------------------------------- #

SYSTEM_PROMPT = (
    "You are a senior associate at a law firm producing a first-draft work product. "
    "Follow the assignment instructions exactly: use only the provided documents, "
    "cite section or document references where the instructions ask for them, and "
    "do not invent facts. Format the answer in clean markdown."
)


def build_task_prompt(task: Task) -> str:
    parts = [f"# Assignment: {task.name}", "", task.instructions.strip(), "", "## Source documents", ""]
    for doc, text in task.read_documents():
        parts.append(f"### {doc.file}" + (f" — {doc.role}" if doc.role else ""))
        parts.append("")
        parts.append(text.strip())
        parts.append("")
    parts.append("## Your response")
    return "\n".join(parts)


def make_openai_agent(model: str = DEFAULT_MODEL, reasoning: str = "medium") -> Callable[[Task], AgentOutput]:
    """Build an OpenAI-backed agent. Import happens lazily so the benchmark's
    core (mock agents, checks, reports) works without the openai package."""
    def _agent(task: Task) -> AgentOutput:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The 'openai' package is required: pip install 'legal-agent-bench[openai]'") from exc
        client = OpenAI(timeout=600)
        response = client.responses.create(
            model=model,
            instructions=SYSTEM_PROMPT,
            input=build_task_prompt(task),
            reasoning={"effort": reasoning},
        )
        return AgentOutput(text=response.output_text or "", model=model, params={"reasoning": reasoning})

    return _agent


AGENTS: dict[str, Callable[[Task], AgentOutput]] = {
    "mock": mock_agent,
    "keyword": keyword_agent,
}


def resolve_agent(name: str, model: str | None = None, reasoning: str = "medium") -> Callable[[Task], AgentOutput]:
    if name == "openai":
        return make_openai_agent(model or DEFAULT_MODEL, reasoning=reasoning)
    if name in AGENTS:
        return AGENTS[name]
    known = ", ".join(["mock", "keyword", "openai"])
    raise ValueError(f"Unknown agent {name!r}. Known agents: {known}")
