/**
 * BigLaw Bench explorer — task catalog.
 *
 * These are fictional, self-contained sample tasks that mirror the shape of
 * the real BigLaw Bench (github.com/harveyai/biglaw-bench): its three parts
 * (Core, Workflows, Retrieval), its practice-area categories, and its
 * two-dimension rubric style (Answer Quality + Source Reliability, positive
 * credit minus penalties). They are illustrative examples, not official data.
 */

export type Part = "core" | "workflows" | "retrieval";
export type Track = "transactional" | "litigation" | "agentic" | "corpus";

export type RubricItem = {
  id: string;
  criterion: string;
  /** Positive points = credit earned; negative = penalty for errors. */
  points: number;
};

export type Rubric = {
  answerQuality: RubricItem[];
  sourceReliability: RubricItem[];
};

export type ExampleTask = {
  id: string;
  title: string;
  part: Part;
  track: Track;
  /** Mirrors the real benchmark's task categories. */
  category: string;
  minutes: number;
  summary: string;
  instructions: string;
  inputs: { name: string; kind: string; description: string }[];
  rubric: Rubric;
};

export const PARTS: Record<Part, { name: string; tagline: string; description: string }> = {
  core: {
    name: "Core",
    tagline: "Foundational legal problem-solving",
    description:
      "Focused, single-pass assignments across 16 transactional and litigation categories — from drafting and due diligence to transcript analysis. Core answers a basic question: given legal material and an instruction, what fraction of a lawyer-quality first draft does the model produce?",
  },
  workflows: {
    name: "Workflows",
    tagline: "Composite, agentic legal work",
    description:
      "Multi-step assignments that mirror how work actually moves through a deal or a matter — read a long agreement, follow cross-references, keep instructions in view, and hand back a decision-ready work product. The flagship workflow is SPA Deal Points: extracting every negotiated deal point from a Share Purchase Agreement.",
  },
  retrieval: {
    name: "Retrieval",
    tagline: "Finding the right source first",
    description:
      "End-to-end retrieval over realistic corpora: long contracts with dense defined terms and cross-references (Merger Agreements, SPAs) and high-volume short documents with threading and metadata (Discovery Emails). A system that cannot surface the right passage cannot be trusted to reason over it.",
  },
};

export const WORK_KINDS = [
  "Drafting",
  "Legal research",
  "Due diligence",
  "Deal work",
  "Document retrieval",
  "Risk & compliance",
  "Litigation analysis",
] as const;

