"""Multi-document comparison API."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supabase import create_client

from app.config import get_settings
from app.security.auth import get_case_access

settings = get_settings()
router = APIRouter(tags=["comparison"])


def svc():
    url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "placeholder-key"
    try:
        return create_client(url, key)
    except Exception:
        return None


class CompareRequest(BaseModel):
    document_ids: List[str] = Field(min_length=2, max_length=6)


def _compute_text_diff(text_a: str, text_b: str) -> list[dict]:
    """Word-level diff computation returning structured chunks with highlight types."""
    import difflib
    words_a = text_a.split()
    words_b = text_b.split()
    matcher = difflib.SequenceMatcher(None, words_a, words_b)
    diff_chunks = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            diff_chunks.append({"type": "equal", "text_a": " ".join(words_a[i1:i2]), "text_b": " ".join(words_b[j1:j2])})
        elif tag == "replace":
            diff_chunks.append({"type": "replace", "text_a": " ".join(words_a[i1:i2]), "text_b": " ".join(words_b[j1:j2])})
        elif tag == "delete":
            diff_chunks.append({"type": "delete", "text_a": " ".join(words_a[i1:i2]), "text_b": ""})
        elif tag == "insert":
            diff_chunks.append({"type": "insert", "text_a": "", "text_b": " ".join(words_b[j1:j2])})
    return diff_chunks


@router.post("/cases/{case_id}/compare")
async def compare_documents(case_id: str, body: CompareRequest, _=Depends(get_case_access)):
    ctx, case = _
    db = svc()

    # Verify all documents belong to this case
    docs = db.table("documents").select("id, file_name").eq("case_id", case_id).in_(
        "id", body.document_ids
    ).execute().data
    if len(docs) < 2:
        raise HTTPException(400, "At least 2 documents from this case are required")

    job = db.table("jobs").insert({
        "case_id": case_id,
        "job_type": "comparison",
        "payload": {"document_ids": body.document_ids},
    }).execute().data[0]
    return {"job_id": job["id"], "status": "QUEUED"}


@router.post("/cases/{case_id}/compare-direct")
async def compare_documents_direct(case_id: str, body: CompareRequest, _=Depends(get_case_access)):
    """Computes immediate side-by-side visual diff and field comparison."""
    ctx, case = _
    db = svc()

    docs = db.table("documents").select("id, file_name, document_type, badge_label").eq("case_id", case_id).in_(
        "id", body.document_ids
    ).execute().data or []
    if len(docs) < 2:
        raise HTTPException(400, "At least 2 documents from this case are required")

    name_by_id = {d["id"]: d.get("file_name", "Document") for d in docs}

    # Fetch pages for text diff
    pages = db.table("document_pages").select("document_id, page_number, text").in_(
        "document_id", body.document_ids
    ).order("page_number").execute().data or []

    text_by_doc: dict[str, str] = {}
    for p in pages:
        text_by_doc[p["document_id"]] = text_by_doc.get(p["document_id"], "") + "\n" + (p.get("text") or "")

    doc_a_id, doc_b_id = body.document_ids[0], body.document_ids[1]
    text_a = text_by_doc.get(doc_a_id, "")
    text_b = text_by_doc.get(doc_b_id, "")

    diff_chunks = _compute_text_diff(text_a, text_b)

    # Fetch entities for field comparison
    entities = db.table("extracted_entities").select("*").eq("case_id", case_id).in_(
        "document_id", body.document_ids
    ).execute().data or []

    compare_fields = [
        "survey_number", "area", "seller", "buyer", "owner",
        "registration_number", "registration_date", "sro", "transaction_amount"
    ]

    field_results = []
    for f in compare_fields:
        vals = {}
        for e in entities:
            if e.get("entity_type") == f:
                vals[e["document_id"]] = e.get("value")
        if vals:
            distinct = {str(v).strip().lower() for v in vals.values() if v}
            verdict = "MATCH" if len(distinct) <= 1 and len(vals) == len(body.document_ids) else ("MISMATCH" if len(distinct) > 1 else "MISSING")
            field_results.append({
                "field_name": f.replace("_", " ").title(),
                "verdict": verdict,
                "values": [
                    {"document_id": did, "document_name": name_by_id.get(did, "Doc"), "value": vals.get(did, "Not specified")}
                    for did in body.document_ids
                ],
            })

    return {
        "case_id": case_id,
        "doc_a": {"id": doc_a_id, "name": name_by_id.get(doc_a_id)},
        "doc_b": {"id": doc_b_id, "name": name_by_id.get(doc_b_id)},
        "field_comparisons": field_results,
        "diff_chunks": diff_chunks[:200],  # Return up to 200 diff segments
    }


@router.get("/cases/{case_id}/comparison")
async def get_comparison_results(case_id: str, _=Depends(get_case_access)):
    ctx, case = _
    return (
        svc().table("comparison_results").select("*").eq("case_id", case_id)
        .order("created_at", desc=True).execute().data
    )
