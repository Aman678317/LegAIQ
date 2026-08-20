"""Bharatiya Sakshya Adhiniyam 2023 - Evidence Admissibility Engine.

Implements evidence admissibility rules under the Bharatiya Sakshya Adhiniyam, 2023
(replacing the Indian Evidence Act, 1872) for legal document validation.

Key Sections Implemented:
- Section 3: Interpretation clause (evidence, document, electronic record)
- Section 22: Oral admissions - when relevant
- Section 23: Admissions in civil cases - when relevant
- Section 27: Confession by accused - when relevant
- Section 31: Admissions not conclusive proof
- Section 32: Statements by persons who cannot be called as witnesses
- Section 33: Relevancy of certain evidence in subsequent proceedings
- Section 45: Opinions of experts
- Section 57: Primary evidence
- Section 58: Secondary evidence
- Section 59: Proof of documents by primary evidence
- Section 60: Cases in which secondary evidence admissible
- Section 61: Rules for electronic records
- Section 62: Admissibility of electronic records
- Section 63: Proof of electronic records
- Section 94: Presumption as to documents (30+ years old)
- Section 95: Presumption as to electronic agreements
- Section 96: Presumption as to electronic records and signatures
- Section 97: Presumption as to certified copies
- Section 99: Presumption as to telegraphic messages
- Section 100: Presumption as to documents not produced
- Section 114: Court may presume existence of certain facts

Also implements DPDP Act 2023 compliance for personal data handling in evidence.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4


class EvidenceType(str, Enum):
    """Types of evidence under BSA 2023."""
    ORAL = "oral"
    DOCUMENTARY = "documentary"
    ELECTRONIC = "electronic"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    EXPERT_OPINION = "expert_opinion"
    PRESUMPTION = "presumption"
    ADMISSION = "admission"
    CONFESSION = "confession"
    HEARSAY_EXCEPTION = "hearsay_exception"


class AdmissibilityStatus(str, Enum):
    """Admissibility determination."""
    ADMISSIBLE = "admissible"
    INADMISSIBLE = "inadmissible"
    CONDITIONALLY_ADMISSIBLE = "conditionally_admissible"
    REQUIRES_FOUNDATION = "requires_foundation"
    PRIVILEGED = "privileged"
    HEARSAY = "hearsay"


class DocumentCategory(str, Enum):
    """Document categories for presumptions."""
    PUBLIC_DOCUMENT = "public_document"
    PRIVATE_DOCUMENT = "private_document"
    ELECTRONIC_RECORD = "electronic_record"
    CERTIFIED_COPY = "certified_copy"
    ANCIENT_DOCUMENT = "ancient_document"  # 30+ years old
    REGISTERED_DOCUMENT = "registered_document"
    REVENUE_RECORD = "revenue_record"
    COURT_ORDER = "court_order"


@dataclass
class EvidenceItem:
    """A piece of evidence with metadata for admissibility analysis."""
    evidence_id: str
    evidence_type: EvidenceType
    description: str
    source: str  # Origin of evidence
    date_created: Optional[datetime] = None
    date_received: Optional[datetime] = None
    
    # Document-specific
    document_category: Optional[DocumentCategory] = None
    is_original: bool = True
    is_certified_copy: bool = False
    custodian: Optional[str] = None
    chain_of_custody: List[str] = field(default_factory=list)
    
    # Electronic record specific
    hash_value: Optional[str] = None
    algorithm: str = "SHA-256"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # DPDP Act compliance
    contains_personal_data: bool = False
    data_principal_consent: bool = False
    lawful_basis: Optional[str] = None  # Section 4, 7, etc.
    retention_period_days: Optional[int] = None
    dpdp_compliant: bool = True
    dpdp_issues: List[str] = field(default_factory=list)
    
    # Admissibility analysis (populated by engine)
    admissibility_status: AdmissibilityStatus = AdmissibilityStatus.REQUIRES_FOUNDATION
    applicable_sections: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    objections: List[str] = field(default_factory=list)
    weight_assessment: Optional[str] = None


@dataclass
class AdmissibilityReport:
    """Complete admissibility analysis report."""
    report_id: str
    case_id: str
    generated_at: datetime
    evidence_items: List[EvidenceItem]
    
    # Summary
    total_items: int = 0
    admissible_count: int = 0
    inadmissible_count: int = 0
    conditionally_admissible_count: int = 0
    requires_foundation_count: int = 0
    
    # Key findings
    critical_gaps: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # DPDP compliance
    dpdp_compliant: bool = True
    dpdp_issues: List[str] = field(default_factory=list)


class BharatiyaSakshyaEngine:
    """Evidence admissibility engine under Bharatiya Sakshya Adhiniyam, 2023."""
    
    # Section references for quick lookup
    SECTIONS = {
        "interpretation": "3",
        "oral_admissions": "22",
        "civil_admissions": "23",
        "confession": "27",
        "admissions_not_conclusive": "31",
        "dying_declaration": "32",
        "subsequent_proceedings": "33",
        "expert_opinion": "45",
        "primary_evidence": "57",
        "secondary_evidence": "58",
        "proof_primary": "59",
        "secondary_when_admissible": "60",
        "electronic_records_rules": "61",
        "electronic_admissibility": "62",
        "electronic_proof": "63",
        "ancient_documents": "94",
        "electronic_agreements": "95",
        "electronic_records_signatures": "96",
        "certified_copies": "97",
        "telegraphic": "99",
        "documents_not_produced": "100",
        "court_presumptions": "114",
    }
    
    def __init__(self):
        self.ancient_document_threshold_years = 30
    
    def analyze_evidence(self, evidence: EvidenceItem) -> EvidenceItem:
        """Analyze a single piece of evidence for admissibility."""
        evidence = self._check_documentary_evidence(evidence)
        evidence = self._check_electronic_evidence(evidence)
        evidence = self._check_hearsay_exceptions(evidence)
        evidence = self._check_privilege(evidence)
        evidence = self._check_dpdp_compliance(evidence)
        evidence = self._determine_final_status(evidence)
        return evidence
    
    def _check_documentary_evidence(self, evidence: EvidenceItem) -> EvidenceItem:
        """Check documentary evidence rules (Sections 57-60, 94, 97)."""
        if evidence.evidence_type not in (EvidenceType.DOCUMENTARY, EvidenceType.ELECTRONIC):
            return evidence
        
        evidence.applicable_sections.append(self.SECTIONS["primary_evidence"])
        evidence.applicable_sections.append(self.SECTIONS["secondary_evidence"])
        
        # Section 57: Primary evidence - original document
        if evidence.is_original:
            evidence.admissibility_status = AdmissibilityStatus.ADMISSIBLE
            evidence.applicable_sections.append(self.SECTIONS["proof_primary"])
            evidence.conditions.append("Original document produced - primary evidence under Section 57")
        
        # Section 58: Secondary evidence - copies
        elif not evidence.is_original:
            evidence.applicable_sections.append(self.SECTIONS["secondary_when_admissible"])
            evidence.admissibility_status = AdmissibilityStatus.CONDITIONALLY_ADMISSIBLE
            evidence.conditions.append("Secondary evidence - requires foundation under Section 60")
            
            # Check conditions for secondary evidence
            if evidence.is_certified_copy:
                evidence.applicable_sections.append(self.SECTIONS["certified_copies"])
                evidence.conditions.append("Certified copy - admissible under Section 97")
            else:
                evidence.objections.append("Uncertified copy - may require original or explanation for non-production")
        
        # Section 94: Ancient documents (30+ years old)
        if evidence.date_created:
            age = datetime.now(timezone.utc) - evidence.date_created.replace(tzinfo=timezone.utc)
            if age.days >= self.ancient_document_threshold_years * 365:
                evidence.document_category = DocumentCategory.ANCIENT_DOCUMENT
                evidence.applicable_sections.append(self.SECTIONS["ancient_documents"])
                evidence.conditions.append(
                    f"Ancient document ({age.days//365} years old) - "
                    f"presumption of genuineness under Section 94"
                )
                if evidence.admissibility_status == AdmissibilityStatus.CONDITIONALLY_ADMISSIBLE:
                    evidence.admissibility_status = AdmissibilityStatus.ADMISSIBLE
        
        # Public documents (revenue records, court orders, registered docs)
        if evidence.document_category in (
            DocumentCategory.REVENUE_RECORD,
            DocumentCategory.COURT_ORDER,
            DocumentCategory.REGISTERED_DOCUMENT,
            DocumentCategory.PUBLIC_DOCUMENT,
        ):
            evidence.applicable_sections.append(self.SECTIONS["certified_copies"])
            evidence.conditions.append("Public document - certified copy admissible under Section 97")
            if evidence.is_certified_copy:
                evidence.admissibility_status = AdmissibilityStatus.ADMISSIBLE
        
        return evidence
    
    def _check_electronic_evidence(self, evidence: EvidenceItem) -> EvidenceItem:
        """Check electronic evidence rules (Sections 61-63, 95, 96)."""
        if evidence.evidence_type != EvidenceType.ELECTRONIC:
            return evidence
        
        evidence.applicable_sections.extend([
            self.SECTIONS["electronic_records_rules"],
            self.SECTIONS["electronic_admissibility"],
            self.SECTIONS["electronic_proof"],
        ])
        
        # Section 62: Admissibility of electronic records
        # Requires: certificate under Section 63(4), hash verification, integrity
        evidence.admissibility_status = AdmissibilityStatus.CONDITIONALLY_ADMISSIBLE
        evidence.conditions.append("Electronic record - requires Section 63 certificate")
        
        # Check for Section 63 certificate requirements
        cert_conditions = []
        
        # (a) Computer output produced by computer
        if evidence.metadata.get("computer_generated"):
            cert_conditions.append("Computer output verified")
        
        # (b) Produced during regular use
        if evidence.metadata.get("regular_use"):
            cert_conditions.append("Produced during regular use")
        
        # (c) Information derived from regularly fed data
        if evidence.metadata.get("regular_data_feed"):
            cert_conditions.append("Data regularly fed into system")
        
        # (d) Computer operating properly
        if evidence.metadata.get("system_integrity_verified"):
            cert_conditions.append("System integrity verified")
        
        # Hash verification
        if evidence.hash_value:
            evidence.conditions.append(f"Hash verified ({evidence.algorithm})")
            cert_conditions.append("Hash integrity confirmed")
        else:
            evidence.objections.append("No hash value - integrity cannot be verified")
        
        # Section 63 certificate
        if evidence.metadata.get("section63_certificate"):
            evidence.conditions.append("Section 63 certificate provided")
            evidence.admissibility_status = AdmissibilityStatus.ADMISSIBLE
        else:
            evidence.objections.append("Section 63 certificate required for admissibility")
        
        # Section 95: Electronic agreements (specific to agreements with digital signatures)
        # Only apply if this is an electronic agreement (has digital signature or electronic signature)
        is_electronic_agreement = (
            evidence.metadata.get("digital_signature") 
            or evidence.metadata.get("electronic_signature")
            or evidence.document_category == DocumentCategory.ELECTRONIC_RECORD and evidence.metadata.get("is_agreement")
        )
        if is_electronic_agreement:
            evidence.applicable_sections.append(self.SECTIONS["electronic_agreements"])
            if evidence.metadata.get("digital_signature_verified"):
                evidence.conditions.append("Digital signature verified under Section 96")
            else:
                evidence.objections.append("Digital signature verification required for electronic agreement")
        
        # Section 96: Electronic records and signatures
        if evidence.metadata.get("electronic_signature") or evidence.metadata.get("digital_signature"):
            evidence.applicable_sections.append(self.SECTIONS["electronic_records_signatures"])
            if evidence.metadata.get("signature_verified"):
                evidence.conditions.append("Electronic signature presumed valid under Section 96")
            else:
                evidence.conditions.append("Electronic signature requires verification")
        
        if cert_conditions:
            evidence.conditions.extend(cert_conditions)
        
        return evidence
    
    def _check_hearsay_exceptions(self, evidence: EvidenceItem) -> EvidenceItem:
        """Check hearsay exceptions (Sections 22, 23, 27, 32, 33)."""
        # Section 22: Oral admissions
        if evidence.evidence_type == EvidenceType.ORAL and evidence.metadata.get("admission"):
            evidence.applicable_sections.append(self.SECTIONS["oral_admissions"])
            evidence.conditions.append("Oral admission - relevant under Section 22")
        
        # Section 23: Admissions in civil cases
        if evidence.evidence_type == EvidenceType.ADMISSION:
            evidence.applicable_sections.append(self.SECTIONS["civil_admissions"])
            if evidence.metadata.get("without_prejudice"):
                evidence.objections.append("Without prejudice communication - may be excluded under Section 23")
            else:
                evidence.conditions.append("Admission in civil case - relevant under Section 23")
        
        # Section 27: Confession by accused
        if evidence.evidence_type == EvidenceType.CONFESSION:
            evidence.applicable_sections.append(self.SECTIONS["confession"])
            if evidence.metadata.get("made_to_police"):
                evidence.objections.append("Confession to police officer - inadmissible under Section 27")
            elif evidence.metadata.get("made_in_custody"):
                evidence.conditions.append("Confession in custody - admissible only if leads to discovery")
            else:
                evidence.conditions.append("Voluntary confession - admissible under Section 27")
        
        # Section 31: Admissions not conclusive proof
        if evidence.evidence_type == EvidenceType.ADMISSION:
            evidence.conditions.append("Admission not conclusive proof - may be rebutted (Section 31)")
        
        # Section 32: Statements by unavailable witnesses (dying declarations, etc.)
        if evidence.metadata.get("witness_unavailable"):
            evidence.applicable_sections.append(self.SECTIONS["dying_declaration"])
            reason = evidence.metadata.get("unavailability_reason", "")
            if reason in ("death", "incapacity", "cannot_be_found"):
                evidence.conditions.append(f"Witness unavailable ({reason}) - admissible under Section 32")
            else:
                evidence.objections.append("Witness unavailability reason insufficient for Section 32")
        
        # Section 33: Evidence in subsequent proceedings
        if evidence.metadata.get("prior_proceeding"):
            evidence.applicable_sections.append(self.SECTIONS["subsequent_proceedings"])
            evidence.conditions.append("Prior proceeding evidence - admissible under Section 33 if conditions met")
        
        return evidence
    
    def _check_privilege(self, evidence: EvidenceItem) -> EvidenceItem:
        """Check for privilege (legal professional privilege, etc.)."""
        privilege_types = evidence.metadata.get("privilege", [])
        
        for priv in privilege_types:
            if priv in ("legal_professional", "attorney_client", "work_product"):
                evidence.admissibility_status = AdmissibilityStatus.PRIVILEGED
                evidence.objections.append(f"Legal professional privilege claimed - {priv}")
            elif priv == "without_prejudice":
                evidence.objections.append("Without prejudice privilege - may be excluded")
            elif priv == "settlement_negotiation":
                evidence.objections.append("Settlement negotiation privilege")
        
        return evidence
    
    def _check_dpdp_compliance(self, evidence: EvidenceItem) -> EvidenceItem:
        """Check DPDP Act 2023 compliance for personal data in evidence."""
        if not evidence.contains_personal_data:
            return evidence
        
        evidence.applicable_sections.append("DPDP Act 2023")
        
        # Section 4: Lawful basis
        if evidence.lawful_basis:
            evidence.conditions.append(f"DPDP lawful basis: {evidence.lawful_basis} (Section 4/7)")
        else:
            evidence.dpdp_compliant = False
            evidence.dpdp_issues.append("No lawful basis specified for personal data processing")
        
        # Section 6: Consent (if required)
        if evidence.lawful_basis == "consent" and not evidence.data_principal_consent:
            evidence.dpdp_compliant = False
            evidence.dpdp_issues.append("Consent required but not obtained (Section 6)")
        
        # Section 8: Data retention
        if evidence.retention_period_days:
            evidence.conditions.append(f"Retention period: {evidence.retention_period_days} days")
        else:
            evidence.dpdp_issues.append("No retention period specified (Section 8)")
        
        # Section 9: Data principal rights
        evidence.conditions.append("Data principal rights under Section 9 must be respected")
        
        # Section 16: Cross-border transfer
        if evidence.metadata.get("cross_border_transfer") and not evidence.metadata.get("adequacy_decision"):
            evidence.dpdp_compliant = False
            evidence.dpdp_issues.append("Cross-border transfer without adequacy decision (Section 16)")
        
        return evidence
    
    def _determine_final_status(self, evidence: EvidenceItem) -> EvidenceItem:
        """Determine final admissibility status."""
        # Priority order: PRIVILEGED > INADMISSIBLE > CONDITIONALLY_ADMISSIBLE > ADMISSIBLE
        if evidence.admissibility_status == AdmissibilityStatus.PRIVILEGED:
            return evidence
        
        if evidence.objections and not evidence.conditions:
            evidence.admissibility_status = AdmissibilityStatus.INADMISSIBLE
        elif evidence.objections and evidence.conditions:
            evidence.admissibility_status = AdmissibilityStatus.CONDITIONALLY_ADMISSIBLE
        elif evidence.admissibility_status == AdmissibilityStatus.REQUIRES_FOUNDATION:
            if evidence.conditions:
                evidence.admissibility_status = AdmissibilityStatus.CONDITIONALLY_ADMISSIBLE
        
        # Weight assessment
        if evidence.admissibility_status == AdmissibilityStatus.ADMISSIBLE:
            if evidence.document_category == DocumentCategory.ANCIENT_DOCUMENT:
                evidence.weight_assessment = "High - ancient document presumption (Section 94)"
            elif evidence.is_original:
                evidence.weight_assessment = "High - primary evidence (Section 57)"
            elif evidence.is_certified_copy and evidence.document_category in (
                DocumentCategory.PUBLIC_DOCUMENT, DocumentCategory.REVENUE_RECORD,
                DocumentCategory.COURT_ORDER, DocumentCategory.REGISTERED_DOCUMENT
            ):
                evidence.weight_assessment = "High - certified public document (Section 97)"
            elif evidence.evidence_type == EvidenceType.ELECTRONIC and evidence.metadata.get("section63_certificate"):
                evidence.weight_assessment = "High - electronic record with Section 63 certificate"
            else:
                evidence.weight_assessment = "Moderate - admissible with conditions"
        elif evidence.admissibility_status == AdmissibilityStatus.CONDITIONALLY_ADMISSIBLE:
            evidence.weight_assessment = "Conditional - subject to foundation requirements"
        else:
            evidence.weight_assessment = "Low/Excluded - significant admissibility issues"
        
        return evidence


# ============================================================================
# High-level Analysis Functions
# ============================================================================

def analyze_case_evidence(
    case_id: str,
    evidence_items: List[EvidenceItem],
) -> AdmissibilityReport:
    """Analyze all evidence for a case and generate admissibility report."""
    engine = BharatiyaSakshyaEngine()
    
    analyzed_items = []
    for item in evidence_items:
        analyzed = engine.analyze_evidence(item)
        analyzed_items.append(analyzed)
    
    # Generate report
    report = AdmissibilityReport(
        report_id=f"ADM-{case_id[:8]}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        case_id=case_id,
        generated_at=datetime.now(timezone.utc),
        evidence_items=analyzed_items,
    )
    
    # Calculate summary
    report.total_items = len(analyzed_items)
    for item in analyzed_items:
        if item.admissibility_status == AdmissibilityStatus.ADMISSIBLE:
            report.admissible_count += 1
        elif item.admissibility_status == AdmissibilityStatus.INADMISSIBLE:
            report.inadmissible_count += 1
        elif item.admissibility_status == AdmissibilityStatus.CONDITIONALLY_ADMISSIBLE:
            report.conditionally_admissible_count += 1
        elif item.admissibility_status == AdmissibilityStatus.REQUIRES_FOUNDATION:
            report.requires_foundation_count += 1
    
    # Identify critical gaps
    report.critical_gaps = _identify_critical_gaps(analyzed_items)
    report.recommendations = _generate_recommendations(analyzed_items)
    
    # DPDP compliance
    report.dpdp_compliant = all(item.dpdp_compliant for item in analyzed_items if item.contains_personal_data)
    report.dpdp_issues = [issue for item in analyzed_items for issue in item.dpdp_issues]
    
    return report


def _identify_critical_gaps(items: List[EvidenceItem]) -> List[str]:
    """Identify critical admissibility gaps."""
    gaps = []
    
    # Electronic records without Section 63 certificate
    electronic_no_cert = [
        i for i in items 
        if i.evidence_type == EvidenceType.ELECTRONIC 
        and not i.metadata.get("section63_certificate")
    ]
    if electronic_no_cert:
        gaps.append(
            f"{len(electronic_no_cert)} electronic record(s) lack Section 63 certificate - "
            f"critical for admissibility under BSA 2023"
        )
    
    # Secondary evidence without explanation
    secondary_no_explanation = [
        i for i in items 
        if i.evidence_type in (EvidenceType.DOCUMENTARY, EvidenceType.ELECTRONIC)
        and not i.is_original
        and not i.is_certified_copy
        and "original" not in str(i.metadata).lower()
    ]
    if secondary_no_explanation:
        gaps.append(
            f"{len(secondary_no_explanation)} secondary evidence item(s) without "
            f"explanation for non-production of original (Section 60)"
        )
    
    # Ancient documents not identified
    potential_ancient = [
        i for i in items 
        if i.date_created 
        and (datetime.now(timezone.utc) - i.date_created.replace(tzinfo=timezone.utc)).days 
        >= 30 * 365
        and not any("ancient document" in c.lower() and "section 94" in c.lower() for c in i.conditions)
    ]
    if potential_ancient:
        gaps.append(
            f"{len(potential_ancient)} document(s) may qualify as ancient documents "
            f"(30+ years) but not categorized - missing Section 94 presumption"
        )
    
    # DPDP issues
    dpdp_issues = [i for i in items if i.contains_personal_data and not i.dpdp_compliant]
    if dpdp_issues:
        gaps.append(
            f"{len(dpdp_issues)} evidence item(s) with DPDP Act 2023 compliance issues - "
            f"may affect admissibility"
        )
    
    # Missing chain of custody
    no_custody = [
        i for i in items 
        if i.evidence_type in (EvidenceType.DOCUMENTARY, EvidenceType.ELECTRONIC)
        and not i.chain_of_custody
    ]
    if no_custody:
        gaps.append(
            f"{len(no_custody)} evidence item(s) lack chain of custody documentation"
        )
    
    return gaps


def _generate_recommendations(items: List[EvidenceItem]) -> List[str]:
    """Generate actionable recommendations."""
    recs = []
    
    # Section 63 certificates for electronic records
    electronic_no_cert = [
        i for i in items 
        if i.evidence_type == EvidenceType.ELECTRONIC 
        and not i.metadata.get("section63_certificate")
    ]
    if electronic_no_cert:
        recs.append(
            f"Obtain Section 63 certificates for {len(electronic_no_cert)} electronic record(s) "
            f"from system custodian with hash verification"
        )
    
    # Certified copies for secondary evidence
    secondary_uncertified = [
        i for i in items 
        if i.evidence_type in (EvidenceType.DOCUMENTARY, EvidenceType.ELECTRONIC)
        and not i.is_original
        and not i.is_certified_copy
    ]
    if secondary_uncertified:
        recs.append(
            f"Obtain certified copies for {len(secondary_uncertified)} secondary evidence item(s) "
            f"under Section 97"
        )
    
    # Ancient document identification
    potential_ancient = [
        i for i in items 
        if i.date_created 
        and (datetime.now(timezone.utc) - i.date_created.replace(tzinfo=timezone.utc)).days 
        >= 30 * 365
        and i.document_category != DocumentCategory.ANCIENT_DOCUMENT
    ]
    if potential_ancient:
        recs.append(
            f"Categorize {len(potential_ancient)} document(s) as ancient documents "
            f"to invoke Section 94 presumption of genuineness"
        )
    
    # Chain of custody
    no_custody = [
        i for i in items 
        if i.evidence_type in (EvidenceType.DOCUMENTARY, EvidenceType.ELECTRONIC)
        and not i.chain_of_custody
    ]
    if no_custody:
        recs.append(
            f"Document chain of custody for {len(no_custody)} evidence item(s) "
            f"to establish authenticity and integrity"
        )
    
    # DPDP compliance
    dpdp_issues = [i for i in items if i.contains_personal_data and not i.dpdp_compliant]
    if dpdp_issues:
        recs.append(
            f"Resolve DPDP Act 2023 compliance for {len(dpdp_issues)} evidence item(s) "
            f"with personal data - establish lawful basis, consent, and retention"
        )
    
    # Expert opinions
    expert_items = [i for i in items if i.evidence_type == EvidenceType.EXPERT_OPINION]
    if expert_items:
        recs.append(
            f"Ensure {len(expert_items)} expert opinion(s) comply with Section 45 - "
            f"expert qualification, methodology disclosure, and cross-examination readiness"
        )
    
    return recs


class Section63Certificate(dict):
    """Section 63 electronic evidence certificate supporting dict and attribute access."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        for k, v in self.items():
            setattr(self, k, v)

    def __setitem__(self, key: str, value: Any):
        super().__setitem__(key, value)
        setattr(self, key, value)

    def __getattr__(self, name: str) -> Any:
        if name in self:
            return self[name]
        raise AttributeError(f"'Section63Certificate' object has no attribute '{name}'")


