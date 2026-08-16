"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Network, Loader2, RefreshCw, Users, Landmark } from "lucide-react";
import { api } from "@/lib/api";
import { Button, Card } from "@/components/ui";

const EDGE_LABELS: Record<string, string> = {
  OWNED: "owns", TRANSFERRED: "transferred to", INHERITED: "inherited by",
  GIFTED: "gifted to", MORTGAGED: "mortgaged to", RELEASED: "released to",
  PARTITIONED: "partitioned",
};

export default function OwnershipPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [graph, setGraph] = useState<{ nodes: any[]; edges: any[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [rebuilding, setRebuilding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<any>(null);

  async function load() {
    try {
      const g = await api.getOwnership(caseId);
      setGraph(g);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [caseId]);

  async function rebuild() {
    setRebuilding(true);
    try {
      await api.rebuildOwnership(caseId);
      setTimeout(load, 4000);
    } catch (e: any) {
      setError(e.message);
      setRebuilding(false);
    }
  }

  if (loading) {
    return <div className="flex h-96 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];

  const nodeById = Object.fromEntries(nodes.map((n) => [n.id, n]));

  // Build simple layered layout: persons on left, property center
  const persons = nodes.filter((n) => n.node_type === "PERSON");
  const properties = nodes.filter((n) => n.node_type !== "PERSON");

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Ownership Chain</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Every relationship requires evidence. Click an edge to inspect its source.
          </p>
        </div>
        <Button onClick={rebuild} disabled={rebuilding} variant="secondary">
          {rebuilding ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
          Rebuild chain
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {nodes.length === 0 ? (
        <Card className="flex flex-col items-center p-12 text-center">
          <Network size={32} className="mb-3 text-text-muted" />
          <h3 className="text-base font-semibold text-white">No ownership graph yet</h3>
          <p className="mt-2 max-w-md text-sm text-text-secondary">
            Upload documents with parties (sellers, buyers, heirs). The chain rebuilds
            automatically after extraction — or click &ldquo;Rebuild chain&rdquo;.
          </p>
        </Card>
      ) : (
        <>
          {/* Relationship list */}
          <div className="space-y-3">
            {edges.map((edge) => {
              const source = nodeById[edge.source_id];
              const target = nodeById[edge.target_id];
              const evidence = edge.evidence || [];
              return (
                <Card
                  key={edge.id}
                  className="cursor-pointer p-5 transition-colors hover:border-primary/40"
                  onClick={() => setSelectedEdge(selectedEdge?.id === edge.id ? null : edge)}
                >
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      {source?.node_type === "PERSON" ? (
                        <Users size={16} className="text-accent" />
                      ) : (
                        <Landmark size={16} className="text-primary" />
                      )}
                      <span className="text-sm font-medium text-white">{source?.label}</span>
                    </div>
                    <div className="flex flex-1 items-center gap-2">
                      <div className="h-px flex-1 bg-gradient-to-r from-border-light to-primary/50" />
                      <span className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-blue-300">
                        {EDGE_LABELS[edge.edge_type] || edge.edge_type}
                        {edge.event_date ? ` · ${edge.event_date}` : ""}
                      </span>
                      <div className="h-px flex-1 bg-gradient-to-l from-border-light to-primary/50" />
                    </div>
                    <div className="flex items-center gap-2">
                      {target?.node_type === "PERSON" ? (
                        <Users size={16} className="text-accent" />
                      ) : (
                        <Landmark size={16} className="text-primary" />
                      )}
                      <span className="text-sm font-medium text-white">{target?.label}</span>
                    </div>
                    <span className="ml-2 shrink-0 text-xs text-text-muted">
                      {(edge.confidence * 100).toFixed(0)}%
                    </span>
                  </div>

                  {selectedEdge?.id === edge.id && (
                    <div className="mt-4 space-y-2 border-t border-border pt-4">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">Evidence</p>
                      {evidence.map((ev: any, i: number) => (
                        <div key={i} className="rounded-lg border border-border bg-bg px-3 py-2 font-mono text-xs">
                          <span className="text-white">{ev.document_name} · p.{ev.page_number}</span>
                          <div className="mt-1 text-emerald-400">&ldquo;{ev.source_text?.slice(0, 200)}&rdquo;</div>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              );
            })}
          </div>

          <p className="text-xs text-text-muted">
            {nodes.filter((n) => n.node_type === "PERSON").length} parties ·{" "}
            {properties.length} properties · {edges.length} evidenced relationships
          </p>
        </>
      )}
    </div>
  );
}
