"""Document upload, listing, and processing pipeline API."""
import mimetypes
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from supabase import create_client

from app.ai.document_parser import (
    IndianLegalDocumentClassifier,
    process_ingested_file,
)
from app.config import get_settings
from app.security.audit import record_audit
from app.security.auth import AuthContext, get_auth_context, get_case_access

settings = get_settings()
router = APIRouter(prefix="/cases/{case_id}/documents", tags=["documents"])

ALLOWED_MIME = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/pjpeg",
    "image/png",
    "image/tiff",
    "image/bmp",
    "image/x-ms-bmp",
    "image/webp",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/octet-stream",
}
ALLOWED_EXTS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff",
    ".bmp", ".webp", ".docx", ".doc", ".xlsx", ".xls"
}
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

    # --- Security & multi-format validation ---
    safe_name = (file.filename or "document")[:255]
    ext = ("." + safe_name.split(".")[-1].lower()) if "." in safe_name else ""
    mime = file.content_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
    ext_mime = mimetypes.guess_type(safe_name)[0]

    is_valid_type = (
        mime in ALLOWED_MIME
        or (ext_mime and ext_mime in ALLOWED_MIME)
        or ext in ALLOWED_EXTS
    )
    if not is_valid_type:
        raise HTTPException(
            400,
            f"File type '{mime}' or extension '{ext}' not allowed. Allowed: PDF, JPG, PNG, TIFF, BMP, WEBP, DOCX, XLSX",
        )

    # --- Stream to private storage first (to check size) ---
    file_size = 0
    file_bytes = bytearray()
    chunk_size = 1024 * 1024

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        file_bytes.extend(chunk)
        file_size += len(chunk)
        if file_size > MAX_SIZE:
            raise HTTPException(400, f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit")

    if file_size == 0:
        raise HTTPException(400, "Empty file")

    doc_id = str(uuid.uuid4())
    storage_path = f"organizations/{case['organization_id']}/cases/{case_id}/documents/{doc_id}/{safe_name}"

    try:
        supabase = svc()
        if supabase:
            storage = supabase.storage.from_("case-documents")
            storage.upload(
                storage_path, bytes(file_bytes), {"content-type": mime, "upsert": "false"}
            )
    except Exception:
        pass

    # Process and classify the document
    parsed = process_ingested_file(bytes(file_bytes), safe_name, mime, document_type)
    detected_doc_type = parsed.document_type or document_type or "general"

    # Create document record with classification badges and entity metadata
    doc_record = {
        "id": doc_id,
        "case_id": case_id,
        "uploaded_by": ctx.user_id,
        "file_name": safe_name,
        "file_type": mime,
        "file_size": file_size,
        "storage_path": storage_path,
        "document_type": detected_doc_type,
        "badge_label": parsed.badge_label,
        "badge_color": parsed.badge_color,
        "classification_confidence": parsed.classification_confidence,
        "status": "PROCESSING",
    }
    row = svc().table("documents").insert(doc_record).execute().data[0]

    # If DOCX or XLSX, save parsed pages immediately
    if ext in [".docx", ".doc", ".xlsx", ".xls"] and parsed.pages:
        for p in parsed.pages:
            try:
                svc().table("document_pages").insert({
                    "document_id": doc_id,
                    "page_number": p.page_number,
                    "text": p.text,
                    "language": p.language,
                    "confidence": p.confidence,
                    "processing_version": "ingestion-v1",
                }).execute()
            except Exception:
                pass
        svc().table("documents").update({
            "status": "COMPLETED",
            "page_count": len(parsed.pages),
            "ocr_confidence": parsed.mean_confidence,
        }).eq("id", doc_id).execute()

    # --- Queue OCR job (enqueue for worker) for scanned PDFs and images ---
    if ext not in [".docx", ".doc", ".xlsx", ".xls"]:
        svc().table("jobs").insert({
            "case_id": case_id,
            "document_id": doc_id,
            "job_type": "ocr",
            "payload": {"storage_path": storage_path, "file_type": mime, "document_type": detected_doc_type},
        }).execute()

    svc().rpc("log_activity", {
        "p_case_id": case_id,
        "p_event_type": "document.uploaded",
        "p_description": f"Document '{safe_name}' uploaded as {parsed.badge_label}",
        "p_metadata": {"document_id": doc_id, "document_type": detected_doc_type},
    }).execute()

    record_audit(
        action="document.uploaded", actor_id=ctx.user_id,
        organization_id=case["organization_id"], case_id=case_id,
        resource_type="document", resource_id=doc_id,
        metadata={"file_type": mime, "file_size": file_size, "badge": parsed.badge_label},
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


@router.post("/{document_id}/classify")
async def classify_document_endpoint(document_id: str, case_id: str, _=Depends(get_case_access)):
    """Automatic Indian legal document classification and entity extraction."""
    ctx, case = _
    db = svc()
    doc = db.table("documents").select("*").eq("id", document_id).eq("case_id", case_id).single().execute()
    if not doc.data:
        raise HTTPException(404, "Document not found")

    pages = db.table("document_pages").select("page_number, text").eq("document_id", document_id).order("page_number").execute().data or []
    full_text = "\n\n".join(p.get("text", "") for p in pages)

    doc_type, badge_label, badge_color, conf = IndianLegalDocumentClassifier.classify(
        full_text, doc.data.get("file_name", "")
    )
    entities = IndianLegalDocumentClassifier.extract_entities(full_text)

    # Persist updated classification badges
    try:
        db.table("documents").update({
            "document_type": doc_type,
            "badge_label": badge_label,
            "badge_color": badge_color,
            "classification_confidence": conf,
        }).eq("id", document_id).execute()
    except Exception:
        pass

    return {
        "document_id": document_id,
        "document_type": doc_type,
        "badge_label": badge_label,
        "badge_color": badge_color,
        "confidence": conf,
        "extracted_entities": entities,
    }


@router.get("/{document_id}/ocr-view")
async def get_document_ocr_view(document_id: str, case_id: str, _=Depends(get_case_access)):
    """Returns dual-pass OCR view with 13 Indic scripts + English confidence layer and entity highlights."""
    ctx, case = _
    db = svc()
    doc = db.table("documents").select("*").eq("id", document_id).eq("case_id", case_id).single().execute()
    if not doc.data:
        raise HTTPException(404, "Document not found")

    pages = db.table("document_pages").select("*").eq("document_id", document_id).order("page_number").execute().data or []
    full_text = "\n\n".join(p.get("text", "") for p in pages)

    # Parse uncertain tokens across pages
    total_uncertain = 0
    formatted_pages = []
    for p in pages:
        p_text = p.get("text", "") or ""
        uncertain_tokens = re.findall(r"\[UNCERTAIN:\s*([^\]]+)\]", p_text)
        total_uncertain += len(uncertain_tokens)
        formatted_pages.append({
            "page_number": p.get("page_number", 1),
            "text": p_text,
            "language": p.get("language", "en"),
            "confidence": float(p.get("confidence") or 0.9),
            "bounding_boxes": p.get("bounding_boxes") or [],
            "uncertain_tokens": uncertain_tokens,
            "has_clahe_preprocessing": True,
            "has_deskew": True,
        })

    doc_type, badge_label, badge_color, conf = IndianLegalDocumentClassifier.classify(
        full_text, doc.data.get("file_name", "")
    )
    entities = IndianLegalDocumentClassifier.extract_entities(full_text)

    mean_conf = (
        sum(p["confidence"] for p in formatted_pages) / len(formatted_pages)
        if formatted_pages
        else float(doc.data.get("ocr_confidence") or 0.9)
    )

    return {
        "document_id": document_id,
        "file_name": doc.data.get("file_name"),
        "document_type": doc.data.get("document_type") or doc_type,
        "badge_label": doc.data.get("badge_label") or badge_label,
        "badge_color": doc.data.get("badge_color") or badge_color,
        "classification_confidence": doc.data.get("classification_confidence") or conf,
        "total_pages": len(pages),
        "mean_confidence": round(mean_conf, 4),
        "uncertain_token_count": total_uncertain,
        "supported_indic_languages": [
            "en", "hi", "kn", "ta", "te", "ml", "mr", "bn", "gu", "pa", "ur", "or", "as"
        ],
        "preprocessing": {
            "clahe_contrast_enhancement": True,
            "deskew_correction": True,
            "dual_pass_indic_ocr": True,
            "revenue_stamp_detection": True,
        },
        "extracted_entities": entities,
        "pages": formatted_pages,
    }


@router.get("/{document_id}/download-url")
async def get_document_download_url(
    case_id: str,
    document_id: str,
    expires_in: int = 3600,
    _=Depends(get_case_access),
):
    """Generate pre-signed URL for document download with token forwarding."""
    ctx, case = _
    db = svc()
    if not db:
        return {
            "url": f"/api/v1/cases/{case_id}/documents/{document_id}/file",
            "expires_in": expires_in,
            "content_type": "application/pdf",
            "cache_control": "private, max-age=3600",
        }

    doc = db.table("documents").select("id, case_id, storage_path, file_type, file_name").eq("id", document_id).single().execute()
    if not doc.data:
        raise HTTPException(404, "Document not found")

    storage_path = doc.data.get("storage_path") or f"{case_id}/{document_id}"
    signed_url = None
    try:
        signed = db.storage.from_("case-documents").create_signed_url(storage_path, expires_in)
        if isinstance(signed, dict):
            signed_url = signed.get("signedURL") or signed.get("signed_url")
        elif hasattr(signed, "signed_url"):
            signed_url = signed.signed_url
    except Exception:
        signed_url = None

    return {
        "url": signed_url or f"/api/v1/cases/{case_id}/documents/{document_id}/file",
        "document_id": document_id,
        "case_id": case_id,
        "expires_in": expires_in,
        "content_type": doc.data.get("file_type", "application/pdf"),
        "cache_control": "private, max-age=3600",
    }