# ============================================================================
# Presumption Helpers
# ============================================================================

def check_section94_presumption(document_date_or_item: Any) -> Tuple[bool, str]:
    """Check if document qualifies for Section 94 presumption (30+ years old).
    
    Polymorphic: Accepts an EvidenceItem, a datetime, an integer year (e.g. 1980 or 35),
    or a date string.
    """
    now = datetime.now(timezone.utc)
    years: float = 0.0

    if isinstance(document_date_or_item, EvidenceItem):
        if document_date_or_item.date_created:
            dt = document_date_or_item.date_created
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            years = (now - dt).total_seconds() / (365.25 * 86400)
        elif "year" in document_date_or_item.metadata:
            y = int(document_date_or_item.metadata["year"])
            years = float(now.year - y) if y > 1000 else float(y)
        else:
            return False, "EvidenceItem has no execution date or year metadata"
    elif isinstance(document_date_or_item, datetime):
        dt = document_date_or_item
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        years = (now - dt).total_seconds() / (365.25 * 86400)
    elif isinstance(document_date_or_item, (int, float)):
        val = float(document_date_or_item)
        if val > 1000:  # e.g., year 1985
            years = float(now.year - val)
        else:  # e.g., 35 years
            years = val
    elif isinstance(document_date_or_item, str):
        try:
            # Try parsing integer/float year
            val = float(document_date_or_item.strip())
            if val > 1000:
                years = float(now.year - val)
            else:
                years = val
        except ValueError:
            try:
                # Try parsing ISO date
                dt = datetime.fromisoformat(document_date_or_item.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                years = (now - dt).total_seconds() / (365.25 * 86400)
            except Exception:
                return False, f"Could not parse document date: {document_date_or_item}"
    else:
        return False, f"Unsupported date format: {type(document_date_or_item)}"

    if years >= 30:
        return True, (
            f"Document is {years:.1f} years old - Section 94 presumption applies: "
            f"document presumed genuine, signatures presumed authentic, "
            f"and document presumed duly executed/attested"
        )
    return False, f"Document is {years:.1f} years old - does not meet 30-year threshold"


def check_section95_presumption(electronic_agreement: Dict[str, Any]) -> Tuple[bool, str]:
    """Check if electronic agreement qualifies for Section 95 presumption."""
    required = [
        "digital_signature",
        "timestamp",
        "certificate_authority",
        "integrity_check",
    ]
    
    met = [r for r in required if electronic_agreement.get(r)]
    
    if len(met) == len(required):
        return True, "Electronic agreement meets Section 95 requirements - presumed valid"
    else:
        missing = set(required) - set(met)
        return False, f"Electronic agreement missing: {', '.join(missing)} for Section 95"


def check_section96_presumption(
    electronic_record: Dict[str, Any],
    electronic_signature: Dict[str, Any],
) -> Tuple[bool, str]:
    """Check if electronic record/signature qualifies for Section 96 presumption."""
    record_reqs = ["hash_verified", "timestamp_verified", "certificate_valid"]
    sig_reqs = ["signature_verified", "certificate_valid", "signer_identified"]
    
    record_met = [r for r in record_reqs if electronic_record.get(r)]
    sig_met = [r for r in sig_reqs if electronic_signature.get(r)]
    
    if len(record_met) == len(record_reqs) and len(sig_met) == len(sig_reqs):
        return True, "Electronic record and signature meet Section 96 - presumed authentic"
    
    missing = []
    if len(record_met) < len(record_reqs):
        missing.extend([f"record: {r}" for r in set(record_reqs) - set(record_met)])
    if len(sig_met) < len(sig_reqs):
        missing.extend([f"signature: {r}" for r in set(sig_reqs) - set(sig_met)])
    
    return False, f"Missing for Section 96: {', '.join(missing)}"


def check_section97_presumption(document_type_or_item: Any, is_certified: Optional[bool] = None) -> Tuple[bool, str]:
    """Check if certified copy qualifies for Section 97 presumption."""
    if isinstance(document_type_or_item, EvidenceItem):
        document_type = document_type_or_item.document_category or DocumentCategory.PRIVATE_DOCUMENT
        is_certified = document_type_or_item.is_certified_copy
    else:
        document_type = document_type_or_item
        is_certified = bool(is_certified)

    public_types = {
        DocumentCategory.PUBLIC_DOCUMENT,
        DocumentCategory.REVENUE_RECORD,
        DocumentCategory.COURT_ORDER,
        DocumentCategory.REGISTERED_DOCUMENT,
        DocumentCategory.CERTIFIED_COPY,
    }
    
    if document_type in public_types and is_certified:
        return True, f"Certified copy of {document_type.value} - Section 97 presumption applies"
    elif document_type in public_types and not is_certified:
        return False, f"Public document ({document_type.value}) but not certified - Section 97 not applicable"
    else:
        return False, f"Document type {document_type.value if hasattr(document_type, 'value') else str(document_type)} not covered by Section 97"


def generate_section63_certificate(
    evidence: Optional[Any] = None,
    custodian_name: Optional[str] = None,
    custodian_designation: Optional[str] = None,
    organization: Optional[str] = None,
    *,
    file_name: Optional[str] = None,
    file_hash: Optional[str] = None,
    hash_algorithm: str = "SHA-256",
    certifier_name: Optional[str] = None,
    certifier_designation: Optional[str] = None,
    system_parameters: Optional[str] = None,
    **kwargs: Any,
) -> Section63Certificate:
    """Generate a Section 63 certificate template for electronic records.
    
    Accepts both positional and keyword argument variations gracefully.
    """
    ev_id = str(uuid4())
    doc_desc = "Electronic Record"
    h_val = file_hash or ""
    algo = hash_algorithm or "SHA-256"
    date_created_iso = None
    system_details = {}
    computer_generated = True
    regular_use = True
    regular_data_feed = True
    system_integrity = True

    if isinstance(evidence, EvidenceItem):
        ev_id = evidence.evidence_id
        doc_desc = evidence.description
        h_val = evidence.hash_value or file_hash or ""
        algo = evidence.algorithm or hash_algorithm or "SHA-256"
        date_created_iso = evidence.date_created.isoformat() if evidence.date_created else None
        system_details = evidence.metadata.get("system_details", {})
        computer_generated = evidence.metadata.get("computer_generated", True)
        regular_use = evidence.metadata.get("regular_use", True)
        regular_data_feed = evidence.metadata.get("regular_data_feed", True)
        system_integrity = evidence.metadata.get("system_integrity_verified", True)
        if not file_name:
            file_name = evidence.description
    elif isinstance(evidence, str):
        file_name = evidence
        doc_desc = f"Electronic Document: {evidence}"

    c_name = custodian_name or certifier_name or kwargs.get("name") or "System Custodian"
    c_desig = custodian_designation or certifier_designation or kwargs.get("designation") or "System Administrator / Lead Advocate"
    c_org = organization or system_parameters or kwargs.get("org") or "Jurisiva Legal Intelligence Systems"

    if not file_name:
        file_name = kwargs.get("file_name") or "electronic_record.pdf"

    cert_data = {
        "certificate_id": str(uuid4()),
        "title": "Section 63 Electronic Evidence Certificate",
        "evidence_id": ev_id,
        "file_name": file_name,
        "hash_value": h_val,
        "algorithm": algo,
        "hash_algorithm": algo,
        "is_valid": True,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "custodian": {
            "name": c_name,
            "designation": c_desig,
            "organization": c_org,
        },
        "certifier_name": c_name,
        "certifier_designation": c_desig,
        "organization": c_org,
        "system_parameters": system_parameters or str(system_details),
        "electronic_record": {
            "file_name": file_name,
            "description": doc_desc,
            "hash_algorithm": algo,
            "hash_value": h_val,
            "date_created": date_created_iso,
            "system_details": system_details,
        },
        "certifications": {
            "computer_generated": computer_generated,
            "regular_use": regular_use,
            "regular_data_feed": regular_data_feed,
            "system_integrity": system_integrity,
        },
        "legal_basis": "Section 63, Bharatiya Sakshya Adhiniyam, 2023",
        "statement": (
            "I certify that the electronic record described above was produced by the computer "
            "system during its regular use, that the information was derived from data regularly "
            "fed into the system, and that the system was operating properly at all material times."
        ),
    }

    return Section63Certificate(cert_data)


# ============================================================================
# DPDP Act 2023 Compliance
# ============================================================================

class DPDPLawfulBasis(str, Enum):
    """Lawful bases under DPDP Act 2023 Section 4/7."""
    CONSENT = "consent"  # Section 6
    LEGITIMATE_INTEREST = "legitimate_interest"  # Section 7
    LEGAL_OBLIGATION = "legal_obligation"  # Section 7
    VITAL_INTERESTS = "vital_interests"  # Section 7
    PUBLIC_TASK = "public_task"  # Section 7
    CONTRACT = "contract"  # Section 7


def validate_dpdp_compliance(evidence: EvidenceItem) -> Tuple[bool, List[str]]:
    """Validate DPDP Act 2023 compliance for evidence with personal data."""
    issues = []
    
    if not evidence.contains_personal_data:
        return True, []
    
    # Lawful basis (Section 4/7)
    if not evidence.lawful_basis:
        issues.append("No lawful basis specified (Section 4/7 DPDP Act)")
    elif evidence.lawful_basis == DPDPLawfulBasis.CONSENT.value:
        if not evidence.data_principal_consent:
            issues.append("Consent basis claimed but no consent recorded (Section 6)")
    
    # Purpose limitation (Section 4)
    if not evidence.metadata.get("purpose_specified"):
        issues.append("Processing purpose not specified (Section 4)")
    
    # Data minimization (Section 4)
    if not evidence.metadata.get("minimized"):
        issues.append("Data minimization not confirmed (Section 4)")
    
    # Retention (Section 8)
    if not evidence.retention_period_days:
        issues.append("No retention period specified (Section 8)")
    elif evidence.retention_period_days > 365 * 7:  # 7 years default for legal
        issues.append("Retention period exceeds typical legal requirement (Section 8)")
    
    # Security safeguards (Section 8)
    if not evidence.metadata.get("security_measures"):
        issues.append("Security safeguards not documented (Section 8)")
    
    # Data principal rights (Section 9)
    if not evidence.metadata.get("rights_informed"):
        issues.append("Data principal rights not addressed (Section 9)")
    
    # Cross-border transfer (Section 16)
    if evidence.metadata.get("cross_border_transfer") and not evidence.metadata.get("adequacy_decision"):
        issues.append("Cross-border transfer without adequacy decision (Section 16)")
    
    return len(issues) == 0, issues


# ============================================================================
# Example Usage / Demo
# ============================================================================

if __name__ == "__main__":
    # Demo usage
    from datetime import timedelta
    
    # Create sample evidence items
    evidence_list = [
        EvidenceItem(
            evidence_id="EVD-001",
            evidence_type=EvidenceType.DOCUMENTARY,
            description="Registered Sale Deed No. 1234/2020",
            source="Sub-Registrar Office, Whitefield",
            date_created=datetime(2020, 5, 20, tzinfo=timezone.utc),
            document_category=DocumentCategory.REGISTERED_DOCUMENT,
            is_original=True,
            is_certified_copy=True,
        ),
        EvidenceItem(
            evidence_id="EVD-002",
            evidence_type=EvidenceType.DOCUMENTARY,
            description="RTC Extract (Pahani) - Survey 124/2",
            source="Bhoomi Portal, Karnataka",
            date_created=datetime(2023, 1, 15, tzinfo=timezone.utc),
            document_category=DocumentCategory.REVENUE_RECORD,
            is_original=False,
            is_certified_copy=True,
        ),
        EvidenceItem(
            evidence_id="EVD-003",
            evidence_type=EvidenceType.ELECTRONIC,
            description="Email correspondence regarding property dispute",
            source="Gmail - party@domain.com",
            date_created=datetime(2022, 3, 10, tzinfo=timezone.utc),
            document_category=DocumentCategory.ELECTRONIC_RECORD,
            hash_value="a1b2c3d4e5f6...",
            metadata={
                "section63_certificate": True,
                "digital_signature_verified": True,
                "system_integrity_verified": True,
                "regular_use": True,
            },
        ),
        EvidenceItem(
            evidence_id="EVD-004",
            evidence_type=EvidenceType.DOCUMENTARY,
            description="Ancient family partition deed",
            source="Family archives",
            date_created=datetime(1980, 6, 15, tzinfo=timezone.utc),
            document_category=DocumentCategory.PRIVATE_DOCUMENT,
            is_original=True,
        ),
        EvidenceItem(
            evidence_id="EVD-005",
            evidence_type=EvidenceType.ELECTRONIC,
            description="WhatsApp chat export - property negotiation",
            source="WhatsApp backup",
            date_created=datetime(2023, 8, 20, tzinfo=timezone.utc),
            document_category=DocumentCategory.ELECTRONIC_RECORD,
            hash_value="f6e5d4c3b2a1...",
            metadata={
                "section63_certificate": False,
                "computer_generated": True,
            },
            contains_personal_data=True,
            lawful_basis="legal_obligation",
        ),
    ]
    
    # Analyze
    report = analyze_case_evidence("CASE-2024-001", evidence_list)
    
    # Print report
    print(f"=== ADMISSIBILITY REPORT ===")
    print(f"Report ID: {report.report_id}")
    print(f"Case ID: {report.case_id}")
    print(f"Generated: {report.generated_at.isoformat()}")
    print(f"\n--- SUMMARY ---")
    print(f"Total Items: {report.total_items}")
    print(f"Admissible: {report.admissible_count}")
    print(f"Conditionally Admissible: {report.conditionally_admissible_count}")
    print(f"Requires Foundation: {report.requires_foundation_count}")
    print(f"Inadmissible: {report.inadmissible_count}")
    print(f"DPDP Compliant: {report.dpdp_compliant}")
    
    print(f"\n--- CRITICAL GAPS ---")
    for gap in report.critical_gaps:
        print(f"  - {gap}")
    
    print(f"\n--- RECOMMENDATIONS ---")
    for rec in report.recommendations:
        print(f"  - {rec}")
    
    print(f"\n--- EVIDENCE DETAILS ---")
    for item in report.evidence_items:
        print(f"\n  {item.evidence_id}: {item.description}")
        print(f"    Type: {item.evidence_type.value}")
        print(f"    Status: {item.admissibility_status.value}")
        print(f"    Sections: {', '.join(item.applicable_sections)}")
        print(f"    Conditions: {', '.join(item.conditions) if item.conditions else 'None'}")
        print(f"    Objections: {', '.join(item.objections) if item.objections else 'None'}")
        print(f"    Weight: {item.weight_assessment}")
        if item.dpdp_issues:
            print(f"    DPDP Issues: {', '.join(item.dpdp_issues)}")