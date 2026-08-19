"""Legal drafting studio API."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supabase import create_client

from app.ai.provider import LLMRequest, router as llm_router
from app.config import get_settings
from app.security.auth import AuthContext, get_case_access, resource_case_access, require_role

settings = get_settings()
router = APIRouter(tags=["drafts"])

DRAFT_TYPES = [
    "petition", "legal_notice", "representation", "application", "reply",
    "affidavit", "declaration", "property_letter", "mutation_application",
    "registration_application", "information_request", "due_diligence_report",
]

DRAFT_DISCLAIMER = (
    "\n\n---\nAI-generated draft. Review and verify before filing or sending."
)

DRAFT_SYSTEM = """You are Jurisiva Drafting Agent for Indian legal documents.

RULES:
1. Draft ONLY from verified case facts and document evidence provided in the prompt.
2. For missing facts, insert clearly marked placeholders like [VERIFY: survey number].
3. NEVER invent case numbers, dates, party details, or statutory sections not given.
4. Use formal Indian legal drafting conventions for the document type.
5. Add appropriate statutory references only when supplied in evidence; otherwise mark [VERIFY: applicable section]."""


class DraftCreate(BaseModel):
    draft_type: str
    title: str = Field(min_length=1, max_length=300)
    instructions: str = Field(min_length=10, max_length=6000)
    model: Optional[str] = None


class DraftUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None


def svc():
    url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "placeholder-key"
    try:
        return create_client(url, key)
    except Exception:
        return None


async def build_case_fact_block(case_id: str) -> str:
    db = svc()
    entities = db.table("extracted_entities").select(
        "entity_type, value, source_text, page_number, documents(file_name)"
    ).eq("case_id", case_id).limit(200).execute().data
    if not entities:
        return "No extracted entities yet. Draft will rely on user instructions only."

    lines = []
    for e in entities:
        doc = (e.get("documents") or {}).get("file_name", "unknown doc")
        lines.append(f"- {e['entity_type']}: {e['value']} [Source: {doc}, page {e['page_number']}]")
    return "\n".join(lines)


@router.post("/cases/{case_id}/drafts")
async def create_draft(case_id: str, body: DraftCreate, _=Depends(get_case_access)):
    ctx, case = _
    if body.draft_type not in DRAFT_TYPES:
        raise HTTPException(400, f"Invalid draft_type. Allowed: {', '.join(DRAFT_TYPES)}")

    facts = await build_case_fact_block(case_id)
    response = await llm_router.complete(LLMRequest(
        system=DRAFT_SYSTEM,
        prompt=f"""Draft a {body.draft_type.replace('_', ' ')} titled "{body.title}".

CASE FACTS (from verified document extraction):
{facts}

USER INSTRUCTIONS:
{body.instructions}

Jurisdiction: {case.get('jurisdiction_state') or 'Not specified'}""",
        task="drafting",
        model=body.model,
        max_tokens=4000,
    ))

    draft = svc().table("drafts").insert({
        "case_id": case_id,
        "created_by": ctx.user_id,
        "draft_type": body.draft_type,
        "title": body.title,
        "content": response.content + DRAFT_DISCLAIMER,
        "status": "REVIEW",
    }).execute().data[0]

    # Phase 14 workflow: draft → fact check → citation check (Verification Agent)
    try:
        from app.ai.agents.registry import run_verification_agent
        await run_verification_agent(draft["id"], case_id, case["organization_id"])
        draft = svc().table("drafts").select("*").eq("id", draft["id"]).single().execute().data
    except Exception:
        pass  # verification is a safeguard, not a blocker; draft stays in REVIEW

    return draft


@router.get("/cases/{case_id}/drafts")
async def list_drafts(case_id: str, _=Depends(get_case_access)):
    ctx, case = _
    return (
        svc().table("drafts").select("*").eq("case_id", case_id)
        .order("updated_at", desc=True).execute().data
    )


@router.get("/drafts/{draft_id}")
async def get_draft(draft_id: str, _=Depends(resource_case_access("drafts", "draft_id"))):
    ctx, case = _
    d = svc().table("drafts").select("*").eq("id", draft_id).single().execute()
    if not d.data or d.data["case_id"] != case["id"]:
        raise HTTPException(404, "Draft not found in this case")
    return d.data


@router.patch("/drafts/{draft_id}")
async def update_draft(draft_id: str, body: DraftUpdate, _=Depends(resource_case_access("drafts", "draft_id"))):
    ctx, case = _
    db = svc()
    existing = db.table("drafts").select("*").eq("id", draft_id).single().execute()
    if not existing.data or existing.data["case_id"] != case["id"]:
        raise HTTPException(404, "Draft not found in this case")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if "content" in updates and updates["content"] != existing.data["content"]:
        updates["version"] = existing.data["version"] + 1
    if not updates:
        raise HTTPException(400, "No fields to update")
    return db.table("drafts").update(updates).eq("id", draft_id).execute().data[0]


@router.post("/drafts/{draft_id}/verify")
async def verify_draft(draft_id: str, _=Depends(resource_case_access("drafts", "draft_id"))):
    """Re-run the fact-check + citation-check workflow on demand."""
    ctx, case = _
    db = svc()
    existing = db.table("drafts").select("content, case_id").eq("id", draft_id).single().execute()
    if not existing.data or existing.data["case_id"] != case["id"]:
        raise HTTPException(404, "Draft not found in this case")

    # Strip a previous verification block before re-checking
    content = existing.data["content"].split("\n---\nVERIFICATION REPORT")[0]
    db.table("drafts").update({"content": content}).eq("id", draft_id).execute()

    from app.ai.agents.registry import run_verification_agent
    result = await run_verification_agent(draft_id, case["id"], case["organization_id"])
    updated = db.table("drafts").select("*").eq("id", draft_id).single().execute().data
    return {"draft": updated, "verification": result}


@router.delete("/drafts/{draft_id}")
async def delete_draft(draft_id: str, _=Depends(resource_case_access("drafts", "draft_id")), ctx: AuthContext = Depends(require_role("ADMIN"))):
    ctx, case = _
    db = svc()
    existing = db.table("drafts").select("case_id").eq("id", draft_id).single().execute()
    if not existing.data or existing.data["case_id"] != case["id"]:
        raise HTTPException(404, "Draft not found in this case")
    db.table("drafts").delete().eq("id", draft_id).execute()
    return {"deleted": True}
