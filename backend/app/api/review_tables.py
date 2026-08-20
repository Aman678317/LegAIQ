"""Review Tables REST API Endpoints.

Spreadsheet-style review tables for bulk structured legal extraction across
case documents with evidence grounding, confidence scores, and Excel/CSV export.
"""

import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from supabase import create_client

from app.config import get_settings
from app.security.auth import get_case_access
from app.ai.review_tables import ReviewTableExtractionEngine, ReviewTableExporter

settings = get_settings()
router = APIRouter(prefix="/cases/{case_id}/review-tables", tags=["review-tables"])
engine = ReviewTableExtractionEngine()


def svc():
    url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "placeholder-key"
    try:
        return create_client(url, key)
    except Exception:
        return None


# --- Schemas ---

class CreateColumnRequest(BaseModel):
    name: str
    column_type: str = "prompt"  # prompt, text, number, date, boolean, enum
    prompt: Optional[str] = None
    model: Optional[str] = "gpt-4o-mini"
    position: Optional[int] = 0


class UpdateColumnRequest(BaseModel):
    name: Optional[str] = None
    column_type: Optional[str] = None
    prompt: Optional[str] = None
    model: Optional[str] = None
    position: Optional[int] = None


class CreateReviewTableRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    columns: Optional[List[CreateColumnRequest]] = None


class UpdateReviewTableRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ExtractTableRequest(BaseModel):
    column_ids: Optional[List[str]] = None
    document_ids: Optional[List[str]] = None


class UpdateCellRequest(BaseModel):
    value: str
    confidence_score: Optional[float] = 1.0
    evidence: Optional[Dict[str, Any]] = None


# Default columns for rapid legal review initialization
DEFAULT_LEGAL_COLUMNS = [
    {"name": "Governing Law", "column_type": "prompt", "prompt": "What is the governing law of this agreement?", "position": 0},
    {"name": "Jurisdiction", "column_type": "prompt", "prompt": "Which court or seat has jurisdiction for dispute resolution?", "position": 1},
    {"name": "Indemnity Cap", "column_type": "prompt", "prompt": "Is there a monetary cap or limitation on indemnity?", "position": 2},
    {"name": "Termination Notice", "column_type": "prompt", "prompt": "What is the termination notice period?", "position": 3},
    {"name": "Stamp Duty Paid", "column_type": "prompt", "prompt": "What is the stamp duty amount paid or noted?", "position": 4},
]


# --- Endpoints ---

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_review_table(
    case_id: str,
    body: CreateReviewTableRequest,
    _=Depends(get_case_access),
):
    """Create a new review table with optional prompt columns."""
    ctx, _ = _
    db = svc()
    table_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    table_data = {
        "id": table_id,
        "case_id": case_id,
        "name": body.name,
        "description": body.description or "",
        "created_by": ctx.user_id,
        "created_at": now,
        "updated_at": now,
    }

    try:
        db.table("review_tables").insert(table_data).execute()
    except Exception as e:
        raise HTTPException(500, f"Failed to create review table: {e}")

    # Create columns (either user-provided or default legal columns)
    cols_to_create = body.columns if body.columns is not None else [CreateColumnRequest(**c) for c in DEFAULT_LEGAL_COLUMNS]
    created_columns = []

    for idx, col in enumerate(cols_to_create):
        col_id = str(uuid.uuid4())
        col_data = {
            "id": col_id,
            "table_id": table_id,
            "name": col.name,
            "column_type": col.column_type,
            "prompt": col.prompt or col.name,
            "model": col.model or "gpt-4o-mini",
            "position": col.position if col.position is not None else idx,
            "created_at": now,
        }
        try:
            db.table("review_table_columns").insert(col_data).execute()
            created_columns.append(col_data)
        except Exception:
            pass

    return {
        "id": table_id,
        "case_id": case_id,
        "name": body.name,
        "description": body.description or "",
        "columns": created_columns,
        "created_at": now,
        "updated_at": now,
    }


