"use client";

import { useEffect, useState } from "react";
import {
  Globe,
  Search,
  CheckCircle2,
  AlertCircle,
  Clock,
  Landmark,
  FileCheck,
  RefreshCw,
  ExternalLink,
  Shield,
  Layers,
} from "lucide-react";
import { Button, Card } from "@/components/ui";
import { api } from "@/lib/api";

const PORTAL_COLORS: Record<string, string> = {
  maharashtra: "text-orange-400 bg-orange-500/10 border-orange-500/30",
  karnataka: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  tamil_nadu: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  telangana: "text-blue-400 bg-blue-500/10 border-blue-500/30",
  gujarat: "text-purple-400 bg-purple-500/10 border-purple-500/30",
};

interface LandPortalSearchProps {
  initialSurvey?: string;
  initialDistrict?: string;
  initialTaluk?: string;
  initialVillage?: string;
  initialState?: string;
}

export function LandPortalSearch({
  initialSurvey = "124/2",
  initialDistrict = "Bangalore Urban",
  initialTaluk = "Bangalore South",
  initialVillage = "Varthur",
  initialState = "karnataka",
}: LandPortalSearchProps) {
  const [state, setState] = useState(initialState);
  const [surveyNumber, setSurveyNumber] = useState(initialSurvey);
  const [district, setDistrict] = useState(initialDistrict);
  const [taluk, setTaluk] = useState(initialTaluk);
  const [village, setVillage] = useState(initialVillage);

  const [portals, setPortals] = useState<any[]>([]);
  const [report, setReport] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getSupportedPortals().then((res) => {
      setPortals(res.portals || []);
    });
  }, []);

  const handleSearch = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.searchStatePortal({
        state,
        survey_number: surveyNumber,
        district,
        taluk,
        village,
      });
      setReport(res);
    } catch (err: any) {
      setError(err.message || "Failed to query state land portal.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Search Header Card */}
      <Card className="p-6 space-y-5 border-border bg-surface">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/20 text-primary">
              <Globe size={20} />
            </div>
            <div>
              <h3 className="font-semibold text-white text-base">5 State Official Land Portal Connectors</h3>
              <p className="text-xs text-text-secondary">
                Live official verification for Mahabhulekh, Bhoomi, Dharani, AnyRoR, and TNREGINET
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-text-muted">Target Portal:</span>
            <select
              value={state}
              onChange={(e) => setState(e.target.value)}
              className="rounded-lg border border-border bg-bg px-3 py-1.5 text-xs text-white focus:border-primary focus:outline-none"
            >
              <option value="karnataka">Karnataka (Bhoomi RTC / Pahani)</option>
              <option value="maharashtra">Maharashtra (Mahabhulekh 7/12 Satbara)</option>
              <option value="tamil_nadu">Tamil Nadu (TNREGINET / Patta Chitta)</option>
              <option value="telangana">Telangana (Dharani / Maa Bhoomi)</option>
              <option value="gujarat">Gujarat (AnyRoR / VF 7/12)</option>
            </select>
          </div>
        </div>

        {/* Input Parameters */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="text-xs font-medium text-text-secondary">Survey / Gat / Khasra No *</label>
            <input
              type="text"
              value={surveyNumber}
              onChange={(e) => setSurveyNumber(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-xs text-white focus:border-primary focus:outline-none font-mono"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-text-secondary">District *</label>
            <input
              type="text"
              value={district}
              onChange={(e) => setDistrict(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-xs text-white focus:border-primary focus:outline-none"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-text-secondary">Taluk / Tehsil *</label>
            <input
              type="text"
              value={taluk}
              onChange={(e) => setTaluk(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-xs text-white focus:border-primary focus:outline-none"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-text-secondary">Village / Hobli *</label>
            <input
              type="text"
              value={village}
              onChange={(e) => setVillage(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-xs text-white focus:border-primary focus:outline-none"
            />
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <Button onClick={handleSearch} disabled={loading} className="flex items-center gap-2">
            <Search size={14} className={loading ? "animate-spin" : ""} />
            Query Portal Live
          </Button>
        </div>
      </Card>

      {/* Results Display */}
      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-xs text-red-400">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {report && (
        <div className="space-y-6">
          {/* Base Record Card */}
          {report.base_record && (
            <Card className="p-6 space-y-4 border-border bg-surface">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <FileCheck size={18} className="text-emerald-400" />
                  <h4 className="font-semibold text-white text-sm">{report.base_record.document_type}</h4>
                </div>
                <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
                  CONFIDENCE: {Math.round((report.base_record.confidence || 0.85) * 100)}%
                </span>
              </div>

              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-lg border border-border bg-bg p-3">
                  <span className="text-[10px] uppercase text-text-muted">Owner / Khatedar</span>
                  <div className="mt-1 text-xs font-bold text-white">
                    {report.base_record.owner_names?.join(", ") || "Recorded Owner"}
                  </div>
                </div>

                <div className="rounded-lg border border-border bg-bg p-3">
                  <span className="text-[10px] uppercase text-text-muted">Total Extent / Area</span>
                  <div className="mt-1 text-xs font-bold text-white">{report.base_record.area_formatted}</div>
                </div>

                <div className="rounded-lg border border-border bg-bg p-3">
                  <span className="text-[10px] uppercase text-text-muted">Land Classification</span>
                  <div className="mt-1 text-xs font-bold text-white">{report.base_record.land_type}</div>
                </div>

                <div className="rounded-lg border border-border bg-bg p-3">
                  <span className="text-[10px] uppercase text-text-muted">Document Reference</span>
                  <div className="mt-1 text-xs font-mono text-blue-400">{report.base_record.document_reference}</div>
                </div>
              </div>
            </Card>
          )}

          {/* Mutation History Table */}
          {report.mutation_history?.length > 0 && (
            <Card className="p-6 space-y-4 border-border bg-surface">
              <div className="flex items-center gap-2 border-b border-border pb-3">
                <Clock size={16} className="text-primary" />
                <h4 className="font-semibold text-white text-sm">Official Mutation Register (MR) History</h4>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-border text-text-muted">
                      <th className="pb-2">Date</th>
                      <th className="pb-2">Transaction Type</th>
                      <th className="pb-2">From Transferor</th>
                      <th className="pb-2">To Transferee</th>
                      <th className="pb-2">Doc Reference</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {report.mutation_history.map((m: any, idx: number) => (
                      <tr key={idx} className="hover:bg-white/[0.02]">
                        <td className="py-2.5 font-mono text-text-secondary">{m.date}</td>
                        <td className="py-2.5 font-semibold text-white">{m.type}</td>
                        <td className="py-2.5 text-text-secondary">{m.from}</td>
                        <td className="py-2.5 text-text-secondary">{m.to}</td>
                        <td className="py-2.5 font-mono text-blue-400">{m.doc_ref}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* Encumbrance Certificate Table */}
          {report.encumbrances && (
            <Card className="p-6 space-y-4 border-border bg-surface">
              <div className="flex items-center gap-2 border-b border-border pb-3">
                <Landmark size={16} className="text-amber-400" />
                <h4 className="font-semibold text-white text-sm">30-Year Encumbrance Register (EC)</h4>
              </div>

              {report.encumbrances.length === 0 ? (
                <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 text-center text-xs text-emerald-400 font-medium">
                  Nil Encumbrance: No active registered mortgages, charges, or liens reported for search period.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-border text-text-muted">
                        <th className="pb-2">Charge Type</th>
                        <th className="pb-2">Lender / Institution</th>
                        <th className="pb-2">Secured Amount</th>
                        <th className="pb-2">Date Registered</th>
                        <th className="pb-2">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/60">
                      {report.encumbrances.map((e: any, idx: number) => (
                        <tr key={idx} className="hover:bg-white/[0.02]">
                          <td className="py-2.5 font-semibold text-white">{e.type}</td>
                          <td className="py-2.5 text-text-secondary">{e.bank || e.party}</td>
                          <td className="py-2.5 font-mono text-emerald-400">Rs. {e.amount}</td>
                          <td className="py-2.5 font-mono text-text-muted">{e.date}</td>
                          <td className="py-2.5">
                            <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-semibold text-amber-400">
                              {e.status || "Active"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
