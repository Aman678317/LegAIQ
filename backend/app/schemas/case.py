"""Case, Matter Vault, Citation Grounding, and Indian Legal Intelligence Schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class GroundingCitation(BaseModel):
    """Strict interactive citation linking findings to document evidence."""
    document_id: Union[UUID, str] = Field(description="UUID or string identifier of the source document in Matter Vault")
    document_name: str = Field(description="Filename or title of the cited document (e.g., 'Registered_Sale_Deed_1994.pdf')")
    page_number: int = Field(default=1, ge=1, description="1-indexed page number in the source document")
    source_passage: str = Field(default="", description="Verbatim source passage extracted from the document")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="OCR / parsing confidence score for the citation")
    bounding_box: Optional[Dict[str, Any]] = Field(default=None, description="Optional bounding box coordinates {x, y, w, h} on page")

    @property
    def citation_tag(self) -> str:
        """Formatted canonical citation tag [Doc: <name>, Pg: <number>]."""
        return f"[Doc: {self.document_name}, Pg: {self.page_number}]"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": str(self.document_id),
            "document_name": self.document_name,
            "page_number": self.page_number,
            "source_passage": self.source_passage,
            "source_text": self.source_passage,
            "confidence": self.confidence,
            "bounding_box": self.bounding_box,
            "citation_tag": self.citation_tag,
        }


class LegalContext(BaseModel):
    """Persistent Matter-Centric Context grounding all AI reasoning & agent workflows."""
    case_id: Union[UUID, str] = Field(description="Unique case / matter identifier")
    client_name: str = Field(default="Unknown Client", description="Client or matter party name")
    jurisdiction: str = Field(default="Supreme Court of India", description="Jurisdictional state / high court")
    court: str = Field(default="High Court", description="Target court or forum")
    acts_applicable: List[str] = Field(
        default_factory=lambda: [
            "Transfer of Property Act, 1882",
            "Registration Act, 1908",
            "Bharatiya Sakshya Adhiniyam, 2023",
            "Code of Civil Procedure, 1908",
        ],
        description="Applicable statutory acts for statutory grounding",
    )
    document_ids: List[Union[UUID, str]] = Field(default_factory=list, description="List of associated Matter Vault document IDs")
    evidence_graph_id: Optional[Union[UUID, str]] = Field(default=None, description="UUID of associated evidence graph or DAG")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional matter-specific metadata and parameters")


class DeedRecord(BaseModel):
    """Structured property deed record in the historical conveyance chain."""
    deed_id: Optional[Union[UUID, str]] = Field(default_factory=lambda: str(uuid4()))
    document_name: str = Field(description="Source deed document name")
    document_number: Optional[str] = Field(default=None, description="Registration number (e.g. 'DOC/1994/0842')")
    execution_date: Optional[str] = Field(default=None, description="Execution date in ISO format (YYYY-MM-DD)")
    registration_date: Optional[str] = Field(default=None, description="Registration date in ISO format")
    transaction_type: str = Field(default="SALE_DEED", description="SALE_DEED | PARTITION_DEED | GIFT_DEED | INHERITANCE_MUTATION | MORTGAGE_CHARGE | RELEASE_DEED")
    grantor: str = Field(default="", description="Transferor / Seller / Grantor name")
    grantee: str = Field(default="", description="Transferee / Buyer / Grantee name")
    survey_numbers: List[str] = Field(default_factory=list, description="Survey / Gat / Khasra / CTS numbers")
    area_extent: Optional[str] = Field(default=None, description="Raw or normalized land area extent")
    consideration_amount: Optional[str] = Field(default=None, description="Transaction consideration amount in INR")
    sro_location: Optional[str] = Field(default=None, description="Sub-Registrar Office jurisdictional location")
    citations: List[GroundingCitation] = Field(default_factory=list, description="Verified source citations for this deed")


class FindingSchema(BaseModel):
    """Legal finding with verified evidentiary citation grounding."""
    id: Optional[str] = None
    case_id: Union[UUID, str]
    category: str = Field(default="TITLE_VERIFICATION", description="Finding category")
    title: str = Field(description="Short title of the finding")
    description: str = Field(description="Detailed finding explanation with statutory citations")
    severity: str = Field(default="MEDIUM", description="CRITICAL | HIGH | MEDIUM | LOW | INFORMATIONAL")
    statutes_cited: List[str] = Field(default_factory=list)
    citations: List[GroundingCitation] = Field(default_factory=list)
    created_at: Optional[str] = None


class RiskSchema(BaseModel):
    """Identified legal or title risk with source grounding."""
    id: Optional[str] = None
    case_id: Union[UUID, str]
    level: str = Field(default="HIGH", description="CRITICAL | HIGH | MEDIUM | LOW")
    category: str = Field(default="TITLE_DISCREPANCY")
    title: str
    description: str
    recommended_mitigation: Optional[str] = None
    citations: List[GroundingCitation] = Field(default_factory=list)
    resolved: bool = False


class CaseQAResponse(BaseModel):
    """Case Q&A response with strict interactive citation grounding."""
    id: str
    case_id: Union[UUID, str]
    role: str = "assistant"
    mode: str = "ask"
    content: str
    citations: List[GroundingCitation] = Field(default_factory=list)
    india_context: bool = True
    model: Optional[str] = None
    created_at: Optional[str] = None


class TitleChainDAGSchema(BaseModel):
    """13-30 Year Title Ownership Reconstruction DAG."""
    case_id: Union[UUID, str]
    search_span_years: int = 30
    is_30_year_search_complete: bool = True
    title_status: str = Field(default="CLEAR", description="CLEAR | CONDITIONAL | DEFECTIVE")
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    gaps: List[Dict[str, Any]] = Field(default_factory=list)
    timeline: List[Dict[str, Any]] = Field(default_factory=list)


class BSACertificateSchema(BaseModel):
    """Bharatiya Sakshya Adhiniyam 2023 Section 63 Electronic Evidence Certificate."""
    certificate_id: str
    case_id: Union[UUID, str]
    case_name: str
    issued_at: str
    master_audit_hash: str
    custodian: Dict[str, Any]
    statutory_framework: Dict[str, Any]
    certifications: Dict[str, bool]
    certified_documents: List[Dict[str, Any]]
    statutory_declaration: str
