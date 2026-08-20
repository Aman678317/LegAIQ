"use client";

import { useEffect, useState } from "react";
import {
  TrendingUp,
  DollarSign,
  Clock,
  Zap,
  Activity,
  BarChart3,
  PieChart,
  Users,
  Briefcase,
  Layers,
  ArrowUpRight,
  Download,
  Loader2,
  Calendar,
} from "lucide-react";
import { Button, Card } from "@/components/ui";
import { api } from "@/lib/api";

export default function CommandCenterPage() {
  const [period, setPeriod] = useState("month");
  const [loading, setLoading] = useState(false);

  // Enterprise Metrics
  const metrics = {
    total_tokens: "4.82M",
    tokens_growth: "+18.4%",
    total_cost_usd: "$142.80",
    cost_inr: "₹11,850",
    attorney_hours_saved: "248.5 hrs",
    hours_growth: "+32.1%",
    estimated_savings_usd: "$18,637",
    net_roi_percentage: "12,950%",
    turnaround_velocity: "4.2 hrs / matter",
    velocity_improvement: "72% faster",
    model_breakdown: [
      { model: "Claude 3.5 Sonnet", share: 42, tokens: "2.02M", cost: "$64.20", provider: "Anthropic" },
      { model: "GPT-4o", share: 28, tokens: "1.35M", cost: "$48.10", provider: "OpenAI" },
      { model: "DeepSeek R1", share: 18, tokens: "867K", cost: "$18.50", provider: "DeepSeek" },
      { model: "Ollama (Local Llama-3 70B)", share: 12, tokens: "580K", cost: "$0.00", provider: "Local Hermetic" },
    ],
    matter_costs: [
      { case_name: "Vodafone International B.V. v. UOI", client: "Vodafone Group", tokens: "840K", cost: "$24.50", hours_saved: "42 hrs", status: "Active" },
      { case_name: "Brigade Meadows Sy 124 Title Search", client: "Brigade Enterprises", tokens: "620K", cost: "$18.20", hours_saved: "35 hrs", status: "Completed" },
      { case_name: "Tata Sons Commercial MSA Review", client: "Tata Consultancy", tokens: "510K", cost: "$15.40", hours_saved: "28 hrs", status: "In Review" },
      { case_name: "Prestige Tech Park Phase 3 Title DAG", client: "Prestige Estates", tokens: "430K", cost: "$12.80", hours_saved: "22 hrs", status: "Completed" },
      { case_name: "Infosys Software Licensing Redline", client: "Infosys Ltd", tokens: "380K", cost: "$11.20", hours_saved: "19 hrs", status: "Active" },
    ],
  };

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-white tracking-tight">Enterprise Command Center</h1>
            <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
              ROI &amp; Telemetry Live
            </span>
          </div>
          <p className="mt-1 text-sm text-text-secondary">
            Firm-wide AI token consumption, matter billing breakdown, attorney time saved, and ROI analytics.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center rounded-lg border border-border bg-surface p-1">
            {["week", "month", "quarter", "year"].map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`rounded-md px-3 py-1 text-xs font-medium capitalize transition-colors ${
                  period === p ? "bg-primary text-white" : "text-text-secondary hover:text-white"
                }`}
              >
                {p}
              </button>
            ))}
          </div>

          <Button variant="secondary" size="sm" className="flex items-center gap-1.5">
            <Download size={14} /> Export Report
          </Button>
        </div>
      </div>

      {/* KPI Top Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Card 1: Token Usage */}
        <Card className="p-5 border-border bg-surface flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-text-muted">Total Token Consumption</span>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/15 text-blue-400">
              <Zap size={16} />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold text-white">{metrics.total_tokens}</div>
            <div className="mt-1 flex items-center gap-1 text-xs text-emerald-400 font-medium">
              <ArrowUpRight size={13} /> {metrics.tokens_growth} vs last period
            </div>
          </div>
        </Card>

        {/* Card 2: AI Spend */}
        <Card className="p-5 border-border bg-surface flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-text-muted">Total AI Cost (Firm-wide)</span>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400">
              <DollarSign size={16} />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold text-white">{metrics.total_cost_usd}</div>
            <div className="mt-1 text-xs text-text-muted">Equivalent: {metrics.cost_inr}</div>
          </div>
        </Card>

        {/* Card 3: Attorney Time Saved */}
        <Card className="p-5 border-border bg-surface flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-text-muted">Attorney Hours Saved</span>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-500/15 text-purple-400">
              <Clock size={16} />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold text-white">{metrics.attorney_hours_saved}</div>
            <div className="mt-1 flex items-center gap-1 text-xs text-emerald-400 font-medium">
              <ArrowUpRight size={13} /> {metrics.hours_growth} velocity
            </div>
          </div>
        </Card>

        {/* Card 4: Net ROI */}
        <Card className="p-5 border-border bg-surface flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-text-muted">Estimated Net ROI</span>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/15 text-amber-400">
              <TrendingUp size={16} />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold text-emerald-400">{metrics.net_roi_percentage}</div>
            <div className="mt-1 text-xs text-text-muted">Savings: {metrics.estimated_savings_usd}</div>
          </div>
        </Card>
      </div>

      {/* Model Breakdown & Cost Distribution */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Model Consumption Table */}
        <Card className="p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center gap-2">
              <Layers size={16} className="text-primary" />
              <h3 className="text-sm font-semibold text-white">LLM Provider &amp; Model Distribution</h3>
            </div>
          </div>

          <div className="space-y-3">
            {metrics.model_breakdown.map((m) => (
              <div key={m.model} className="space-y-1.5 rounded-xl border border-border/60 bg-surface/50 p-3.5">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white">{m.model}</span>
                    <span className="rounded bg-bg px-2 py-0.5 font-mono text-[10px] text-text-muted">
                      {m.provider}
                    </span>
                  </div>
                  <span className="font-mono font-medium text-white">{m.cost}</span>
                </div>

                <div className="flex items-center justify-between text-[11px] text-text-muted">
                  <span>{m.tokens} tokens</span>
                  <span>{m.share}% share</span>
                </div>

                {/* Progress bar */}
                <div className="h-1.5 w-full rounded-full bg-bg overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full"
                    style={{ width: `${m.share}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Velocity & Efficiency Card */}
        <Card className="p-6 space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Activity size={16} className="text-emerald-400" />
                <h3 className="text-sm font-semibold text-white">Turnaround Velocity &amp; Efficiency</h3>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-4">
              <div className="rounded-xl border border-border bg-bg p-4 text-center">
                <span className="text-xs text-text-muted">Average Title Search Turnaround</span>
                <div className="mt-2 text-xl font-bold text-white">{metrics.turnaround_velocity}</div>
                <span className="text-[11px] text-emerald-400 font-medium">Down from 18 days manual</span>
              </div>

              <div className="rounded-xl border border-border bg-bg p-4 text-center">
                <span className="text-xs text-text-muted">Contract Review Speed</span>
                <div className="mt-2 text-xl font-bold text-white">12 min / contract</div>
                <span className="text-[11px] text-emerald-400 font-medium">92% acceleration</span>
              </div>
            </div>

            <p className="mt-4 text-xs leading-relaxed text-text-secondary">
              LegAIQ multi-agent pipelines automate document OCR, 13-30 year chain reconstruction, 9-category risk
              audits, and BSA 2023 evidence hashing to reduce legal risk while cutting matter turnaround.
            </p>
          </div>

          <div className="rounded-xl border border-primary/30 bg-primary/10 p-3.5 flex items-center justify-between text-xs">
            <span className="text-blue-300 font-medium">Ready to export formal audit statement?</span>
            <Button size="sm" variant="secondary" className="h-7 text-xs">
              Generate Billing PDF
            </Button>
          </div>
        </Card>
      </div>

      {/* Cost & Time Saved Per Matter */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <div className="flex items-center gap-2">
            <Briefcase size={16} className="text-primary" />
            <h3 className="text-sm font-semibold text-white">Matter &amp; Client Cost Breakdown</h3>
          </div>
          <span className="text-xs text-text-muted">Top 5 Active Matters</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-border text-text-muted">
                <th className="pb-3 font-semibold">Matter Name</th>
                <th className="pb-3 font-semibold">Client</th>
                <th className="pb-3 font-semibold">Tokens</th>
                <th className="pb-3 font-semibold">AI Cost</th>
                <th className="pb-3 font-semibold">Time Saved</th>
                <th className="pb-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {metrics.matter_costs.map((m, i) => (
                <tr key={i} className="hover:bg-white/[0.02]">
                  <td className="py-3 font-medium text-white">{m.case_name}</td>
                  <td className="py-3 text-text-secondary">{m.client}</td>
                  <td className="py-3 font-mono text-text-muted">{m.tokens}</td>
                  <td className="py-3 font-mono font-medium text-emerald-400">{m.cost}</td>
                  <td className="py-3 text-text-secondary">{m.hours_saved}</td>
                  <td className="py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        m.status === "Completed"
                          ? "bg-emerald-500/20 text-emerald-400"
                          : "bg-blue-500/20 text-blue-400"
                      }`}
                    >
                      {m.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
