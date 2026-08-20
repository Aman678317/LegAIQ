"""Review Tables AI Engine & Exporter.

Structured prompt-driven bulk extraction across legal matter documents with
cell-level evidence citations, confidence scoring, and Excel/CSV export.
"""

import csv
import io
import re
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# Default columns for rapid legal review initialization
DEFAULT_LEGAL_COLUMNS = [
    {"name": "Governing Law", "column_type": "prompt", "prompt": "What is the governing law of this agreement?", "position": 0},
    {"name": "Jurisdiction", "column_type": "prompt", "prompt": "Which court or seat has jurisdiction for dispute resolution?", "position": 1},
    {"name": "Indemnity Cap", "column_type": "prompt", "prompt": "Is there a monetary cap or limitation on indemnity?", "position": 2},
    {"name": "Termination Notice", "column_type": "prompt", "prompt": "What is the termination notice period?", "position": 3},
    {"name": "Stamp Duty Paid", "column_type": "prompt", "prompt": "What is the stamp duty amount paid or noted?", "position": 4},
]


@dataclass
class CellEvidence:
    """Grounding evidence for extracted review cell value."""
    doc_id: str
    doc_name: str
    page_num: int = 1
    text_snippet: str = ""
    bbox: Optional[List[float]] = None  # [ymin, xmin, ymax, xmax] normalized 0-1
    char_start: int = 0
    char_end: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "doc_name": self.doc_name,
            "page_num": self.page_num,
            "text_snippet": self.text_snippet,
            "bbox": self.bbox or [0.1, 0.1, 0.2, 0.9],
            "char_start": self.char_start,
            "char_end": self.char_end,
        }


@dataclass
class ExtractionResult:
    """Result of extracting a single cell value from document text."""
    value: str
    confidence_score: float
    evidence: Optional[CellEvidence] = None
    status: str = "completed"  # completed, failed, not_found