export const TASKS: ExampleTask[] = [
  {
    id: "core-drafting-indemnity",
    title: "Redline an indemnification clause",
    part: "core",
    track: "transactional",
    category: "Drafting",
    minutes: 25,
    summary:
      "Convert a one-sided indemnity into a mutual, capped clause with standard carve-outs — as a marked-up redline with a short rationale per change.",
    instructions:
      "You are counsel to the buyer (Kestrel Systems) in a software acquisition. The target's form SPA contains a one-way indemnification clause with no cap. Produce (1) a redline of the clause making the indemnity mutual, adding a basket and a cap at 15% of purchase price, and carving out fraud, IP infringement, and breach of confidentiality obligations from the cap, and (2) a one-sentence negotiation rationale for each change.",
    inputs: [
      { name: "spa-excerpt.pdf", kind: "Agreement excerpt", description: "Section 9 (Indemnification) of the target's form SPA, 3 pages." },
      { name: "buyer-positions.md", kind: "Playbook", description: "Kestrel's approved indemnity positions and fallbacks." },
    ],
    rubric: {
      answerQuality: [
        { id: "AQ1", criterion: "Makes the indemnity expressly mutual (both buyer and target indemnifying parties defined)", points: 2 },
        { id: "AQ2", criterion: "Adds a damages cap set at a percentage of the purchase price (15% per playbook)", points: 2 },
        { id: "AQ3", criterion: "Carves out fraud, IP infringement, and confidentiality breaches from the cap", points: 3 },
        { id: "AQ4", criterion: "Adds a deductible/basket before indemnity claims are payable", points: 1 },
        { id: "AQ5", criterion: "Provides a one-sentence rationale tied to the playbook for each edit", points: 2 },
        { id: "AQ6", criterion: "Invents obligations that appear in neither the excerpt nor the playbook", points: -3 },
      ],
      sourceReliability: [
        { id: "SR1", criterion: "Each redline element is anchored to a quoted phrase from the source clause or playbook", points: 2 },
        { id: "SR2", criterion: "Cites section/paragraph references for every quoted phrase", points: 1 },
        { id: "SR3", criterion: "Fabricates a quote that does not exist in the source documents", points: -3 },
      ],
    },
  },
  {
    id: "core-dd-change-of-control",
    title: "Sweep a credit agreement for change-of-control triggers",
    part: "core",
    track: "transactional",
    category: "Due Diligence",
    minutes: 30,
    summary:
      "Find every provision in a credit agreement that a proposed acquisition could trip — defaults, prepayments, consents — and state the cure for each.",
    instructions:
      "Your client (the acquirer, Coral Gate Capital) plans to buy 100% of BlueHarbor Logistics, which is borrower under the attached credit agreement. Identify every provision that the acquisition could trigger, including: events of default keyed to change of control, mandatory prepayment, consent requirements, and reporting obligations that change at closing. For each: quote the operative language, state whether the acquisition triggers it, and what the cure is (consent, repayment, notice).",
    inputs: [
      { name: "credit-agreement.pdf", kind: "Agreement", description: "BlueHarbor revolving credit agreement, 46 pages." },
      { name: "transaction-summary.md", kind: "Deal facts", description: "Structure of the proposed acquisition (stock purchase, new money at closing)." },
    ],
    rubric: {
      answerQuality: [
        { id: "AQ1", criterion: "Identifies the change-of-control event of default with the operative definition", points: 3 },
        { id: "AQ2", criterion: "Identifies mandatory prepayment obligations triggered by the transaction", points: 2 },
        { id: "AQ3", criterion: "Flags consent/notice requirements beyond the default itself", points: 2 },
        { id: "AQ4", criterion: "States a concrete cure path for each flagged provision", points: 2 },
        { id: "AQ5", criterion: "Misses a provision that the transaction summary plainly triggers", points: -3 },
      ],
      sourceReliability: [
        { id: "SR1", criterion: "Every flagged provision carries a section reference", points: 2 },
        { id: "SR2", criterion: "Quotes match the agreement text verbatim", points: 2 },
        { id: "SR3", criterion: "Attributes a quote to the wrong section", points: -2 },
      ],
    },
  },
  {
    id: "core-research-limitations",
    title: "Limitation-period research memo",
    part: "core",
    track: "transactional",
    category: "Legal Research",
    minutes: 35,
    summary:
      "Answer a limitations question with an authority table: statute, elements, exceptions, and how the facts apply — no loose ends.",
    instructions:
      "The client discovered a defective shipment delivered 2 years and 10 months ago and wants to know if a breach-of-contract claim is still viable. Draft a short research memo (≤600 words) with an authority table: for each authority, give the citation, the rule it states, and the part of the analysis it supports. Address the accrual rule, any discovery-of-breach exception, and tolling facts that could change the answer.",
    inputs: [
      { name: "facts-memo.pdf", kind: "Facts", description: "Client memo: delivery dates, inspection history, discovery timeline." },
      { name: "jurisdiction-note.md", kind: "Scope note", description: "Governing law is the UCC as enacted in the forum state; treat § 2-725 as controlling." },
    ],
    rubric: {
      answerQuality: [
        { id: "AQ1", criterion: "States the four-year limitation period and its statutory source (UCC § 2-725)", points: 3 },
        { id: "AQ2", criterion: "Applies the discovery-of-breach accrual rule to the timeline", points: 3 },
        { id: "AQ3", criterion: "Notes the contractual-reduction boundary (cannot go below one year)", points: 1 },
        { id: "AQ4", criterion: "Concludes clearly on viability with the decisive fact identified", points: 2 },
        { id: "AQ5", criterion: "Relies on a rule not supported by any cited authority", points: -3 },
      ],
      sourceReliability: [
        { id: "SR1", criterion: "Authority table present with citation, rule, and use-in-analysis for each entry", points: 3 },
        { id: "SR2", criterion: "Citations are verifiable and matched to the propositions they support", points: 2 },
        { id: "SR3", criterion: "Cites an authority that does not exist or does not say what is claimed", points: -4 },
      ],
    },
  },
  {
    id: "core-negotiation-msa",
    title: "Counter-offer strategy for an off-market MSA",
    part: "core",
    track: "transactional",
    category: "Negotiation Strategy",
    minutes: 25,
    summary:
      "Rank a vendor MSA's deviations from the client playbook, propose a first counter for each, and flag which items to hold firm on.",
    instructions:
      "You are outside counsel to the customer (Kestrel Systems). The vendor's proposed MSA deviates from Kestrel's playbook in several places. Produce a negotiation table: for each deviation — Term, Playbook position, Proposed terms, Severity (High/Medium/Low), Recommended counter — then a short note on which two items to hold firm on and why.",
    inputs: [
      { name: "proposed-msa.pdf", kind: "Agreement", description: "Vendor's draft master subscription agreement." },
      { name: "negotiation-playbook.md", kind: "Playbook", description: "Approved positions, fallbacks, and walk-away lines." },
    ],
    rubric: {
      answerQuality: [
        { id: "AQ1", criterion: "Identifies the liability-cap deviation and counters toward playbook (2x fees / $500k floor)", points: 2 },
        { id: "AQ2", criterion: "Flags evergreen auto-renewal and proposes affirmative renewal", points: 2 },
        { id: "AQ3", criterion: "Flags payment-terms and breach-notice gaps", points: 2 },
        { id: "AQ4", criterion: "Severity ratings follow the playbook's High criteria consistently", points: 2 },
        { id: "AQ5", criterion: "Lists a term as a deviation when the MSA already meets the playbook", points: -2 },
      ],
      sourceReliability: [
        { id: "SR1", criterion: "Each row cites the MSA section and playbook item it relies on", points: 2 },
        { id: "SR2", criterion: "Misstates the playbook position for a flagged term", points: -2 },
      ],
    },
  },
  {
    id: "core-transcript-impeachment",
    title: "Impeachment points from a deposition excerpt",
    part: "core",
    track: "litigation",
    category: "Transcript Analysis",
    minutes: 20,
    summary:
      "Read a depo excerpt against prior sworn statements and draft usable impeachment — page-line cites, contradiction, and the question to ask.",
    instructions:
      "You are second chair in a wage-and-hour class action. Compare the witness's deposition testimony against their prior declarations and payroll records. For each contradiction: cite the deposition page:line and the conflicting prior statement, quote both, and draft the impeachment question you would ask at trial.",
    inputs: [
      { name: "depo-excerpt.pdf", kind: "Transcript", description: "Nair deposition, 14 pages with condensed page:line numbering." },
      { name: "prior-statements.pdf", kind: "Sworn statements", description: "Two declarations and selected payroll registers." },
    ],
    rubric: {
      answerQuality: [
        { id: "AQ1", criterion: "Identifies each direct contradiction between testimony and prior statement", points: 3 },
        { id: "AQ2", criterion: "Drafts a proper impeachment question (commit, credit, confront)", points: 2 },
        { id: "AQ3", criterion: "Distinguishes actual contradictions from mere ambiguity", points: 2 },
        { id: "AQ4", criterion: "Treats an ambiguous difference as a hard contradiction", points: -2 },
      ],
      sourceReliability: [
        { id: "SR1", criterion: "Every point carries page:line cites for both sources", points: 3 },
        { id: "SR2", criterion: "Quotes are verbatim from the transcript and declarations", points: 2 },
        { id: "SR3", criterion: "Miscites a page:line or misattributes a quote", points: -4 },
      ],
    },
  },
  {
    id: "core-privilege-triage",
    title: "Privilege log triage",
    part: "core",
    track: "litigation",
    category: "Document Review and Analysis",
    minutes: 20,
    summary:
      "Decide what is actually privileged across a stack of emails — no over-designation, no waiver — and produce defensible log entries.",
    instructions:
      "You receive 12 documents from the client for privilege review. For each: determine whether attorney-client privilege, work product, or neither applies; note any waiver risk (third parties on the thread, business-advice-only content); and draft a log entry (date, author, recipients, privilege basis) for those withheld.",
    inputs: [
      { name: "review-set.pdf", kind: "Document set", description: "12 emails with headers and attachments listed." },
      { name: "matter-summary.md", kind: "Context", description: "Claims at issue and who counsel represents." },
    ],
    rubric: {
      answerQuality: [
        { id: "AQ1", criterion: "Correctly separates legal advice from business communications", points: 3 },
        { id: "AQ2", criterion: "Spots waiver risks (third-party presence) on at least the plain cases", points: 2 },
        { id: "AQ3", criterion: "Log entries complete: date, author, recipients, basis", points: 2 },
        { id: "AQ4", criterion: "Designates a purely business email as privileged", points: -3 },
      ],
      sourceReliability: [
        { id: "SR1", criterion: "Each call references the document by its production number", points: 2 },
        { id: "SR2", criterion: "Describes withheld documents accurately without revealing privileged content", points: 1 },
      ],
    },
  },
  {
    id: "wf-spa-deal-points",
    title: "Extract deal points from a Share Purchase Agreement",
    part: "workflows",
    track: "agentic",
    category: "SPA Deal Points",
    minutes: 45,
    summary:
      "Work through a long SPA end to end — following defined terms and cross-references — and extract every negotiated deal point into a structured table.",
    instructions:
      "Read the attached Share Purchase Agreement in full. Extract every deal point into a table with: Deal point, Section, Value/Terms, and any conditions or cross-references that qualify it. The deal points must include purchase price and adjustments, escrow/holdback (amount and release conditions), indemnity basket/cap and carve-outs, closing conditions, termination rights and their triggers, restrictive covenants and durations, and governing law/forum. Where a deal point depends on a defined term, resolve the definition and note it.",
    inputs: [
      { name: "spa-full.pdf", kind: "Agreement", description: "Share Purchase Agreement, 84 pages, heavy defined terms and cross-references." },
      { name: "extraction-schema.json", kind: "Output schema", description: "Required columns and accepted value formats." },
    ],
    rubric: {
      answerQuality: [
        { id: "AQ1", criterion: "Extracts purchase price mechanism including the working-capital adjustment", points: 3 },
        { id: "AQ2", criterion: "Captures escrow/holdback amount AND release conditions", points: 2 },
        { id: "AQ3", criterion: "Captures indemnity basket, cap, and carve-outs as separate fields", points: 3 },
        { id: "AQ4", criterion: "Lists termination rights with their actual triggers (not paraphrased away)", points: 3 },
        { id: "AQ5", criterion: "Resolves defined terms the deal points depend on (e.g., what 'Losses' includes)", points: 2 },
        { id: "AQ6", criterion: "Reports a deal point value that contradicts the agreement text", points: -4 },
      ],
      sourceReliability: [
        { id: "SR1", criterion: "Every row cites the SPA section it came from", points: 3 },
        { id: "SR2", criterion: "Conditions/qualifiers column reflects the agreement's actual conditions", points: 2 },
        { id: "SR3", criterion: "Cites a section that does not contain the extracted term", points: -3 },
      ],
    },
  },
  {
    id: "wf-data-room-index",
    title: "Build a closing-ready data room index",
    part: "workflows",
    track: "agentic",
    category: "Deal Management",
    minutes: 40,
    summary:
      "Follow a diligence checklist across a messy document bundle, build the closing index, and surface every gap that would hold up signing.",
    instructions:
      "Work through the data room bundle against the buyer's diligence checklist. Produce a closing-ready index: for each checklist item, the supporting document(s) (with dates and execution status), or an explicit gap flag. Where a document is unsigned, misdated, or inconsistent with another document in the bundle, flag it as a closing issue with a one-line description of the problem.",
    inputs: [
      { name: "data-room-bundle/", kind: "Document bundle", description: "Board minutes, cap table, employment agreements, lease abstract, insurance certificates, finance memos." },
      { name: "diligence-checklist.md", kind: "Checklist", description: "The buyer's required evidence list, item by item." },
    ],
    rubric: {
      answerQuality: [
        { id: "AQ1", criterion: "Indexes every checklist item to a document or an explicit gap", points: 3 },
        { id: "AQ2", criterion: "Records execution status (signed/unsigned) for each document", points: 2 },
        { id: "AQ3", criterion: "Flags inconsistencies between documents (e.g., dates or amounts that disagree)", points: 3 },
        { id: "AQ4", criterion: "Closing issues stated with a one-line problem description", points: 2 },
        { id: "AQ5", criterion: "Marks a checklist item satisfied by a document that does not actually support it", points: -4 },
      ],
      sourceReliability: [
        { id: "SR1", criterion: "Every index row cites the document it points to by name and date", points: 2 },
        { id: "SR2", criterion: "Gap flags state exactly what evidence is missing", points: 2 },
        { id: "SR3", criterion: "Attributes a date or status to a document that contradicts the bundle", points: -3 },
      ],
    },
  },
  {
    id: "ret-contracts-defined-terms",
    title: "Resolve defined-term cross-references in a merger agreement",
    part: "retrieval",
    track: "corpus",
    category: "Contracts — Merger Agreements & SPAs",
    minutes: 15,
    summary:
      "Given a term used in a dense agreement, return its definition, where it is defined, and the passages where it drives an obligation.",
    instructions:
      "For each queried term (e.g., 'Company Material Adverse Effect', 'Working Capital', 'Excluded Liabilities'): return (1) the definition verbatim with its section, (2) every section where the term creates or modifies an obligation, quoted briefly, and (3) any related defined terms the definition itself depends on. Precision matters more than recall — returning the wrong passage is worse than returning fewer, exact ones.",
    inputs: [
      { name: "merger-agreement-corpus/", kind: "Corpus", description: "Long-form agreements with dense cross-references and defined-term chains." },
      { name: "queries.json", kind: "Query set", description: "Terms to resolve, one per query." },
    ],
    rubric: {
      answerQuality: [
        { id: "AQ1", criterion: "Returns the verbatim definition with the correct section for each query", points: 3 },
        { id: "AQ2", criterion: "Identifies the sections where the term drives an obligation", points: 3 },
        { id: "AQ3", criterion: "Follows defined-term chains the definition depends on", points: 2 },
        { id: "AQ4", criterion: "Returns a passage that is not the definition or an operative use", points: -4 },
      ],
      sourceReliability: [
        { id: "SR1", criterion: "Every returned passage carries its section reference", points: 2 },
        { id: "SR2", criterion: "Verbatim quotes match the corpus exactly", points: 2 },
      ],
    },
  },
  {
    id: "ret-discovery-emails",
    title: "Retrieve a responsive email thread",
    part: "retrieval",
    track: "corpus",
    category: "Discovery Emails",
    minutes: 15,
    summary:
      "Over a high-volume email corpus, retrieve the exact thread that answers a discovery request — right custodian, right window, whole thread, no strays.",
    instructions:
      "The discovery request seeks: all emails between custodian P. Nair and Western Foods regarding pricing commitments, from 2026-01-01 to 2026-06-30. Retrieve the responsive thread(s): full thread (not fragments), with date, sender, recipients, and subject for each message. Flag any message in the thread that falls outside the date window but is part of the same chain.",
    inputs: [
      { name: "discovery-corpus/", kind: "Corpus", description: "High-volume short documents: email with threading, headers, and metadata." },
      { name: "request.md", kind: "Request", description: "The discovery request with custodians, entities, date range, and topics." },
    ],
    rubric: {
      answerQuality: [
        { id: "AQ1", criterion: "Retrieves the correct thread(s) for the named custodian and counterparty", points: 3 },
        { id: "AQ2", criterion: "Respects the date window while keeping the chain intact", points: 2 },
        { id: "AQ3", criterion: "Returns complete threads, not isolated fragments", points: 2 },
        { id: "AQ4", criterion: "Includes messages from unrelated threads or custodians", points: -3 },
      ],
      sourceReliability: [
        { id: "SR1", criterion: "Each message identified by message-id or header citation", points: 2 },
        { id: "SR2", criterion: "Metadata (date/sender/recipients) reported matches the corpus", points: 2 },
      ],
    },
  },
];