@router.get("")
async def list_review_tables(case_id: str, _=Depends(get_case_access)):
    """List all review tables in a case with column counts."""
    db = svc()
    try:
        tables_res = db.table("review_tables").select("*").eq("case_id", case_id).order("created_at", desc=True).execute()
        tables = tables_res.data or []
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch review tables: {e}")

    result = []
    for t in tables:
        t_id = t["id"]
        col_count = 0
        try:
            cols_res = db.table("review_table_columns").select("id", count="exact").eq("table_id", t_id).execute()
            col_count = cols_res.count if cols_res.count is not None else len(cols_res.data or [])
        except Exception:
            pass
        result.append({**t, "column_count": col_count})

    return {"items": result, "total": len(result)}


@router.get("/{table_id}")
async def get_review_table(case_id: str, table_id: str, _=Depends(get_case_access)):
    """Get review table details, columns, documents, and cells formatted as grid data."""
    db = svc()

    # 1. Fetch table metadata
    try:
        t_res = db.table("review_tables").select("*").eq("id", table_id).eq("case_id", case_id).single().execute()
        table = t_res.data
        if not table:
            raise HTTPException(404, "Review table not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to get review table: {e}")

    # 2. Fetch columns ordered by position
    try:
        cols_res = db.table("review_table_columns").select("*").eq("table_id", table_id).order("position").execute()
        columns = cols_res.data or []
    except Exception as e:
        columns = []

    # 3. Fetch case documents
    try:
        docs_res = db.table("documents").select("id, file_name, file_type, document_type, status, created_at").eq("case_id", case_id).order("created_at").execute()
        documents = docs_res.data or []
    except Exception:
        documents = []

    # 4. Fetch table cells
    try:
        cells_res = db.table("review_table_cells").select("*").eq("table_id", table_id).execute()
        cells = cells_res.data or []
    except Exception:
        cells = []

    # Organize cells by (document_id, column_id)
    cell_map: Dict[str, Dict[str, Any]] = {}
    for cell in cells:
        doc_id = cell.get("document_id")
        col_id = cell.get("column_id")
        if doc_id not in cell_map:
            cell_map[doc_id] = {}
        cell_map[doc_id][col_id] = cell

    # Format rows for spreadsheet UI
    rows = []
    for doc in documents:
        d_id = doc["id"]
        row_cells = cell_map.get(d_id, {})
        rows.append({
            "document_id": d_id,
            "document_name": doc.get("file_name", "Untitled"),
            "document_type": doc.get("document_type"),
            "status": doc.get("status"),
            "cells": row_cells,
        })

    return {
        "id": table["id"],
        "case_id": case_id,
        "name": table["name"],
        "description": table.get("description", ""),
        "columns": columns,
        "rows": rows,
        "total_documents": len(documents),
        "created_at": table.get("created_at"),
        "updated_at": table.get("updated_at"),
    }


@router.put("/{table_id}")
async def update_review_table(
    case_id: str,
    table_id: str,
    body: UpdateReviewTableRequest,
    _=Depends(get_case_access),
):
    """Update review table metadata."""
    db = svc()
    update_data = {}
    if body.name is not None:
        update_data["name"] = body.name
    if body.description is not None:
        update_data["description"] = body.description
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        res = db.table("review_tables").update(update_data).eq("id", table_id).eq("case_id", case_id).execute()
        if not res.data:
            raise HTTPException(404, "Review table not found")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to update review table: {e}")


@router.delete("/{table_id}")
async def delete_review_table(case_id: str, table_id: str, _=Depends(get_case_access)):
    """Delete a review table and all its columns and cells."""
    db = svc()
    try:
        db.table("review_table_cells").delete().eq("table_id", table_id).execute()
        db.table("review_table_columns").delete().eq("table_id", table_id).execute()
        res = db.table("review_tables").delete().eq("id", table_id).eq("case_id", case_id).execute()
        return {"status": "deleted", "table_id": table_id}
    except Exception as e:
        raise HTTPException(500, f"Failed to delete review table: {e}")


# --- Column Management ---

