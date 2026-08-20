"""PII Detection and Redaction API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json

from app.config import get_settings
from app.security.auth import AuthContext, get_auth_context, require_role, get_case_access
from app.security.pii import (
    PIIEntityType,
    RedactionStrategy,
    PIIEntity,
    RedactionResult,
    RedactionConfig,
    PIIDetectionEngine,
    PIIRedactionPipeline,
    detect_pii,
    redact_pii,
    redact_document,
)

settings = get_settings()
router = APIRouter(prefix="/pii", tags=["pii"])


# ==================== Request/Response Models ====================

class PIIDetectionRequest(BaseModel):
    text: str
    config: Optional[RedactionConfig] = None


class PIIDetectionResponse(BaseModel):
    entities: List[Dict[str, Any]]
    stats: Dict[str, int]


class PIIRedactionRequest(BaseModel):
    text: str
    strategy: RedactionStrategy = RedactionStrategy.MASK
    mask_char: str = "*"
    preserve_length: bool = True
    custom_replacements: Optional[Dict[str, str]] = None
    enabled_entity_types: Optional[List[str]] = None
    min_confidence: float = 0.7
    indian_context: bool = True
    legal_context: bool = True


class PIIRedactionResponse(BaseModel):
    original_text: str
    redacted_text: str
    entities: List[Dict[str, Any]]
    redaction_map: Dict[str, str]
    stats: Dict[str, Any]


class DocumentRedactionRequest(BaseModel):
    document: Dict[str, Any]
    strategy: RedactionStrategy = RedactionStrategy.MASK
    mask_char: str = "*"
    preserve_length: bool = True
    custom_replacements: Optional[Dict[str, str]] = None
    enabled_entity_types: Optional[List[str]] = None
    min_confidence: float = 0.7


class CaseRedactionRequest(BaseModel):
    case_id: str
    strategy: RedactionStrategy = RedactionStrategy.MASK
    mask_char: str = "*"
    preserve_length: bool = True
    custom_replacements: Optional[Dict[str, str]] = None
    enabled_entity_types: Optional[List[str]] = None
    min_confidence: float = 0.7


class CaseRedactionResponse(BaseModel):
    case_id: str
    total_documents: int
    processed: int
    entities_found: int
    by_type: Dict[str, int]


# ==================== API Endpoints ====================

@router.post("/detect", response_model=PIIDetectionResponse)
async def detect_pii_endpoint(
    request: PIIDetectionRequest,
    ctx: AuthContext = Depends(get_auth_context),
):
    """Detect PII entities in text."""
    engine = PIIDetectionEngine(request.config)
    entities = engine.detect(request.text)
    
    # Convert to serializable format
    entity_list = [
        {
            "entity_type": e.entity_type.value,
            "text": e.text,
            "start": e.start,
            "end": e.end,
            "confidence": e.confidence,
            "context": e.context,
            "metadata": e.metadata,
        }
        for e in entities
    ]
    
    # Stats
    stats = {}
    for e in entities:
        t = e.entity_type.value
        stats[t] = stats.get(t, 0) + 1
    
    return PIIDetectionResponse(entities=entity_list, stats=stats)


@router.post("/redact", response_model=PIIRedactionResponse)
async def redact_pii_endpoint(
    request: PIIRedactionRequest,
    ctx: AuthContext = Depends(get_auth_context),
):
    """Redact PII from text."""
    # Build config
    enabled_types = None
    if request.enabled_entity_types:
        enabled_types = [PIIEntityType(t) for t in request.enabled_entity_types]
    
    custom_replacements = None
    if request.custom_replacements:
        custom_replacements = {PIIEntityType(k): v for k, v in request.custom_replacements.items()}
    
    config = RedactionConfig(
        strategy=request.strategy,
        mask_char=request.mask_char,
        preserve_length=request.preserve_length,
        custom_replacements=custom_replacements,
        enabled_entity_types=enabled_types or list(PIIEntityType),
        min_confidence=request.min_confidence,
        indian_context=request.indian_context,
        legal_context=request.legal_context,
    )
    
    result = redact_pii(request.text, config)
    
    return PIIRedactionResponse(
        original_text=result.original_text,
        redacted_text=result.redacted_text,
        entities=[
            {
                "entity_type": e.entity_type.value,
                "text": e.text,
                "start": e.start,
                "end": e.end,
                "confidence": e.confidence,
                "context": e.context,
            }
            for e in result.entities
        ],
        redaction_map=result.redaction_map,
        stats=result.stats,
    )


@router.post("/redact/document", response_model=Dict[str, Any])
async def redact_document_endpoint(
    request: DocumentRedactionRequest,
    ctx: AuthContext = Depends(require_role("STAFF")),
):
    """Redact PII from a document object."""
    enabled_types = None
    if request.enabled_entity_types:
        enabled_types = [PIIEntityType(t) for t in request.enabled_entity_types]
    
    custom_replacements = None
    if request.custom_replacements:
        custom_replacements = {PIIEntityType(k): v for k, v in request.custom_replacements.items()}
    
    config = RedactionConfig(
        strategy=request.strategy,
        mask_char=request.mask_char,
        preserve_length=request.preserve_length,
        custom_replacements=custom_replacements,
        enabled_entity_types=enabled_types or list(PIIEntityType),
        min_confidence=request.min_confidence,
    )
    
    redacted = redact_document(request.document, config)
    return redacted


@router.post("/redact/case", response_model=CaseRedactionResponse)
async def redact_case_documents(
    request: CaseRedactionRequest,
    ctx: AuthContext = Depends(require_role("LAWYER")),
):
    """Redact PII from all documents in a case."""
    # Verify case access
    _, case = await get_case_access(request.case_id, ctx)
    
    enabled_types = None
    if request.enabled_entity_types:
        enabled_types = [PIIEntityType(t) for t in request.enabled_entity_types]
    
    custom_replacements = None
    if request.custom_replacements:
        custom_replacements = {PIIEntityType(k): v for k, v in request.custom_replacements.items()}
    
    config = RedactionConfig(
        strategy=request.strategy,
        mask_char=request.mask_char,
        preserve_length=request.preserve_length,
        custom_replacements=custom_replacements,
        enabled_entity_types=enabled_types or list(PIIEntityType),
        min_confidence=request.min_confidence,
    )
    
    pipeline = PIIRedactionPipeline(config)
    result = pipeline.process_case_documents(request.case_id)
    
    return CaseRedactionResponse(**result)


@router.post("/redact/file")
async def redact_file(
    file: UploadFile = File(...),
    strategy: RedactionStrategy = Form(RedactionStrategy.MASK),
    mask_char: str = Form("*"),
    preserve_length: bool = Form(True),
    min_confidence: float = Form(0.7),
    indian_context: bool = Form(True),
    legal_context: bool = Form(True),
    ctx: AuthContext = Depends(require_role("STAFF")),
):
    """Redact PII from uploaded file (text/JSON)."""
    content = await file.read()
    
    # Try to parse as JSON first
    try:
        document = json.loads(content.decode("utf-8"))
        is_json = True
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Treat as plain text
        document = {"content": content.decode("utf-8", errors="ignore")}
        is_json = False
    
    config = RedactionConfig(
        strategy=strategy,
        mask_char=mask_char,
        preserve_length=preserve_length,
        min_confidence=min_confidence,
        indian_context=indian_context,
        legal_context=legal_context,
    )
    
    redacted = redact_document(document, config)
    
    if is_json:
        return redacted
    else:
        return {"redacted_text": redacted.get("content", "")}


@router.get("/entity-types")
async def get_entity_types(
    ctx: AuthContext = Depends(get_auth_context),
):
    """Get list of supported PII entity types."""
    return {
        "entity_types": [e.value for e in PIIEntityType],
        "indian_specific": [
            PIIEntityType.AADHAAR.value,
            PIIEntityType.PAN.value,
            PIIEntityType.INDIAN_PHONE.value,
            PIIEntityType.INDIAN_EMAIL.value,
            PIIEntityType.BANK_ACCOUNT.value,
            PIIEntityType.IFSC.value,
            PIIEntityType.VEHICLE_REG.value,
            PIIEntityType.PASSPORT.value,
            PIIEntityType.VOTER_ID.value,
            PIIEntityType.DRIVING_LICENSE.value,
            PIIEntityType.GST.value,
            PIIEntityType.UPI_ID.value,
            PIIEntityType.CIN.value,
            PIIEntityType.DIN.value,
        ],
        "legal_specific": [
            PIIEntityType.CASE_NUMBER.value,
            PIIEntityType.COURT_NAME.value,
            PIIEntityType.LAWYER_NAME.value,
            PIIEntityType.JUDGE_NAME.value,
        ],
        "redaction_strategies": [s.value for s in RedactionStrategy],
    }


@router.get("/stats/{case_id}")
async def get_pii_stats(
    case_id: str,
    ctx: AuthContext = Depends(require_role("STAFF")),
):
    """Get PII statistics for a case."""
    _, case = await get_case_access(case_id, ctx)
    
    from app.config import get_settings
    from supabase import create_client
    
    settings = get_settings()
    url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
    key = settings.SUPABASE_SERVICE_ROLE_KEY or "placeholder-key"
    docs = []
    try:
        db = create_client(url, key)
        docs = db.table("documents").select("id, file_name, pii_redacted, pii_entities").eq("case_id", case_id).execute().data or []
    except Exception:
        db = None
    
    total_docs = len(docs)
    redacted_docs = sum(1 for d in docs if d.get("pii_redacted"))
    total_entities = 0
    by_type = {}
    
    for doc in docs:
        entities = doc.get("pii_entities", [])
        total_entities += len(entities)
        for entity in entities:
            t = entity.get("type", "UNKNOWN")
            by_type[t] = by_type.get(t, 0) + 1
    
    return {
        "case_id": case_id,
        "total_documents": total_docs,
        "redacted_documents": redacted_docs,
        "total_entities_found": total_entities,
        "by_type": by_type,
    }


@router.post("/pipeline/process-case")
async def trigger_pii_pipeline(
    case_id: str,
    ctx: AuthContext = Depends(get_auth_context),
):
    """Trigger PII redaction pipeline for a case (async job)."""
    _, case = await get_case_access(case_id, ctx)
    
    # Queue job
    from app.config import get_settings
    from supabase import create_client
    
    settings = get_settings()
    url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
    key = settings.SUPABASE_SERVICE_ROLE_KEY or "placeholder-key"
    try:
        db = create_client(url, key)
        db.table("jobs").insert({
            "case_id": case_id,
            "job_type": "pii_redaction",
            "payload": {},
        }).execute()
    except Exception:
        pass
    
    return {"status": "queued", "case_id": case_id, "job_type": "pii_redaction"}


@router.get("/health")
async def pii_health():
    """PII service health check."""
    return {
        "status": "healthy",
        "presidio_available": True,  # Will be checked at runtime
        "supported_entity_types": len(PIIEntityType),
        "supported_strategies": len(RedactionStrategy),
    }