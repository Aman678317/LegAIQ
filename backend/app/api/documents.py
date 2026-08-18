"""Document upload, listing, and processing pipeline API."""
import mimetypes
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from supabase import create_client

from app.config import get_settings
from app.security.audit import record_audit
from app.security.auth import AuthContext, get_auth_context, get_case_access

settings = get_settings()
router = APIRouter(prefix="/cases/{case_id}/documents", tags=["documents"])

ALLOWED_MIME = {"application/pdf", "image/jpeg", "image/png", "image/tiff"}
MAX_SIZE = 50 * 1024 * 1024  # 50 MB


def svc():
    url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "placeholder-key"
    try:
        return create_client(url, key)
    except Exception:
        return None


@router.post("")
async def upload_document(
    case_id: str,
    file: UploadFile = File(...),
    document_type: Optional[str] = None,
    _=Depends(get_case_access),
):
    ctx, case = _

    # --- Security validation ---
    mime = file.content_type or mimetypes.guess_type(file.filename or "")[0] or ""
    ext_mime = mimetypes.guess_type(file.filename or "")[0]
    if mime not in ALLOWED_MIME and ext_mime not in ALLOWED_MIME:
        raise HTTPException(400, f"File type '{mime}' not allowed. Allowed: PDF, JPG, PNG, TIFF")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit")
    if len(content) == 0:
        raise HTTPException(400, "Empty file")

    # --- Record ---
    doc_id = str(uuid.uuid4())
    safe_name = (file.filename or "document")[:255]
    storage_path = f"organizations/{case['organization_id']}/cases/{case_id}/documents/{doc_id}/{safe_name}"

    row = svc().table("documents").insert({
        "id": doc_id,
        "case_id": case_id,
        "uploaded_by": ctx.user_id,
        "file_name": safe_name,
        "file_type": mime,
        "file_size": len(content),
        "storage_path": storage_path,
        "document_type": document_type,
        "status": "VALIDATING",
    }).execute().data[0]

    # --- Private storage upload ---
    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        supabase.storage.from_("case-documents").upload(
            storage_path, content, {"content-type": mime, "upsert": "false"}
        )
    except Exception as e:
        svc().table("documents").update({"status": "FAILED", "error_message": f"Storage upload failed: {e}"}).eq("id", doc_id).execute()
        raise HTTPException(500, f"Storage upload failed: {e}")

    svc().table("documents").update({"status": "PROCESSING"}).eq("id", doc_id).execute()

    # --- Queue OCR job (enqueue for worker) ---
    svc().table("jobs").insert({
        "case_id": case_id,
        "document_id": doc_id,
        "job_type": "ocr",
        "payload": {"storage_path": storage_path, "file_type": mime},
    }).execute()

    svc().rpc("log_activity", {
        "p_case_id": case_id,
        "p_event_type": "document.uploaded",
        "p_description": f"Document '{safe_name}' uploaded",
        "p_metadata": {"document_id": doc_id},
    }).execute()

    record_audit(
        action="document.uploaded", actor_id=ctx.user_id,
        organization_id=case["organization_id"], case_id=case_id,
        resource_type="document", resource_id=doc_id,
        metadata={"file_type": mime, "file_size": len(content)},
    )

    return row


@router.get("")
async def list_documents(
    case_id: str,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    _=Depends(get_case_access),
):
    ctx, case = _
    q = (
        svc().table("documents").select("*").eq("case_id", case_id)
        .order("created_at", desc=True).range(offset, offset + limit - 1)
    )
    if status:
        q = q.eq("status", status)
    return q.execute().data


@router.get("/{document_id}")
async def get_document(document_id: str, case_id: str, _=Depends(get_case_access)):
    ctx, case = _
    doc = svc().table("documents").select("*").eq("id", document_id).eq("case_id", case_id).single().execute()
    if not doc.data:
        raise HTTPException(404, "Document not found")
    return doc.data


@router.get("/{document_id}/download-url")
async def download_url(document_id: str, case_id: str, _=Depends(get_case_access)):
    ctx, case = _
    doc = svc().table("documents").select("storage_path").eq("id", document_id).single().execute()
    if not doc.data:
        raise HTTPException(404, "Document not found")
    url = svc().storage.from_("case-documents").create_signed_url(doc.data["storage_path"], 3600)
    svc().rpc("log_activity", {
        "p_case_id": case_id,
        "p_event_type": "document.downloaded",
        "p_description": f"Document {document_id} download link generated",
    }).execute()
    record_audit(
        action="document.downloaded", actor_id=ctx.user_id,
        case_id=case_id, resource_type="document", resource_id=document_id,
    )
    return {"url": url, "expires_in": 3600}