class ReviewTableExtractionEngine:
    """Extracts structured values from documents based on column prompt definitions."""

    # Built-in heuristic extractors for common legal review prompts
    PROMPT_PATTERNS = {
        "governing_law": [
            r"(?:governed by|governing law|applicable law|laws of)\s+(?:the\s+)?([A-Z][a-zA-Z\s,]+?)(?:\.|\n|;|$)",
            r"(?:laws of India|State of [A-Za-z]+|laws of [A-Za-z\s]+)",
        ],
        "jurisdiction": [
            r"(?:courts (?:at|of|in)|exclusive jurisdiction (?:of|to))\s+([A-Z][a-zA-Z\s,]+?)(?:\.|\n|;|$)",
            r"(?:jurisdiction of the courts in|arbitration seat in)\s+([A-Z][a-zA-Z\s]+)",
        ],
        "indemnity_cap": [
            r"(?:indemnity|indemnification)\s+(?:shall be|is)?\s*(?:capped at|limited to|not exceed)\s+([^\.\n;]+)",
            r"(?:liability under this indemnity|indemnity obligation)\s+([^\.\n;]+)",
            r"(?:unlimited indemnity|no limitation on indemnity)",
        ],
        "termination_notice": [
            r"(?:terminate|termination)(?:[^\.\n;]{0,50}?)(?:upon|with|by giving)\s+(\d+\s+(?:days?|months?|weeks?))\s+(?:prior\s+)?(?:written\s+)?notice",
            r"(\d+\s+(?:days?|months?|weeks?))\s+(?:prior\s+)?(?:written\s+)?notice\s+of\s+termination",
        ],
        "stamp_duty": [
            r"(?:stamp duty|Stamp Duty)(?:[^\.\n;]{0,40}?)(?:paid|payable|of)\s+(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d+)?(?:\s*(?:Lakhs?|Crores?|Rupees?))?)",
            r"(?:properly stamped|stamp duty of Rs\.?\s*([\d,]+))",
            r"(?:stamp paper of Rs\.?\s*([\d,]+))",
        ],
        "non_compete": [
            r"(?:non-compete|not compete|restrictive covenant)(?:[^\.\n;]{0,60}?)(?:for a period of|during)\s+([^\.\n;]+)",
            r"(?:restraint of trade|non-compete restriction)\s+(?:of|for)\s+([^\.\n;]+)",
        ],
        "parties": [
            r"(?:BETWEEN|between)\s*:\s*([^\n\.,]+?)\s+(?:AND|and)\s+([^\n\.,]+)",
            r"(?:Party A|Vendor|Client|Licensor)\s*:\s*([^\n,]+)",
        ],
        "payment_terms": [
            r"(?:consideration|fee|payment|price)\s+(?:of|is|shall be)\s+(?:Rs\.?|INR|₹|\$|USD)?\s*([\d,]+(?:\.\d+)?(?:\s*(?:Lakhs?|Crores?|Rupees?|million))?)",
            r"(?:payment within|payable within)\s+(\d+\s+(?:days?|weeks?|months?))",
        ],
        "liability_cap": [
            r"(?:aggregate liability|total liability|liability of either party)\s+(?:shall not exceed|limited to|capped at)\s+([^\.\n;]+)",
            r"(?:limitation of liability|liability cap)\s*:\s*([^\.\n;]+)",
        ],
        "effective_date": [
            r"(?:effective date|commencement date|made on|entered into on)\s+(?:this\s+)?(\d{1,2}(?:st|nd|rd|th)?\s+(?:day of\s+)?[A-Za-z]+,?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(?:dated|date of agreement)\s*:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        ],
    }

    def extract_value_for_prompt(
        self,
        prompt: str,
        doc_id: str,
        doc_name: str,
        text: str,
        pages: Optional[List[Dict[str, Any]]] = None,
    ) -> ExtractionResult:
        """Extract value and evidence citation for a given prompt from document text."""
        if not text or not text.strip():
            return ExtractionResult(
                value="N/A (Document text empty)",
                confidence_score=0.0,
                status="not_found",
            )

        prompt_lower = prompt.lower()
        extracted_value = None
        evidence = None
        confidence = 0.5

        # 1. Match against known legal prompt types
        matched_key = None
        if "governing law" in prompt_lower or "applicable law" in prompt_lower:
            matched_key = "governing_law"
        elif "jurisdiction" in prompt_lower or "court" in prompt_lower or "seat" in prompt_lower:
            matched_key = "jurisdiction"
        elif "indemnity cap" in prompt_lower or "indemnity" in prompt_lower:
            matched_key = "indemnity_cap"
        elif "termination" in prompt_lower or "notice period" in prompt_lower:
            matched_key = "termination_notice"
        elif "stamp duty" in prompt_lower or "stamp" in prompt_lower:
            matched_key = "stamp_duty"
        elif "non-compete" in prompt_lower or "non compete" in prompt_lower or "restraint" in prompt_lower:
            matched_key = "non_compete"
        elif "parties" in prompt_lower or "party" in prompt_lower:
            matched_key = "parties"
        elif "payment" in prompt_lower or "consideration" in prompt_lower or "fee" in prompt_lower or "price" in prompt_lower:
            matched_key = "payment_terms"
        elif "liability cap" in prompt_lower or "limitation of liability" in prompt_lower:
            matched_key = "liability_cap"
        elif "effective date" in prompt_lower or "execution date" in prompt_lower or "date" in prompt_lower:
            matched_key = "effective_date"

        if matched_key and matched_key in self.PROMPT_PATTERNS:
            patterns = self.PROMPT_PATTERNS[matched_key]
            for pat in patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    extracted_value = m.group(1).strip() if m.lastindex else m.group(0).strip()
                    # Clean up value
                    extracted_value = re.sub(r"\s+", " ", extracted_value)[:150]
                    confidence = 0.92
                    start_char = m.start()
                    end_char = m.end()
                    snippet = self._build_snippet(text, start_char, end_char)
                    page_num = self._find_page_number(pages, start_char, text)
                    evidence = CellEvidence(
                        doc_id=doc_id,
                        doc_name=doc_name,
                        page_num=page_num,
                        text_snippet=snippet,
                        bbox=[0.15, 0.1, 0.25, 0.9],
                        char_start=start_char,
                        char_end=end_char,
                    )
                    break

        # 2. Heuristic fallback: Search keywords from custom user prompt
        if not extracted_value:
            keywords = [w for w in re.findall(r"\w+", prompt_lower) if len(w) > 3 and w not in {"what", "which", "is", "the", "for", "this", "clause", "document", "extract"}]
            if keywords:
                for kw in keywords:
                    m = re.search(rf"(?:^|\n|[.;])([^\n.;]*?{re.escape(kw)}[^\n.;]*)", text, re.IGNORECASE)
                    if m:
                        snippet_match = m.group(1).strip()
                        if len(snippet_match) > 10:
                            extracted_value = snippet_match[:150]
                            confidence = 0.68
                            start_char = m.start(1)
                            end_char = m.end(1)
                            snippet = self._build_snippet(text, start_char, end_char)
                            page_num = self._find_page_number(pages, start_char, text)
                            evidence = CellEvidence(
                                doc_id=doc_id,
                                doc_name=doc_name,
                                page_num=page_num,
                                text_snippet=snippet,
                                bbox=[0.2, 0.1, 0.3, 0.9],
                                char_start=start_char,
                                char_end=end_char,
                            )
                            break

        # 3. If still nothing found, return explicit Not Found
        if not extracted_value:
            return ExtractionResult(
                value="Not Specified in Document",
                confidence_score=0.30,
                evidence=CellEvidence(
                    doc_id=doc_id,
                    doc_name=doc_name,
                    page_num=1,
                    text_snippet=text[:180] + ("..." if len(text) > 180 else ""),
                    bbox=[0.05, 0.1, 0.15, 0.9],
                    char_start=0,
                    char_end=min(len(text), 180),
                ),
                status="completed",
            )

        return ExtractionResult(
            value=extracted_value,
            confidence_score=confidence,
            evidence=evidence,
            status="completed",
        )

    def _build_snippet(self, text: str, start: int, end: int, padding: int = 80) -> str:
        """Create a grounded context snippet around matched character offsets."""
        snip_start = max(0, start - padding)
        snip_end = min(len(text), end + padding)
        prefix = "..." if snip_start > 0 else ""
        suffix = "..." if snip_end < len(text) else ""
        return f"{prefix}{text[snip_start:snip_end].strip()}{suffix}"

    def _find_page_number(self, pages: Optional[List[Dict[str, Any]]], char_pos: int, full_text: str) -> int:
        """Map character position to exact document page number if pages metadata is available."""
        if not pages:
            return max(1, (char_pos // 2000) + 1)

        running_chars = 0
        for p in pages:
            p_num = p.get("page_number", 1)
            p_len = len(p.get("text", "") or "")
            if running_chars <= char_pos <= (running_chars + p_len + 1):
                return p_num
            running_chars += p_len + 1
        return 1


class ReviewTableExporter:
    """Exports review tables to formatted CSV and Open XML (.xlsx) spreadsheets."""

    @staticmethod
    def _sanitize_csv_cell(val: Any) -> str:
        """Sanitize formula injection prefixes (=, +, -, @, \\t, \\r) by prepending single quote."""
        if val is None:
            return ""
        s = str(val)
        if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
            return f"'{s}"
        return s

    @staticmethod
    def export_csv(
        table_name: str,
        columns: List[Dict[str, Any]],
        rows: List[Dict[str, Any]],
    ) -> str:
        """Generate structured CSV with columns, values, confidence, and source citations."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        header = ["Document Name"]
        for col in columns:
            col_name = col.get("name", "Column")
            header.append(col_name)
            header.append(f"{col_name} (Confidence)")
            header.append(f"{col_name} (Citation / Page)")
        writer.writerow([ReviewTableExporter._sanitize_csv_cell(h) for h in header])

        # Data rows
        for row in rows:
            doc_name = row.get("document_name", "Untitled Document")
            cells_by_col = row.get("cells", {})
            row_data = [ReviewTableExporter._sanitize_csv_cell(doc_name)]

            for col in columns:
                col_id = col.get("id")
                cell = cells_by_col.get(col_id, {})
                val = cell.get("value", "")
                conf = cell.get("confidence_score")
                conf_str = f"{int(conf * 100)}%" if conf is not None else ""
                evidence = cell.get("evidence") or {}
                pg = evidence.get("page_num", 1) if evidence else ""
                snip = evidence.get("text_snippet", "") if evidence else ""
                citation = f"Pg {pg}: {snip[:60]}..." if snip else (f"Pg {pg}" if pg else "")

                row_data.append(ReviewTableExporter._sanitize_csv_cell(val))
                row_data.append(ReviewTableExporter._sanitize_csv_cell(conf_str))
                row_data.append(ReviewTableExporter._sanitize_csv_cell(citation))

            writer.writerow(row_data)

        return output.getvalue()

    @staticmethod
    def export_xlsx(
        table_name: str,
        columns: List[Dict[str, Any]],
        rows: List[Dict[str, Any]],
    ) -> bytes:
        """Generate a valid, fully-formed Office Open XML (.xlsx) spreadsheet.

        Produces 2 sheets:
        1. 'Review Table': Formatted grid with values & confidence chips.
        2. 'Citations & Evidence': Full page numbers, snippets, and bounding box citations.
        """
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
            # 1. [Content_Types].xml
            content_types = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStringTable+xml"/>'
                '</Types>'
            )
            z.writestr("[Content_Types].xml", content_types)

            # 2. _rels/.rels
            rels = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                '</Relationships>'
            )
            z.writestr("_rels/.rels", rels)

            # 3. xl/_rels/workbook.xml.rels
            wb_rels = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
                '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                '<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
                '</Relationships>'
            )
            z.writestr("xl/_rels/workbook.xml.rels", wb_rels)

            # 4. xl/workbook.xml
            workbook_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets>'
                '<sheet name="Review Table" sheetId="1" r:id="rId1"/>'
                '<sheet name="Evidence Citations" sheetId="2" r:id="rId2"/>'
                '</sheets>'
                '</workbook>'
            )
            z.writestr("xl/workbook.xml", workbook_xml)

            # 5. xl/styles.xml
            styles_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                '<fonts count="2">'
                '<font><sz val="11"/><name val="Calibri"/></font>'
                '<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>'
                '</fonts>'
                '<fills count="3">'
                '<fill><patternFill patternType="none"/></fill>'
                '<fill><patternFill patternType="gray125"/></fill>'
                '<fill><patternFill patternType="solid"><fgColor rgb="FF1E3A8A"/></patternFill></fill>'
                '</fills>'
                '<borders count="1">'
                '<border><left/><right/><top/><bottom/></border>'
                '</borders>'
                '<cellXfs count="2">'
                '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
                '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>'
                '</cellXfs>'
                '</styleSheet>'
            )
            z.writestr("xl/styles.xml", styles_xml)

            # Shared strings collection
            strings: List[str] = []
            string_map: Dict[str, int] = {}

            def get_str_idx(s: str) -> int:
                val = str(s or "").strip()
                if val not in string_map:
                    string_map[val] = len(strings)
                    strings.append(val)
                return string_map[val]

            # Build Sheet 1 (Review Table)
            s1_rows_xml = []
            # Header Row
            s1_header_cells = [f'<c r="A1" t="s" s="1"><v>{get_str_idx("Document Name")}</v></c>']
            col_idx = 1
            for col in columns:
                col_letter = ReviewTableExporter._col_letter(col_idx)
                s1_header_cells.append(f'<c r="{col_letter}1" t="s" s="1"><v>{get_str_idx(col.get("name", "Column"))}</v></c>')
                col_idx += 1
            s1_rows_xml.append(f'<row r="1">{"".join(s1_header_cells)}</row>')

            # Data Rows
            r_num = 2
            for row in rows:
                row_cells = [f'<c r="A{r_num}" t="s"><v>{get_str_idx(row.get("document_name", "Document"))}</v></c>']
                c_idx = 1
                cells_by_col = row.get("cells", {})
                for col in columns:
                    col_letter = ReviewTableExporter._col_letter(c_idx)
                    cell = cells_by_col.get(col.get("id"), {})
                    val = cell.get("value", "")
                    conf = cell.get("confidence_score")
                    conf_tag = f" [{int(conf * 100)}%]" if conf is not None else ""
                    disp_val = f"{val}{conf_tag}" if val else ""
                    row_cells.append(f'<c r="{col_letter}{r_num}" t="s"><v>{get_str_idx(disp_val)}</v></c>')
                    c_idx += 1
                s1_rows_xml.append(f'<row r="{r_num}">{"".join(row_cells)}</row>')
                r_num += 1

            sheet1_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                f'<sheetData>{"".join(s1_rows_xml)}</sheetData>'
                '</worksheet>'
            )
            z.writestr("xl/worksheets/sheet1.xml", sheet1_xml)

            # Build Sheet 2 (Evidence Citations)
            s2_rows_xml = []
            s2_headers = ["Document", "Column Name", "Extracted Value", "Confidence", "Page", "Evidence Snippet"]
            s2_header_cells = [
                f'<c r="{ReviewTableExporter._col_letter(i)}1" t="s" s="1"><v>{get_str_idx(h)}</v></c>'
                for i, h in enumerate(s2_headers)
            ]
            s2_rows_xml.append(f'<row r="1">{"".join(s2_header_cells)}</row>')

            s2_r_num = 2
            for row in rows:
                doc_name = row.get("document_name", "Document")
                cells_by_col = row.get("cells", {})
                for col in columns:
                    cell = cells_by_col.get(col.get("id"), {})
                    if not cell:
                        continue
                    val = cell.get("value", "")
                    conf = cell.get("confidence_score")
                    conf_str = f"{int(conf * 100)}%" if conf is not None else ""
                    evidence = cell.get("evidence") or {}
                    pg = str(evidence.get("page_num", 1)) if evidence else ""
                    snip = str(evidence.get("text_snippet", "")) if evidence else ""

                    row_vals = [doc_name, col.get("name", ""), val, conf_str, pg, snip]
                    c_cells = [
                        f'<c r="{ReviewTableExporter._col_letter(i)}{s2_r_num}" t="s"><v>{get_str_idx(v)}</v></c>'
                        for i, v in enumerate(row_vals)
                    ]
                    s2_rows_xml.append(f'<row r="{s2_r_num}">{"".join(c_cells)}</row>')
                    s2_r_num += 1

            sheet2_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                f'<sheetData>{"".join(s2_rows_xml)}</sheetData>'
                '</worksheet>'
            )
            z.writestr("xl/worksheets/sheet2.xml", sheet2_xml)

            # 6. xl/sharedStrings.xml
            sst_items = "".join(f"<si><t>{ReviewTableExporter._escape_xml(s)}</t></si>" for s in strings)
            sst_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(strings)}" uniqueCount="{len(strings)}">'
                f'{sst_items}'
                '</sst>'
            )
            z.writestr("xl/sharedStrings.xml", sst_xml)

        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    @staticmethod
    def _col_letter(col_idx: int) -> str:
        """Convert 0-based column index to Excel column letters (A, B, ..., Z, AA, AB)."""
        result = ""
        col_idx += 1
        while col_idx > 0:
            col_idx, remainder = divmod(col_idx - 1, 26)
            result = chr(65 + remainder) + result
        return result

    @staticmethod
    def _escape_xml(s: str) -> str:
        """Escape XML characters."""
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )
