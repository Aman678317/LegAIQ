import Link from "next/link";
import {
  FileSearch, Landmark, Scale, Bot, PenLine, Mic, Languages,
  ShieldCheck, Building2, ArrowRight, ChevronDown, CheckCircle2,
  Network, GitCompare, AlertTriangle, Search,
} from "lucide-react";
import { Button, Card, Badge, SectionHeading } from "@/components/ui";

const NAV_LINKS = [
  { href: "#product", label: "Product" },
  { href: "#how-it-works", label: "How It Works" },
  { href: "#capabilities", label: "Capabilities" },
  { href: "#pricing", label: "Pricing" },
  { href: "#faq", label: "FAQ" },
];

function Nav() {
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-border/60 bg-bg/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent">
            <Scale className="text-white" size={18} />
          </div>
          <span className="text-lg font-semibold tracking-tight text-white">
            Jurisiva<span className="text-primary"> AI</span>
          </span>
        </Link>
        <nav className="hidden items-center gap-8 md:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm text-text-secondary transition-colors hover:text-white"
            >
              {link.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" href="/login">
            Sign in
          </Button>
          <Button size="sm" href="/signup">
            Start a Property Case
          </Button>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="hero-glow relative overflow-hidden pt-32 pb-24">
      <div className="grid-pattern absolute inset-0" />
      <div className="relative mx-auto max-w-7xl px-6 text-center">
        <div className="animate-fade-up mx-auto max-w-4xl">
          <Badge className="mb-6 border-primary/30 bg-primary/10 text-blue-300">
            <ShieldCheck size={13} className="mr-1.5" />
            Evidence-first legal AI · Every finding cites its source
          </Badge>
          <h1 className="text-5xl font-semibold leading-[1.08] tracking-tight text-white sm:text-6xl lg:text-7xl">
            AI for Legal Work.
            <br />
            <span className="bg-gradient-to-r from-primary via-blue-400 to-accent bg-clip-text text-transparent">
              Built for India.
            </span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-text-secondary">
            Jurisiva reads decades-old property documents in 11 Indian languages,
            reconstructs the ownership chain, flags title risks with page-level
            evidence, and drafts what you need — so your team verifies instead of
            searches.
          </p>
          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Button size="lg" href="/signup" className="group">
              Start a Property Case
              <ArrowRight size={18} className="transition-transform group-hover:translate-x-1" />
            </Button>
            <Button size="lg" variant="secondary" href="#how-it-works">
              See How It Works
            </Button>
          </div>
          <p className="mt-5 text-xs text-text-muted">
            Upload a sale deed → get the full ownership chain in minutes.
          </p>
        </div>

        {/* Product preview */}
        <div className="animate-fade-up mx-auto mt-16 max-w-5xl" style={{ animationDelay: "0.15s" }}>
          <div className="overflow-hidden rounded-2xl border border-border bg-bg-surface shadow-2xl shadow-primary/10">
            <div className="flex items-center gap-2 border-b border-border px-4 py-3">
              <div className="h-3 w-3 rounded-full bg-red-500/60" />
              <div className="h-3 w-3 rounded-full bg-amber-500/60" />
              <div className="h-3 w-3 rounded-full bg-emerald-500/60" />
              <div className="ml-4 flex items-center gap-2 rounded-md bg-bg px-3 py-1 text-xs text-text-muted">
                <Search size={12} />
                <span>app.jurisiva.ai/cases/sale-deed-1987/ownership</span>
              </div>
            </div>
            <div className="grid gap-px bg-border md:grid-cols-[220px_1fr]">
              <div className="space-y-1 bg-bg-surface p-4">
                {["Case Home", "Documents", "AI Analysis", "Ownership Chain", "Property Timeline", "Comparison", "Risks & Issues", "Legal Research", "Drafting", "Reports"].map((item, i) => (
                  <div
                    key={item}
                    className={`flex items-center gap-2.5 rounded-md px-3 py-2 text-xs ${
                      i === 3 ? "bg-primary/15 text-blue-300" : "text-text-secondary"
                    }`}
                  >
                    <div className={`h-1.5 w-1.5 rounded-full ${i === 3 ? "bg-primary" : "bg-text-muted/40"}`} />
                    {item}
                  </div>
                ))}
              </div>
              <div className="bg-bg p-6">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-white">Ownership Chain — Sy. No. 124/3, Whitefield</h3>
                    <p className="text-xs text-text-muted">Reconstructed from 4 documents · 6 evidence links</p>
                  </div>
                  <Badge className="border-emerald-500/30 bg-emerald-500/15 text-emerald-400">
                    <CheckCircle2 size={12} className="mr-1" /> Chain complete
                  </Badge>
                </div>
                <div className="space-y-3">
                  {[
                    { party: "Venkatarama Reddy", action: "OWNED since 1962", doc: "Original Grant · p.1", tone: "text-emerald-400" },
                    { party: "Sale → Lakshmamma", action: "TRANSFERRED 1987 · Rs. 45,000", doc: "Sale Deed.pdf · p.3", tone: "text-blue-400" },
                    { party: "Inheritance → 3 heirs", action: "INHERITED 2003", doc: "Family Settlement · p.2", tone: "text-violet-400" },
                    { party: "Release by 2 heirs", action: "RELEASED 2005", doc: "Release Deed · p.1", tone: "text-amber-400" },
                    { party: "Current recorded owner: Suresh Kumar", action: "OWNED since 2005", doc: "Mutation Register · p.12", tone: "text-emerald-400" },
                  ].map((step, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border bg-bg-surface text-xs font-semibold ${step.tone}`}>
                        {i + 1}
                      </div>
                      <div className="flex-1 rounded-lg border border-border bg-bg-surface px-4 py-2.5">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-white">{step.party}</span>
                          <span className={`text-xs font-medium ${step.tone}`}>{step.action}</span>
                        </div>
                        <p className="mt-0.5 font-mono text-[11px] text-text-muted">Evidence: {step.doc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function ProductExplanation() {
  const items = [
    {
      icon: <FileSearch className="h-6 w-6 text-primary" />,
      title: "Document Intelligence",
      text: "OCR tuned for faded 1960s deeds, stamped pages, and handwritten margins. Every page keeps its original alongside extracted text, translations, and confidence scores.",
    },
    {
      icon: <Network className="h-6 w-6 text-accent" />,
      title: "Ownership Intelligence",
      text: "Jurisiva reconstructs the full chain — grants, sales, inheritances, partitions, releases — and shows the exact document and page proving each link.",
    },
    {
      icon: <AlertTriangle className="h-6 w-6 text-warning" />,
      title: "Risk Intelligence",
      text: "Survey mismatches, missing mutation entries, conflicting areas — every risk is traced to evidence, ranked by severity, and paired with a recommended next step.",
    },
  ];
  return (
    <section id="product" className="border-t border-border/50 py-24">
      <div className="mx-auto max-w-7xl px-6">
        <SectionHeading
          eyebrow="The Product"
          title="One workspace for the entire evidence trail"
          description="Jurisiva turns a folder of old papers into a structured, citable, verifiable case file."
        />
        <div className="mt-16 grid gap-6 md:grid-cols-3">
          {items.map((item) => (
            <Card key={item.title} className="group p-8 transition-colors hover:border-primary/40">
              <div className="mb-5 inline-flex rounded-xl border border-border bg-bg-elevated p-3">
                {item.icon}
              </div>
              <h3 className="text-lg font-semibold text-white">{item.title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-text-secondary">{item.text}</p>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}

function HowItWorks() {
  const steps = [
    { n: "01", title: "Create a case", text: "Set the jurisdiction and property details you know. Jurisiva marks them as user-provided until documents verify them." },
    { n: "02", title: "Upload everything", text: "PDFs, phone photos of old deeds, mutation extracts — any format, any condition, any of 11 languages." },
    { n: "03", title: "Jurisiva reads & extracts", text: "OCR runs page by page. Parties, survey numbers, amounts, and dates are extracted with source text and confidence." },
    { n: "04", title: "Verify the findings", text: "Review the ownership chain, comparison table, and risk register — each entry opens its evidence page." },
  ];
  return (
    <section id="how-it-works" className="border-t border-border/50 bg-bg-surface/30 py-24">
      <div className="mx-auto max-w-7xl px-6">
        <SectionHeading
          eyebrow="How It Works"
          title="From shoebox of papers to evidence-backed case file"
        />
        <div className="mt-16 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {steps.map((step, i) => (
            <div key={step.n} className="relative">
              {i < steps.length - 1 && (
                <div className="absolute left-full top-8 hidden h-px w-6 bg-border-light lg:block" />
              )}
              <div className="font-mono text-sm font-semibold text-primary">{step.n}</div>
              <h3 className="mt-3 text-base font-semibold text-white">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-text-secondary">{step.text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

const CAPABILITIES = [
  {
    id: "property",
    icon: <Landmark className="h-5 w-5" />,
    title: "Property Intelligence",
    subtitle: "The full field set for Indian land records",
    points: [
      "Survey, hissa, khata, plot & registration numbers",
      "State → district → taluk → village hierarchy",
      "USER PROVIDED vs DOCUMENT VERIFIED labels on every field",
      "No ownership claim without document evidence",
    ],
  },
  {
    id: "documents",
    icon: <FileSearch className="h-5 w-5" />,
    title: "Old Document Intelligence",
    subtitle: "Built for the documents that matter most",
    points: [
      "Sale, gift, partition, release & mortgage deeds",
      "Mutation and revenue records, court orders",
      "Faded text, rotated scans, stamps, tables",
      "Page-by-page OCR with confidence scores",
    ],
  },
  {
    id: "research",
    icon: <Search className="h-5 w-5" />,
    title: "Legal Research",
    subtitle: "Citations you can actually open",
    points: [
      "Prioritises authoritative Indian sources",
      "Judgments, statutes, and regulations",
      "Never fabricates a citation",
      "Flags anything it cannot verify",
    ],
  },
  {
    id: "agents",
    icon: <Bot className="h-5 w-5" />,
    title: "AI Agents",
    subtitle: "Specialised, budgeted, audited",
    points: [
      "Document, Property, Research & Risk agents",
      "Token, time and cost budgets per agent",
      "Every tool call permissioned and logged",
      "No infinite loops — hard caps enforced",
    ],
  },
  {
    id: "drafting",
    icon: <PenLine className="h-5 w-5" />,
    title: "Drafting Studio",
    subtitle: "Drafts grounded in case facts",
    points: [
      "Notices, petitions, affidavats, applications",
      "Facts pulled from verified extraction only",
      "[VERIFY: …] placeholders for missing facts",
      "Human review gate before anything final",
    ],
  },
  {
    id: "voice",
    icon: <Mic className="h-5 w-5" />,
    title: "Voice Assistant",
    subtitle: "Ask about a paper, hear the answer",
    points: [
      "Speaks and understands major Indian languages",
      "Opens the referenced page automatically",
      "Responds in the language you speak",
      "Identifies itself as AI — never as a lawyer",
    ],
  },
  {
    id: "multilingual",
    icon: <Languages className="h-5 w-5" />,
    title: "Multilingual AI",
    subtitle: "11 languages at launch",
    points: [
      "English, Hindi, Kannada, Tamil, Telugu, Malayalam",
      "Marathi, Bengali, Gujarati, Punjabi, Urdu",
      "Original text always preserved",
      "Per-page translation on demand",
    ],
  },
  {
    id: "security",
    icon: <ShieldCheck className="h-5 w-5" />,
    title: "Security & Isolation",
    subtitle: "Enterprise-grade by default",
    points: [
      "Row-level tenant isolation in PostgreSQL",
      "Private document storage, signed URLs",
      "Full audit log of sensitive actions",
      "Original files are never modified",
    ],
  },
];

function Capabilities() {
  return (
    <section id="capabilities" className="border-t border-border/50 py-24">
      <div className="mx-auto max-w-7xl px-6">
        <SectionHeading
          eyebrow="Capabilities"
          title="Everything a property matter needs"
          description="Each capability is production functionality — real APIs, real processing, real evidence chains."
        />
        <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {CAPABILITIES.map((cap) => (
            <Card key={cap.id} className="flex flex-col p-6 transition-colors hover:border-primary/40">
              <div className="mb-4 inline-flex self-start rounded-lg border border-border bg-bg-elevated p-2.5 text-primary">
                {cap.icon}
              </div>
              <h3 className="text-base font-semibold text-white">{cap.title}</h3>
              <p className="mt-1 text-xs text-text-muted">{cap.subtitle}</p>
              <ul className="mt-4 space-y-2.5">
                {cap.points.map((point) => (
                  <li key={point} className="flex items-start gap-2 text-[13px] leading-snug text-text-secondary">
                    <CheckCircle2 size={14} className="mt-0.5 shrink-0 text-primary" />
                    {point}
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}

function Enterprise() {
  return (
    <section className="border-t border-border/50 bg-bg-surface/30 py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          <div>
            <SectionHeading
              center={false}
              eyebrow="Enterprise"
              title="Built for firms and legal teams"
              description="Organizations, roles, and audit trails come standard. From a single advocate practice to multi-office firms."
            />
            <div className="mt-8 space-y-4">
              {[
                { icon: <Building2 size={16} />, title: "Organizations & roles", text: "OWNER, ADMIN, LAWYER, REVIEWER, STAFF, CLIENT — enforced server-side." },
                { icon: <GitCompare size={16} />, title: "Document comparison", text: "Cross-check survey numbers, areas, and parties across every deed in the case." },
                { icon: <ShieldCheck size={16} />, title: "Audit everything", text: "Uploads, downloads, AI runs, and permission changes — all logged." },
              ].map((item) => (
                <div key={item.title} className="flex gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border bg-bg-elevated text-primary">
                    {item.icon}
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-white">{item.title}</h4>
                    <p className="mt-0.5 text-sm text-text-secondary">{item.text}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <Card className="p-8">
            <h3 className="text-sm font-semibold text-white">Evidence-first findings</h3>
            <p className="mt-1 text-xs text-text-muted">This is the actual finding format Jurisiva produces:</p>
            <div className="mt-6 space-y-3 font-mono text-xs">
              <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4">
                <div className="text-red-400">FINDING — Survey number mismatch · RISK: HIGH</div>
              </div>
              <div className="rounded-lg border border-border bg-bg-elevated p-4 leading-relaxed">
                <div className="text-text-muted">SOURCE</div>
                <div className="text-white">Sale Deed.pdf — Page 7</div>
                <div className="mt-2 text-text-muted">EVIDENCE</div>
                <div className="text-emerald-400">&ldquo;…Sy. No. 124/3 situated in Whitefield Hobli…&rdquo;</div>
                <div className="mt-2 text-text-muted">COMPARE WITH</div>
                <div className="text-white">Previous Deed.pdf — Page 3</div>
                <div className="mt-1 text-amber-400">&ldquo;…Sy. No. 124/2 measuring 2 acres 14 guntas…&rdquo;</div>
                <div className="mt-3 border-t border-border pt-3 text-blue-300">ACTION: Verify the official record at the Sub-Registrar office.</div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </section>
  );
}

const PLANS = [
  {
    name: "Free",
    price: "₹0",
    period: "forever",
    description: "For exploring one property matter end-to-end.",
    features: ["1 case workspace", "25 document pages / month", "OCR + extraction", "AI chat with citations", "1 language pair"],
    cta: "Start free",
    highlighted: false,
  },
  {
    name: "Professional",
    price: "₹4,999",
    period: "per month",
    description: "For individual advocates handling property due diligence.",
    features: ["Unlimited cases", "500 pages / month", "Ownership chain + timeline", "Risk engine + comparison", "Legal research agent", "Drafting studio", "All 11 languages"],
    cta: "Start Professional",
    highlighted: true,
  },
  {
    name: "Firm",
    price: "₹24,999",
    period: "per month",
    description: "For teams with reviewers and shared matter files.",
    features: ["Everything in Professional", "5 seats included", "Roles & permissions", "Due diligence reports (PDF)", "Priority processing queue", "Email support"],
    cta: "Contact for Firm",
    highlighted: false,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "annual",
    description: "For large firms and legal departments.",
    features: ["Everything in Firm", "SSO & SCIM", "Custom retention policies", "Dedicated infrastructure", "On-premise / private cloud", "SLA & dedicated support"],
    cta: "Talk to us",
    highlighted: false,
  },
];

function Pricing() {
  return (
    <section id="pricing" className="border-t border-border/50 py-24">
      <div className="mx-auto max-w-7xl px-6">
        <SectionHeading
          eyebrow="Pricing"
          title="Priced for Indian legal work"
          description="Start free. Upgrade when the volume of pages and matters grows."
        />
        <div className="mt-16 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {PLANS.map((plan) => (
            <Card
              key={plan.name}
              className={`relative flex flex-col p-8 ${
                plan.highlighted ? "border-primary/50 shadow-[0_0_40px_rgba(37,99,235,0.15)]" : ""
              }`}
            >
              {plan.highlighted && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Badge>Most popular</Badge>
                </div>
              )}
              <h3 className="text-lg font-semibold text-white">{plan.name}</h3>
              <div className="mt-4 flex items-baseline gap-1.5">
                <span className="text-4xl font-semibold tracking-tight text-white">{plan.price}</span>
                <span className="text-sm text-text-muted">/ {plan.period}</span>
              </div>
              <p className="mt-3 text-sm text-text-secondary">{plan.description}</p>
              <ul className="mt-6 flex-1 space-y-2.5">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-text-secondary">
                    <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-primary" />
                    {f}
                  </li>
                ))}
              </ul>
              <Button
                className="mt-8 w-full"
                variant={plan.highlighted ? "primary" : "secondary"}
                href="/signup"
              >
                {plan.cta}
              </Button>
            </Card>
          ))}
        </div>
        <p className="mt-8 text-center text-xs text-text-muted">
          Page counts refer to OCR-processed pages. No charge for storage of originals.
        </p>
      </div>
    </section>
  );
}

const FAQS = [
  {
    q: "Does Jurisiva replace a lawyer's judgment?",
    a: "No. Jurisiva is AI-assisted legal workflow support. It finds, structures, and cites evidence — professional judgment, verification, and filing decisions remain with the lawyer. Every generated document carries a review reminder.",
  },
  {
    q: "How does Jurisiva handle very old or damaged documents?",
    a: "Upload photos or scans in any condition. OCR runs page by page with preprocessing for faded text, rotation, and stamps. Where text is illegible, the page is marked low-confidence rather than guessed.",
  },
  {
    q: "Which languages are supported?",
    a: "English, Hindi, Kannada, Tamil, Telugu, Malayalam, Marathi, Bengali, Gujarati, Punjabi, and Urdu at launch. You can view any page in its original language or translated, with the original always preserved.",
  },
  {
    q: "Can Jurisiva tell me who owns a property?",
    a: "Only from your documents. Jurisiva never claims ownership without document evidence. Each link in the ownership chain cites the document and page that proves it. Fields are labelled USER PROVIDED, DOCUMENT VERIFIED, or EXTERNAL SOURCE VERIFIED.",
  },
  {
    q: "Is my data secure?",
    a: "Documents live in private storage with row-level tenant isolation in PostgreSQL. Access requires organization membership, downloads use short-lived signed URLs, and sensitive actions are audit-logged. Original files are never modified.",
  },
  {
    q: "What if the AI can't find something?",
    a: "It says so: \"Not found in the uploaded documents.\" It never invents names, dates, survey numbers, or citations. When sources conflict, both are shown.",
  },
];

function FAQ() {
  return (
    <section id="faq" className="border-t border-border/50 bg-bg-surface/30 py-24">
      <div className="mx-auto max-w-3xl px-6">
        <SectionHeading eyebrow="FAQ" title="Questions, answered plainly" />
        <div className="mt-12 space-y-4">
          {FAQS.map((faq, i) => (
            <details key={i} className="group rounded-xl border border-border bg-bg-surface">
              <summary className="flex cursor-pointer list-none items-center justify-between p-5 text-sm font-medium text-white [&::-webkit-details-marker]:hidden">
                {faq.q}
                <ChevronDown size={16} className="shrink-0 text-text-muted transition-transform group-open:rotate-180" />
              </summary>
              <p className="px-5 pb-5 text-sm leading-relaxed text-text-secondary">{faq.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

function FinalCTA() {
  return (
    <section className="border-t border-border/50 py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="hero-glow relative overflow-hidden rounded-3xl border border-border bg-bg-surface px-8 py-16 text-center sm:px-16">
          <h2 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
            Start your first property case today
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-text-secondary">
            Upload one old sale deed. Watch Jurisiva read it, extract the parties,
            and build the ownership chain — with every step citing its evidence.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Button size="lg" href="/signup" className="group">
              Start a Property Case
              <ArrowRight size={18} className="transition-transform group-hover:translate-x-1" />
            </Button>
            <Button size="lg" variant="secondary" href="/login">
              Sign in
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  const cols = [
    {
      title: "Product",
      links: ["Property Intelligence", "Document Intelligence", "Legal Research", "Drafting Studio", "Reports", "Pricing"],
    },
    {
      title: "Company",
      links: ["About", "Contact", "Careers", "Press"],
    },
    {
      title: "Resources",
      links: ["Documentation", "API Reference", "Security", "Status"],
    },
    {
      title: "Legal",
      links: ["Privacy Policy", "Terms of Service", "Data Processing", "Responsible AI"],
    },
  ];
  return (
    <footer className="border-t border-border/50 bg-bg-surface/30">
      <div className="mx-auto max-w-7xl px-6 py-16">
        <div className="grid gap-12 md:grid-cols-[1.5fr_repeat(4,1fr)]">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent">
                <Scale className="text-white" size={16} />
              </div>
              <span className="text-lg font-semibold text-white">
                Jurisiva<span className="text-primary"> AI</span>
              </span>
            </div>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-text-secondary">
              AI for legal work. Built for India. Evidence-first property and
              document intelligence for lawyers, firms, and legal teams.
            </p>
          </div>
          {cols.map((col) => (
            <div key={col.title}>
              <h4 className="text-sm font-semibold text-white">{col.title}</h4>
              <ul className="mt-4 space-y-2.5">
                {col.links.map((link) => (
                  <li key={link}>
                    <span className="cursor-pointer text-sm text-text-secondary transition-colors hover:text-white">
                      {link}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-border pt-8 sm:flex-row">
          <p className="text-xs text-text-muted">
            © {new Date().getFullYear()} Jurisiva AI. AI-assisted legal workflow support — not a substitute for professional legal judgment.
          </p>
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <ShieldCheck size={14} className="text-primary" />
            Evidence-first · Tenant-isolated · Audit-logged
          </div>
        </div>
      </div>
    </footer>
  );
}

export default function LandingPage() {
  return (
    <main className="bg-bg">
      <Nav />
      <Hero />
      <ProductExplanation />
      <HowItWorks />
      <Capabilities />
      <Enterprise />
      <Pricing />
      <FAQ />
      <FinalCTA />
      <Footer />
    </main>
  );
}
