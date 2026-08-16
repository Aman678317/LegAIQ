"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { FileBarChart, Loader2, Download, Plus } from "lucide-react";
import { api } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { formatDateTime } from "@/lib/utils";

export default function ReportsPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewing, setViewing] = useState<any>(null);

  async function load() {
    try {
      setReports(await api.listReports(caseId));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [caseId]);

  async function generate() {
    setGenerating(true);
    setError(null);
    try {
      await api.generateReport(caseId);
      setTimeout(load, 4000);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setGenerating(false);
    }
  }

  async function openReport(report: any) {
    try {
      const full = await api.getReport(report.id);
      setViewing(full);
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function exportReport(reportId: string, format: "pdf" | "docx") {
    try {
      await api.exportReport(reportId, format);
      setError(null);
      // Note: download URL delivery via storage path once worker completes
      setTimeout(() => setError(null), 100);
    } catch (e: any) {
      setError(e.message);
    }
  }

  if (loading) {
    return <div className="flex h-96 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Reports</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Property Due Diligence reports compile the full evidence trail:
            documents, ownership, timeline, comparisons, and risks.
          </p>
        </div>
        <Button onClick={generate} disabled={generating}>
          {generating ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />}
          Generate Report
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {viewing ? (
        <Card className="p-8">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">{viewing.title}</h2>
              <p className="text-xs text-text-muted">
                Generated {formatDateTime(viewing.completed_at || viewing.created_at)}
              </p>
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="secondary" onClick={() => exportReport(viewing.id, "pdf")}>
                <Download size={13} /> PDF
              </Button>
              <Button size="sm" variant="secondary" onClick={() => exportReport(viewing.id, "docx")}>
                <Download size={13} /> DOCX
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setViewing(null)}>
                Close
              </Button>
            </div>
          </div>

          <div className="mt-6 space-y-6">
            {Object.entries(viewing.content || {}).map(([section, value]: [string, any]) => (
              <div key={section}>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-primary">
                  {section.replace(/_/g, " ")}
                </h3>
                <div className="mt-2 rounded-lg border border-border bg-bg p-4">
                  {typeof value === "string" ? (
                    <p className="text-sm leading-relaxed text-text-secondary">{value}</p>
                  ) : Array.isArray(value) ? (
                    <ul className="space-y-1.5">
                      {value.map((item: any, i: number) => (
                        <li key={i} className="text-sm text-text-secondary">
                          {typeof item === "string" ? item : JSON.stringify(item, null, 2).slice(0, 200)}
                        </li>
                      ))}
                    </ul>
                  ) : value ? (
                    <pre className="overflow-x-auto text-xs text-text-secondary">
                      {JSON.stringify(value, null, 2)}
                    </pre>
                  ) : (
                    <p className="text-sm text-text-muted">Not available</p>
                  )}
                </div>
              </div>
            ))}
          </div>

          <p className="mt-6 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-2.5 text-xs text-amber-400/90">
            AI-generated report. Review and verify before relying upon.
          </p>
        </Card>
      ) : reports.length === 0 ? (
        <Card className="flex flex-col items-center p-12 text-center">
          <FileBarChart size={32} className="mb-3 text-text-muted" />
          <h3 className="text-base font-semibold text-white">No reports yet</h3>
          <p className="mt-2 max-w-md text-sm text-text-secondary">
            Generate a Property Due Diligence report once your documents are processed.
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {reports.map((report) => (
            <Card key={report.id} className="flex items-center gap-4 p-5">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-bg-elevated">
                <FileBarChart size={18} className="text-primary" />
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="truncate text-sm font-semibold text-white">{report.title}</h3>
                <p className="text-xs text-text-muted">{formatDateTime(report.created_at)}</p>
                {report.error_message && (
                  <p className="text-xs text-red-400">{report.error_message}</p>
                )}
              </div>
              <Badge className={
                report.status === "COMPLETED"
                  ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-400"
                  : report.status === "FAILED"
                  ? "border-red-500/30 bg-red-500/15 text-red-400"
                  : "border-blue-500/30 bg-blue-500/15 text-blue-400"
              }>
                {report.status}
              </Badge>
              {report.status === "COMPLETED" && (
                <Button size="sm" variant="secondary" onClick={() => openReport(report)}>
                  View
                </Button>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
