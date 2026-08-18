"""Property intelligence API with verification status tracking."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import create_client

from app.config import get_settings
from app.security.auth import get_case_access

settings = get_settings()
router = APIRouter(tags=["properties"])


def svc():
    url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "placeholder-key"
    try:
        return create_client(url, key)
    except Exception:
        return None


PROPERTY_FIELDS = [
    "name", "address", "state", "district", "taluk", "village",
    "survey_number", "hissa_number", "plot_number", "khata_number",
    "registration_number", "property_id_number", "description",
]


class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    taluk: Optional[str] = None
    village: Optional[str] = None
    survey_number: Optional[str] = None
    hissa_number: Optional[str] = None
    plot_number: Optional[str] = None
    khata_number: Optional[str] = None
    registration_number: Optional[str] = None
    property_id_number: Optional[str] = None
    description: Optional[str] = None


@router.get("/cases/{case_id}/property")
async def get_property(case_id: str, _=Depends(get_case_access)):
    ctx, case = _
    db = svc()
    prop = db.table("properties").select("*").eq("case_id", case_id).execute().data
    if not prop:
        # Auto-create for property cases on first access
        row = db.table("properties").insert({"case_id": case_id, "name": case["name"]}).execute()
        prop = row.data
    prop = prop[0]

    # Attach per-field verification sources
    sources = db.table("property_field_sources").select("*").eq("property_id", prop["id"]).execute().data
    by_field: dict[str, list] = {}
    for s in sources:
        by_field.setdefault(s["field_name"], []).append(s)

    fields = []
    for f in PROPERTY_FIELDS:
        entries = by_field.get(f, [])
        # Best available: DOCUMENT_VERIFIED > EXTERNAL_SOURCE_VERIFIED > USER_PROVIDED
        best = None
        for priority in ("DOCUMENT_VERIFIED", "EXTERNAL_SOURCE_VERIFIED", "USER_PROVIDED"):
            best = next((e for e in entries if e["verification"] == priority), best)
        fields.append({
            "field": f,
            "value": prop.get(f),
            "verification": best["verification"] if best else "UNVERIFIED",
            "source_document_id": best.get("source_document_id") if best else None,
            "source_page": best.get("source_page") if best else None,
        })

    return {"property": prop, "fields": fields}


@router.patch("/cases/{case_id}/property")
async def update_property(case_id: str, body: PropertyUpdate, _=Depends(get_case_access)):
    ctx, case = _
    db = svc()
    prop = db.table("properties").select("*").eq("case_id", case_id).single().execute()
    if not prop.data:
        db.table("properties").insert({"case_id": case_id, "name": case["name"]}).execute()
        prop = db.table("properties").select("*").eq("case_id", case_id).single().execute()

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")

    # Record user-provided values with USER_PROVIDED verification
    for field, value in updates.items():
        db.table("property_field_sources").insert({
            "property_id": prop.data["id"],
            "field_name": field,
            "value": value,
            "verification": "USER_PROVIDED",
        }).execute()

    return db.table("properties").update(updates).eq("id", prop.data["id"]).execute().data[0]


@router.get("/cases/{case_id}/property/entities")
async def property_entities(case_id: str, _=Depends(get_case_access)):
    """Show all document-extracted values for property fields, with evidence."""
    ctx, case = _
    PROPERTY_ENTITY_TYPES = {
        "survey_number": "survey_number", "hissa": "hissa_number",
        "plot_number": "plot_number", "khata_number": "khata_number",
        "village": "village", "taluk": "taluk", "district": "district",
        "registration_number": "registration_number", "area": "area",
        "boundaries": "boundaries",
    }
    rows = (
        svc().table("extracted_entities")
        .select("*, documents(file_name)")
        .eq("case_id", case_id)
        .in_("entity_type", list(PROPERTY_ENTITY_TYPES.keys()))
        .order("confidence", desc=True)
        .execute().data
    )
    grouped: dict[str, list] = {}
    for r in rows:
        field = PROPERTY_ENTITY_TYPES.get(r["entity_type"], r["entity_type"])
        grouped.setdefault(field, []).append({
            "value": r["value"],
            "source_text": r["source_text"],
            "document": (r.get("documents") or {}).get("file_name"),
            "page": r["page_number"],
            "confidence": float(r["confidence"] or 0),
        })
    return grouped