@router.get("/{document_id}/pages")
async def get_pages(document_id: str, case_id: str, _=Depends(get_case_access)):
    ctx, case = _
    return (
        svc().table("document_pages").select("id, page_number, text, language, confidence")
        .eq("document_id", document_id).order("page_number").execute().data
    )


class TranslationRequest(BaseModel):
    page: Optional[int] = 1
    language: str = "en"


@router.post("/{document_id}/translate")
async def translate_document(
    document_id: str, case_id: str, body: TranslationRequest,
    _=Depends(get_case_access),
):
    ctx, case = _
    target_lang = body.language
    page_number = body.page or 1

    if target_lang not in settings.SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Unsupported language '{target_lang}'")

    db = svc()
    if not db:
        raise HTTPException(500, "Database not available")

    page = (
        db.table("document_pages").select("id, text")
        .eq("document_id", document_id).eq("page_number", page_number).single().execute()
    )
    if not page.data:
        raise HTTPException(404, "Page not found")

    existing = (
        db.table("page_translations").select("translated_text")
        .eq("page_id", page.data["id"]).eq("target_language", target_lang)
        .execute().data
    )
    if existing:
        return {"page_number": page_number, "language": target_lang, "text": existing[0]["translated_text"], "cached": True, "status": "COMPLETED"}

    # Generate inline when provider available
    if settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY or settings.OLLAMA_BASE_URL:
        from app.ai.provider import LLMRequest, router as llm_router
        lang_names = {
            "en": "English", "hi": "Hindi", "kn": "Kannada", "ta": "Tamil",
            "te": "Telugu", "ml": "Malayalam", "mr": "Marathi", "bn": "Bengali",
            "gu": "Gujarati", "pa": "Punjabi", "ur": "Urdu", "or": "Odia", "as": "Assamese",
        }
        raw_text = page.data.get("text", "")
        if raw_text:
            try:
                response = await llm_router.complete(LLMRequest(
                    system=f"Translate the legal document text into {lang_names.get(target_lang, target_lang)}. "
                           "Preserve party names, survey numbers, dates, and amounts exactly. Output translation only.",
                    prompt=raw_text[:12000],
                    task="translation",
                ))
                translated = response.content
                try:
                    db.table("page_translations").upsert({
                        "page_id": page.data["id"], "target_language": target_lang,
                        "translated_text": translated, "provider": response.provider,
                    }, on_conflict="page_id,target_language").execute()
                except Exception:
                    pass
                return {"page_number": page_number, "language": target_lang, "text": translated, "cached": False, "status": "COMPLETED"}
            except Exception:
                pass

    # Queue via worker as fallback
    db.table("jobs").insert({
        "case_id": case_id,
        "document_id": document_id,
        "job_type": "translation",
        "payload": {"page_number": page_number, "target_language": target_lang},
    }).execute()
    return {"page_number": page_number, "language": target_lang, "status": "QUEUED", "cached": False}


@router.get("/{document_id}/pages/{page_number}/translation/{target_lang}")
async def get_page_translation(
    document_id: str, page_number: int, target_lang: str, case_id: str,
    _=Depends(get_case_access),
):
    ctx, case = _
    if target_lang not in settings.SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Unsupported language '{target_lang}'")

    page = (
        svc().table("document_pages").select("id")
        .eq("document_id", document_id).eq("page_number", page_number).single().execute()
    )
    if not page.data:
        raise HTTPException(404, "Page not found")

    existing = (
        svc().table("page_translations").select("translated_text")
        .eq("page_id", page.data["id"]).eq("target_language", target_lang)
        .execute().data
    )
    if existing:
        return {"page_number": page_number, "language": target_lang, "text": existing[0]["translated_text"], "cached": True}

    # Generate via worker queue; return accepted status
    svc().table("jobs").insert({
        "case_id": case_id,
        "document_id": document_id,
        "job_type": "translation",
        "payload": {"page_number": page_number, "target_language": target_lang},
    }).execute()
    return {"page_number": page_number, "language": target_lang, "status": "QUEUED", "cached": False}


@router.delete("/{document_id}")
async def delete_document(document_id: str, case_id: str, _=Depends(get_case_access)):
    ctx, case = _
    if ctx.role not in ("OWNER", "ADMIN"):
        raise HTTPException(403, "Only OWNER or ADMIN can delete documents")
    doc = svc().table("documents").select("storage_path").eq("id", document_id).single().execute()
    if doc.data:
        try:
            svc().storage.from_("case-documents").remove([doc.data["storage_path"]])
        except Exception:
            pass
    svc().table("documents").delete().eq("id", document_id).execute()
    return {"deleted": True}