export const CATEGORIES_BY_TRACK: Record<Track, { label: string; part: Part }[]> = {
  transactional: [
    { label: "Corporate Strategy & Advising", part: "core" },
    { label: "Drafting", part: "core" },
    { label: "Legal Research", part: "core" },
    { label: "Due Diligence", part: "core" },
    { label: "Risk Assessment & Compliance", part: "core" },
    { label: "Negotiation Strategy", part: "core" },
    { label: "Deal Management", part: "core" },
    { label: "Transaction Structuring", part: "core" },
    { label: "Regulatory & Advising", part: "core" },
  ],
  litigation: [
    { label: "Analysis of Litigation Filings", part: "core" },
    { label: "Case Management", part: "core" },
    { label: "Drafting", part: "core" },
    { label: "Case Law Research", part: "core" },
    { label: "Transcript Analysis", part: "core" },
    { label: "Document Review and Analysis", part: "core" },
    { label: "Trial Preparations & Oral Argument", part: "core" },
  ],
  agentic: [{ label: "SPA Deal Points", part: "workflows" }],
  corpus: [
    { label: "Contracts — Merger Agreements & SPAs", part: "retrieval" },
    { label: "Discovery Emails", part: "retrieval" },
  ],
};

export function taskById(id: string): ExampleTask | undefined {
  return TASKS.find((task) => task.id === id);
}

export function rubricTotals(rubric: Rubric): { positive: number; penalties: number } {
  const items = [...rubric.answerQuality, ...rubric.sourceReliability];
  return {
    positive: items.filter((i) => i.points > 0).reduce((sum, i) => sum + i.points, 0),
    penalties: items.filter((i) => i.points < 0).reduce((sum, i) => sum + Math.abs(i.points), 0),
  };
}