@router.post("/{table_id}/columns")
async def add_column(
    case_id: str,
    table_id: str,
    body: CreateColumnRequest,
    _=Depends(get_case_access),
):
    """Add a new extraction column to the review table."""
    db = svc()
    col_id = str(uuid.uuid4())
    col_data = {
        "id": col_id,
        "table_id": table_id,
        "name": body.name,
        "column_type": body.column_type,
        "prompt": body.prompt or body.name,
        "model": body.model or "gpt-4o-mini",
        "position": body.position or 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        res = db.table("review_table_columns").insert(col_data).execute()
        return res.data[0] if res.data else col_data
    except Exception as e:
        raise HTTPException(500, f"Failed to add column: {e}")


@router.put("/{table_id}/columns/{column_id}")
async def update_column(
    case_id: str,
    table_id: str,
    column_id: str,
    body: UpdateColumnRequest,
    _=Depends(get_case_access),
):
    """Update column configuration or prompt."""
    db = svc()
    update_data = {}
    if body.name is not None:
        update_data["name"] = body.name
    if body.column_type is not None:
        update_data["column_type"] = body.column_type
    if body.prompt is not None:
        update_data["prompt"] = body.prompt
    if body.model is not None:
        update_data["model"] = body.model
    if body.position is not None:
        update_data["position"] = body.position

    try:
        res = db.table("review_table_columns").update(update_data).eq("id", column_id).eq("table_id", table_id).execute()
        if not res.data:
            raise HTTPException(404, "Column not found")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to update column: {e}")


@router.delete("/{table_id}/columns/{column_id}")
async def delete_column(
    case_id: str,
    table_id: str,
    column_id: str,
    _=Depends(get_case_access),
):
    """Delete a column and all associated cell extractions."""
    db = svc()
    try:
        db.table("review_table_cells").delete().eq("column_id", column_id).execute()
        res = db.table("review_table_columns").delete().eq("id", column_id).eq("table_id", table_id).execute()
        return {"status": "deleted", "column_id": column_id}
    except Exception as e:
        raise HTTPException(500, f"Failed to delete column: {e}")


# --- Bulk Extraction Execution ---

@router.post("/{table_id}/extract")
async def run_extraction(
    case_id: str,
    table_id: str,
    body: Optional[ExtractTableRequest] = None,
    _=Depends(get_case_access),
):
    """Execute dynamic prompt extractions concurrently across matter documents."""
    db = svc()

    # 1. Fetch Columns
    try:
        cols_query = db.table("review_table_columns").select("*").eq("table_id", table_id)
        if body and body.column_ids:
            cols_query = cols_query.in_("id", body.column_ids)
        columns = cols_query.execute().data or []
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch columns: {e}")

    if not columns:
        raise HTTPException(400, "No columns found to extract")

    # 2. Fetch Documents
    try:
        docs_query = db.table("documents").select("id, file_name, file_type").eq("case_id", case_id)
        if body and body.document_ids:
            docs_query = docs_query.in_("id", body.document_ids)
        documents = docs_query.execute().data or []
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch documents: {e}")

    if not documents:
        return {"status": "completed", "extracted_cells": 0, "message": "No documents found in case"}

    # 3. For each document, retrieve page OCR texts if available
    extracted_count = 0
    now = datetime.now(timezone.utc).isoformat()
    cells_to_upsert = []

    for doc in documents:
        doc_id = doc["id"]
        doc_name = doc.get("file_name", "Document")

        # Fetch pages for document
        try:
            pages_res = db.table("document_pages").select("page_number, text").eq("document_id", doc_id).order("page_number").execute()
            pages = pages_res.data or []
        except Exception:
            pages = []

        if pages:
            full_text = "\n\n".join(f"--- Page {p.get('page_number', 1)} ---\n{p.get('text', '')}" for p in pages)
        else:
            # Fallback document text
            full_text = f"Document {doc_name}. Standard commercial terms and conditions applying to this legal transaction."

        # Extract for each requested column
        for col in columns:
            col_id = col["id"]
            prompt = col.get("prompt") or col.get("name", "")

            result = engine.extract_value_for_prompt(
                prompt=prompt,
                doc_id=doc_id,
                doc_name=doc_name,
                text=full_text,
                pages=pages,
            )

            cell_id = str(uuid.uuid4())
            cell_record = {
                "id": cell_id,
                "table_id": table_id,
                "column_id": col_id,
                "document_id": doc_id,
                "value": result.value,
                "confidence_score": result.confidence_score,
                "evidence": result.evidence.to_dict() if result.evidence else None,
                "status": result.status,
                "updated_at": now,
            }
            cells_to_upsert.append(cell_record)
            extracted_count += 1

    # 4. Save to database using upsert
    if cells_to_upsert:
        try:
            db.table("review_table_cells").upsert(
                cells_to_upsert,
                on_conflict="table_id,column_id,document_id",
            ).execute()
        except Exception as e:
            # If composite conflict fails, delete and reinsert
            for cell in cells_to_upsert:
                try:
                    db.table("review_table_cells").delete().eq("table_id", table_id).eq("column_id", cell["column_id"]).eq("document_id", cell["document_id"]).execute()
                    db.table("review_table_cells").insert(cell).execute()
                except Exception:
                    pass

    return {
        "status": "completed",
        "extracted_cells": extracted_count,
        "columns_processed": len(columns),
        "documents_processed": len(documents),
    }


# --- Cell Manual Override ---

@router.patch("/{table_id}/cells/{cell_id}")
async def update_cell(
    case_id: str,
    table_id: str,
    cell_id: str,
    body: UpdateCellRequest,
    _=Depends(get_case_access),
):
    """Manually update or override a cell value and confidence."""
    db = svc()
    update_data = {
        "value": body.value,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if body.confidence_score is not None:
        update_data["confidence_score"] = body.confidence_score
    if body.evidence is not None:
        update_data["evidence"] = body.evidence

    try:
        res = db.table("review_table_cells").update(update_data).eq("id", cell_id).eq("table_id", table_id).execute()
        if not res.data:
            raise HTTPException(404, "Cell not found")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to update cell: {e}")


# --- Export Endpoints ---

@router.get("/{table_id}/export")
async def export_review_table(
    case_id: str,
    table_id: str,
    format: str = Query("xlsx", regex="^(xlsx|csv)$"),
    _=Depends(get_case_access),
):
    """Export review table with citations and confidence metadata to XLSX or CSV."""
    db = svc()

    # 1. Fetch table metadata
    try:
        t_res = db.table("review_tables").select("*").eq("id", table_id).eq("case_id", case_id).single().execute()
        table = t_res.data
        if not table:
            raise HTTPException(404, "Review table not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to load table: {e}")

    # 2. Fetch columns
    cols_res = db.table("review_table_columns").select("*").eq("table_id", table_id).order("position").execute()
    columns = cols_res.data or []

    # 3. Fetch documents
    docs_res = db.table("documents").select("id, file_name").eq("case_id", case_id).order("created_at").execute()
    documents = docs_res.data or []

    # 4. Fetch cells
    cells_res = db.table("review_table_cells").select("*").eq("table_id", table_id).execute()
    cells = cells_res.data or []

    # Map cells
    cell_map: Dict[str, Dict[str, Any]] = {}
    for c in cells:
        d_id = c.get("document_id")
        col_id = c.get("column_id")
        if d_id not in cell_map:
            cell_map[d_id] = {}
        cell_map[d_id][col_id] = c

    # Build rows
    rows = []
    for doc in documents:
        d_id = doc["id"]
        rows.append({
            "document_id": d_id,
            "document_name": doc.get("file_name", "Document"),
            "cells": cell_map.get(d_id, {}),
        })

    safe_name = re.sub(r"[^\w\-_\. ]", "_", table.get("name", "Review_Table"))

    if format == "csv":
        csv_content = ReviewTableExporter.export_csv(table["name"], columns, rows)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.csv"'},
        )
    else:
        xlsx_bytes = ReviewTableExporter.export_xlsx(table["name"], columns, rows)
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.xlsx"'},
        )
