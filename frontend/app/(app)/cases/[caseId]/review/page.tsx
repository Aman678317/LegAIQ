"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  Table as TableIcon, Plus, Sparkles, Download, FileSpreadsheet,
  FileText, CheckCircle2, AlertTriangle, HelpCircle, Loader2,
  Trash2, Edit2, ExternalLink, X, RefreshCw, ChevronDown, Layers
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Column {
  id: string;
  name: string;
  column_type: string;
  prompt: string;
  model?: string;
  position: number;
}

interface CellData {
  id?: string;
  value: string;
  confidence_score?: number;
  status?: string;
  evidence?: {
    doc_id: string;
    doc_name: string;
    page_num: number;
    text_snippet: string;
    bbox?: number[];
  };
}

interface RowData {
  document_id: string;
  document_name: string;
  document_type?: string;
  status?: string;
  cells: Record<string, CellData>;
}

interface ReviewTable {
  id: string;
  name: string;
  description: string;
  columns: Column[];
  rows: RowData[];
  total_documents: number;
}

const PRESET_COLUMNS = [
  { name: "Governing Law", prompt: "What is the substantive governing law of this agreement?" },
  { name: "Jurisdiction & Seat", prompt: "Which court or seat has exclusive dispute resolution jurisdiction?" },
  { name: "Indemnity Cap", prompt: "Is indemnity liability capped? What is the monetary limitation?" },
  { name: "Termination Notice", prompt: "What is the required termination notice period in days or months?" },
  { name: "Stamp Duty Paid", prompt: "What is the stamp duty amount paid or noted on this instrument?" },
  { name: "Non-Compete Term", prompt: "What is the duration of any non-compete or restraint of trade restriction?" },
  { name: "Payment Terms", prompt: "What is the total consideration, fee amount, or payment schedule?" },
];

export default function ReviewTablesPage() {
  const params = useParams();
  const caseId = params.caseId as string;

  const [tablesList, setTablesList] = useState<any[]>([]);
  const [activeTableId, setActiveTableId] = useState<string>("");
  const [table, setTable] = useState<ReviewTable | null>(null);
  const [loading, setLoading] = useState(true);
  const [extracting, setExtracting] = useState(false);

  // Modals & Popovers
  const [showAddColModal, setShowAddColModal] = useState(false);
  const [showNewTableModal, setShowNewTableModal] = useState(false);
  const [selectedCellEvidence, setSelectedCellEvidence] = useState<{ colName: string; cell: CellData } | null>(null);

  // Form states
  const [newColName, setNewColName] = useState("");
  const [newColPrompt, setNewColPrompt] = useState("");
  const [newTableName, setNewTableName] = useState("");
  const [newTableDesc, setNewTableDesc] = useState("");
  const [editingCellKey, setEditingCellKey] = useState<string | null>(null);
  const [editingCellValue, setEditingCellValue] = useState("");

  useEffect(() => {
    loadTables();
  }, [caseId]);

  useEffect(() => {
    if (activeTableId) {
      loadActiveTable(activeTableId);
    }
  }, [activeTableId]);

  async function loadTables() {
    setLoading(true);
    try {
      const res = await api.listReviewTables(caseId);
      const items = res?.items || [];
      setTablesList(items);
      if (items.length > 0) {
        setActiveTableId(items[0].id);
      } else {
        setLoading(false);
      }
    } catch {
      setLoading(false);
    }
  }

  async function loadActiveTable(tableId: string) {
    try {
      const data = await api.getReviewTable(caseId, tableId);
      setTable(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateNewTable() {
    if (!newTableName.trim()) return;
    try {
      const created = await api.createReviewTable(caseId, {
        name: newTableName.trim(),
        description: newTableDesc.trim(),
      });
      setShowNewTableModal(false);
      setNewTableName("");
      setNewTableDesc("");
      await loadTables();
      if (created?.id) {
        setActiveTableId(created.id);
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function handleAddColumn() {
    if (!newColName.trim() || !activeTableId) return;
    try {
      await api.addReviewColumn(caseId, activeTableId, {
        name: newColName.trim(),
        prompt: newColPrompt.trim() || newColName.trim(),
        position: table?.columns.length || 0,
      });
      setShowAddColModal(false);
      setNewColName("");
      setNewColPrompt("");
      loadActiveTable(activeTableId);
    } catch (err) {
      console.error(err);
    }
  }

  async function handleDeleteColumn(colId: string) {
    if (!activeTableId || !confirm("Are you sure you want to delete this column?")) return;
    try {
      await api.deleteReviewColumn(caseId, activeTableId, colId);
      loadActiveTable(activeTableId);
    } catch (err) {
      console.error(err);
    }
  }

  async function handleRunExtraction() {
    if (!activeTableId) return;
    setExtracting(true);
    try {
      await api.extractReviewTable(caseId, activeTableId);
      await loadActiveTable(activeTableId);
    } catch (err) {
      console.error(err);
    } finally {
      setExtracting(false);
    }
  }

  async function handleSaveCellEdit(docId: string, colId: string, cellId?: string) {
    if (!activeTableId) return;
    try {
      if (cellId) {
        await api.updateReviewCell(caseId, activeTableId, cellId, {
          value: editingCellValue,
          confidence_score: 1.0,
        });
      }
      setEditingCellKey(null);
      loadActiveTable(activeTableId);
    } catch (err) {
      console.error(err);
    }
  }

  function renderConfidenceChip(score?: number) {
    if (score === undefined || score === null) return null;
    const pct = Math.round(score * 100);
    if (pct >= 85) {
      return (
        <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 size={10} />
          {pct}%
        </span>
      );
    }
    if (pct >= 60) {
      return (
        <span className="inline-flex items-center gap-1 rounded bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-amber-300 border border-amber-500/20">
          <AlertTriangle size={10} />
          {pct}%
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 rounded bg-red-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-red-400 border border-red-500/20">
        <HelpCircle size={10} />
        {pct}%
      </span>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/10 text-primary border border-blue-500/20">
              <TableIcon size={20} />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Spreadsheet Review Tables</h1>
              <p className="text-xs text-text-secondary">
                Harvey-class prompt-driven bulk extraction across all matter documents with evidence citations
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Table Switcher */}
          {tablesList.length > 0 && (
            <div className="relative">
              <select
                value={activeTableId}
                onChange={(e) => setActiveTableId(e.target.value)}
                className="rounded-lg border border-border bg-bg-surface px-3 py-2 text-xs font-medium text-text-primary focus:border-primary focus:outline-none"
              >
                {tablesList.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.column_count || 0} cols)
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={() => setShowNewTableModal(true)}
            className="flex items-center gap-1.5 rounded-lg border border-border bg-bg-surface px-3 py-2 text-xs font-medium text-text-secondary hover:bg-bg-elevated hover:text-white"
          >
            <Plus size={14} />
            New Table
          </button>

          <button
            onClick={handleRunExtraction}
            disabled={extracting || !table}
            className="flex items-center gap-1.5 rounded-lg bg-primary px-3.5 py-2 text-xs font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {extracting ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
            {extracting ? "Extracting..." : "Run AI Extraction"}
          </button>

          {/* Export Actions */}
          {table && (
            <div className="flex items-center gap-1">
              <a
                href={api.getReviewTableExportUrl(caseId, activeTableId, "xlsx")}
                download
                className="flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs font-medium text-emerald-300 hover:bg-emerald-500/20"
              >
                <FileSpreadsheet size={14} />
                Excel (.xlsx)
              </a>
              <a
                href={api.getReviewTableExportUrl(caseId, activeTableId, "csv")}
                download
                className="flex items-center gap-1.5 rounded-lg border border-border bg-bg-surface px-3 py-2 text-xs font-medium text-text-secondary hover:bg-bg-elevated hover:text-white"
              >
                <Download size={14} />
                CSV
              </a>
            </div>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center rounded-xl border border-border bg-bg-surface">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      ) : !table ? (
        <div className="flex h-64 flex-col items-center justify-center rounded-xl border border-dashed border-border bg-bg-surface p-6 text-center">
          <Layers className="h-10 w-10 text-text-muted mb-3" />
          <h3 className="text-sm font-semibold text-white">No Review Tables Created</h3>
          <p className="text-xs text-text-secondary max-w-sm mt-1 mb-4">
            Create your first structured review table to extract governing laws, indemnity caps, and custom prompts.
          </p>
          <button
            onClick={() => setShowNewTableModal(true)}
            className="flex items-center gap-1.5 rounded-lg bg-primary px-3.5 py-2 text-xs font-semibold text-white hover:opacity-90"
          >
            <Plus size={14} />
            Create Review Table
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Table Meta Bar */}
          <div className="flex items-center justify-between rounded-lg border border-border bg-bg-surface/60 px-4 py-2.5">
            <div>
              <span className="text-xs font-semibold text-white">{table.name}</span>
              {table.description && (
                <span className="ml-2 text-xs text-text-muted">— {table.description}</span>
              )}
            </div>
            <div className="flex items-center gap-3 text-xs text-text-muted">
              <span>{table.rows?.length || 0} Documents</span>
              <span>•</span>
              <span>{table.columns?.length || 0} Extraction Columns</span>
              <button
                onClick={() => setShowAddColModal(true)}
                className="flex items-center gap-1 font-medium text-primary hover:underline ml-2"
              >
                <Plus size={13} />
                Add Column
              </button>
            </div>
          </div>

          {/* Interactive Spreadsheet Grid */}
          <div className="overflow-x-auto rounded-xl border border-border bg-bg-surface shadow-xl">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-border bg-bg-elevated/80 text-text-secondary sticky top-0 z-20">
                  <th className="px-4 py-3 font-semibold uppercase tracking-wider text-[11px] w-64 min-w-[200px] border-r border-border bg-bg-elevated/95 sticky left-0 z-30">
                    Matter Document
                  </th>
                  {table.columns.map((col) => (
                    <th
                      key={col.id}
                      className="px-4 py-3 font-semibold uppercase tracking-wider text-[11px] min-w-[240px] max-w-[320px] border-r border-border group"
                    >
                      <div className="flex items-center justify-between">
                        <span className="truncate text-white" title={col.prompt}>
                          {col.name}
                        </span>
                        <button
                          onClick={() => handleDeleteColumn(col.id)}
                          className="opacity-0 group-hover:opacity-100 text-text-muted hover:text-red-400 transition-opacity p-0.5"
                          title="Delete column"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                      <div className="text-[10px] text-text-muted truncate lowercase font-normal mt-0.5">
                        {col.prompt}
                      </div>
                    </th>
                  ))}
                  <th className="px-3 py-3 w-16 text-center">
                    <button
                      onClick={() => setShowAddColModal(true)}
                      className="flex items-center justify-center h-6 w-6 rounded bg-primary/10 text-primary hover:bg-primary/20 transition-colors mx-auto"
                      title="Add column"
                    >
                      <Plus size={14} />
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border text-text-primary">
                {table.rows.map((row) => (
                  <tr key={row.document_id} className="hover:bg-bg-elevated/40 transition-colors">
                    {/* Document Header Cell (Sticky) */}
                    <td className="px-4 py-3 font-medium text-white border-r border-border bg-bg-surface sticky left-0 z-10">
                      <div className="flex items-center gap-2">
                        <FileText size={15} className="text-primary shrink-0" />
                        <div className="truncate">
                          <div className="truncate font-medium">{row.document_name}</div>
                          <div className="text-[10px] text-text-muted uppercase">
                            {row.document_type || "DOCUMENT"}
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Extraction Prompt Cells */}
                    {table.columns.map((col) => {
                      const cell = row.cells?.[col.id] || { value: "" };
                      const cellKey = `${row.document_id}-${col.id}`;
                      const isEditing = editingCellKey === cellKey;

                      return (
                        <td
                          key={col.id}
                          className="px-4 py-2.5 border-r border-border align-top relative group"
                        >
                          {isEditing ? (
                            <div className="flex flex-col gap-1.5">
                              <textarea
                                value={editingCellValue}
                                onChange={(e) => setEditingCellValue(e.target.value)}
                                className="w-full rounded border border-primary bg-bg-surface p-1.5 text-xs text-white focus:outline-none min-h-[60px]"
                                autoFocus
                              />
                              <div className="flex items-center gap-1 justify-end">
                                <button
                                  onClick={() => setEditingCellKey(null)}
                                  className="rounded px-2 py-0.5 text-[10px] text-text-muted hover:text-white"
                                >
                                  Cancel
                                </button>
                                <button
                                  onClick={() => handleSaveCellEdit(row.document_id, col.id, cell.id)}
                                  className="rounded bg-primary px-2 py-0.5 text-[10px] font-medium text-white"
                                >
                                  Save
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div className="flex flex-col gap-1">
                              <div className="flex items-start justify-between gap-1.5">
                                <span className="text-xs text-slate-200 leading-relaxed break-words">
                                  {cell.value || (
                                    <span className="italic text-text-muted">Not extracted</span>
                                  )}
                                </span>
                                <button
                                  onClick={() => {
                                    setEditingCellKey(cellKey);
                                    setEditingCellValue(cell.value || "");
                                  }}
                                  className="opacity-0 group-hover:opacity-100 text-text-muted hover:text-white transition-opacity p-0.5 shrink-0"
                                  title="Edit cell"
                                >
                                  <Edit2 size={11} />
                                </button>
                              </div>

                              <div className="flex items-center justify-between mt-1 pt-1 border-t border-border/40">
                                <div>{renderConfidenceChip(cell.confidence_score)}</div>
                                {cell.evidence && (
                                  <button
                                    onClick={() => setSelectedCellEvidence({ colName: col.name, cell })}
                                    className="flex items-center gap-1 text-[10px] text-primary hover:text-blue-300 transition-colors"
                                  >
                                    <span>Pg {cell.evidence.page_num}</span>
                                    <ExternalLink size={10} />
                                  </button>
                                )}
                              </div>
                            </div>
                          )}
                        </td>
                      );
                    })}

                    <td className="px-3 py-2.5"></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Cell Evidence Popover Modal */}
      {selectedCellEvidence && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl border border-border bg-bg-surface p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded bg-primary/10 text-primary">
                  <FileText size={15} />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Source Evidence Citation</h3>
                  <p className="text-[11px] text-text-muted">{selectedCellEvidence.colName}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedCellEvidence(null)}
                className="text-text-muted hover:text-white"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-lg bg-bg-elevated p-3 text-xs">
                <div>
                  <span className="text-text-muted">Document:</span>{" "}
                  <span className="font-semibold text-white">{selectedCellEvidence.cell.evidence?.doc_name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded bg-primary/15 px-2 py-0.5 font-medium text-blue-300">
                    Page {selectedCellEvidence.cell.evidence?.page_num || 1}
                  </span>
                  {renderConfidenceChip(selectedCellEvidence.cell.confidence_score)}
                </div>
              </div>

              <div>
                <label className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                  Extracted Value
                </label>
                <div className="mt-1 rounded-lg border border-border bg-bg-elevated/60 p-3 text-xs font-medium text-emerald-300">
                  {selectedCellEvidence.cell.value}
                </div>
              </div>

              <div>
                <label className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                  Grounding Document Snippet
                </label>
                <div className="mt-1 rounded-lg border border-border bg-bg/80 p-3.5 text-xs text-text-primary leading-relaxed font-mono italic border-l-4 border-l-primary">
                  "{selectedCellEvidence.cell.evidence?.text_snippet}"
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedCellEvidence(null)}
                className="rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white hover:opacity-90"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Column Modal */}
      {showAddColModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-border bg-bg-surface p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-sm font-bold text-white">Add Dynamic Extraction Column</h3>
              <button onClick={() => setShowAddColModal(false)} className="text-text-muted hover:text-white">
                <X size={18} />
              </button>
            </div>

            <div className="space-y-3">
              {/* Presets */}
              <div>
                <label className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                  Quick Legal Presets
                </label>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {PRESET_COLUMNS.map((p) => (
                    <button
                      key={p.name}
                      onClick={() => {
                        setNewColName(p.name);
                        setNewColPrompt(p.prompt);
                      }}
                      className="rounded-lg border border-border bg-bg-elevated px-2.5 py-1 text-[11px] text-text-secondary hover:bg-primary/20 hover:text-white hover:border-primary/40 transition-colors"
                    >
                      {p.name}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-text-secondary">Column Name</label>
                <input
                  type="text"
                  value={newColName}
                  onChange={(e) => setNewColName(e.target.value)}
                  placeholder="e.g. Indemnity Cap, Notice Period"
                  className="mt-1 w-full rounded-lg border border-border bg-bg-elevated px-3 py-2 text-xs text-white placeholder-text-muted focus:border-primary focus:outline-none"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-text-secondary">AI Extraction Prompt</label>
                <textarea
                  value={newColPrompt}
                  onChange={(e) => setNewColPrompt(e.target.value)}
                  placeholder="e.g. What is the monetary limitation on indemnity?"
                  className="mt-1 w-full rounded-lg border border-border bg-bg-elevated px-3 py-2 text-xs text-white placeholder-text-muted focus:border-primary focus:outline-none min-h-[70px]"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowAddColModal(false)}
                className="rounded-lg px-4 py-2 text-xs font-medium text-text-secondary hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleAddColumn}
                disabled={!newColName.trim()}
                className="rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50"
              >
                Add Column
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Table Modal */}
      {showNewTableModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-border bg-bg-surface p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-sm font-bold text-white">Create Review Table</h3>
              <button onClick={() => setShowNewTableModal(false)} className="text-text-muted hover:text-white">
                <X size={18} />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-text-secondary">Table Name</label>
                <input
                  type="text"
                  value={newTableName}
                  onChange={(e) => setNewTableName(e.target.value)}
                  placeholder="e.g. Vendor Agreement Due Diligence"
                  className="mt-1 w-full rounded-lg border border-border bg-bg-elevated px-3 py-2 text-xs text-white placeholder-text-muted focus:border-primary focus:outline-none"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-text-secondary">Description (Optional)</label>
                <textarea
                  value={newTableDesc}
                  onChange={(e) => setNewTableDesc(e.target.value)}
                  placeholder="e.g. Structured extraction for lease clauses and liabilities."
                  className="mt-1 w-full rounded-lg border border-border bg-bg-elevated px-3 py-2 text-xs text-white placeholder-text-muted focus:border-primary focus:outline-none min-h-[60px]"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowNewTableModal(false)}
                className="rounded-lg px-4 py-2 text-xs font-medium text-text-secondary hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateNewTable}
                disabled={!newTableName.trim()}
                className="rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50"
              >
                Create Table
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
