"""Contract Intelligence Module.

Clause extraction, risk scoring, redlining, and obligation tracking
for Indian legal contracts under Bharatiya Nagarik Suraksha Sanhita, 2023
and Indian Contract Act, 1872.
"""

import re
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4


class ClauseType(str, Enum):
    """Types of contract clauses."""
    PARTIES = "parties"
    RECITALS = "recitals"
    DEFINITIONS = "definitions"
    SCOPE = "scope"
    TERM = "term"
    TERMINATION = "termination"
    PAYMENT = "payment"
    CONFIDENTIALITY = "confidentiality"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    INDEMNITY = "indemnity"
    LIMITATION_OF_LIABILITY = "limitation_of_liability"
    FORCE_MAJEURE = "force_majeure"
    GOVERNING_LAW = "governing_law"
    DISPUTE_RESOLUTION = "dispute_resolution"
    ASSIGNMENT = "assignment"
    NON_COMPETE = "non_compete"
    NON_SOLICITATION = "non_solicitation"
    WARRANTIES = "warranties"
    REPRESENTATIONS = "representations"
    CONDITIONS_PRECEDENT = "conditions_precedent"
    CONDITIONS_SUBSEQUENT = "conditions_subsequent"
    AMENDMENT = "amendment"
    WAIVER = "waiver"
    SEVERABILITY = "severability"
    ENTIRE_AGREEMENT = "entire_agreement"
    NOTICES = "notices"
    COUNTERPARTS = "counterparts"
    SIGNATURE = "signature"
    SCHEDULES = "schedules"
    ANNEXURES = "annexures"
    STAMP_DUTY = "stamp_duty"
    JURISDICTION = "jurisdiction"
    DATA_PROTECTION = "data_protection"
    TAXATION = "taxation"
    ANTI_BRIBERY = "anti_bribery"
    CUSTOM = "custom"


class RiskLevel(str, Enum):
    """Risk assessment levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEGLIGIBLE = "negligible"


class ObligationType(str, Enum):
    """Types of contractual obligations."""
    PAYMENT = "payment"
    DELIVERY = "delivery"
    PERFORMANCE = "performance"
    REPORTING = "reporting"
    COMPLIANCE = "compliance"
    CONFIDENTIALITY = "confidentiality"
    INSURANCE = "insurance"
    APPROVAL = "approval"
    NOTIFICATION = "notification"
    INDEMNIFICATION = "indemnification"
    CUSTOM = "custom"


class ObligationStatus(str, Enum):
    """Status of obligation tracking."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BREACHED = "breached"
    WAIVED = "waived"
    EXPIRED = "expired"


@dataclass
class ContractClause:
    """Extracted contract clause with metadata."""
    clause_id: str
    clause_type: ClauseType
    title: str
    content: str
    start_position: int
    end_position: int
    page_number: Optional[int] = None
    section_number: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.NEGLIGIBLE
    risk_factors: List[str] = field(default_factory=list)
    obligations: List[str] = field(default_factory=list)  # obligation_ids
    dependencies: List[str] = field(default_factory=list)  # clause_ids this depends on
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContractObligation:
    """Trackable contractual obligation."""
    obligation_id: str
    obligation_type: ObligationType
    description: str
    responsible_party: str  # Party name or "Party A"/"Party B"
    beneficiary_party: str
    due_date: Optional[datetime] = None
    trigger_event: Optional[str] = None
    conditions: List[str] = field(default_factory=list)
    status: ObligationStatus = ObligationStatus.PENDING
    clause_ref: Optional[str] = None  # clause_id
    contract_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RedlineChange:
    """Represents a redline change in contract comparison."""
    change_id: str
    change_type: str  # "insertion", "deletion", "modification", "move"
    original_text: str
    modified_text: str
    clause_id: Optional[str] = None
    position: int = 0
    author: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    accepted: bool = False
    comment: Optional[str] = None


@dataclass
class ContractRiskAssessment:
    """Overall contract risk assessment."""
    contract_id: str
    overall_risk: RiskLevel
    risk_score: float  # 0-100
    clause_risks: Dict[str, RiskLevel] = field(default_factory=dict)  # clause_id -> risk
    critical_issues: List[str] = field(default_factory=list)
    high_risk_issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    compliance_gaps: List[str] = field(default_factory=list)
    assessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ContractDocument:
    """Parsed contract document."""
    contract_id: str
    title: str
    parties: List[Dict[str, str]] = field(default_factory=list)
    contract_type: Optional[str] = None
    execution_date: Optional[datetime] = None
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    governing_law: Optional[str] = None
    jurisdiction: Optional[str] = None
    full_text: str = ""
    clauses: List[ContractClause] = field(default_factory=list)
    obligations: List[ContractObligation] = field(default_factory=list)
    risk_assessment: Optional[ContractRiskAssessment] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Clause Extraction Patterns
# ============================================================================

# More flexible patterns - match clause headers in various formats
CLAUSE_PATTERNS = {
    ClauseType.PARTIES: [
        r"(?:^|\n)(?:PARTIES|PARTY|BETWEEN)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:This Agreement is (?:made|entered into))\b",
    ],
    ClauseType.RECITALS: [
        r"(?:^|\n)(?:RECITALS|WHEREAS|BACKGROUND)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)WHEREAS\b",
    ],
    ClauseType.DEFINITIONS: [
        r"(?:^|\n)(?:DEFINITIONS|INTERPRETATION|DEFINED TERMS)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:\"[A-Z][a-z]+\"\s+means)\b",
    ],
    ClauseType.SCOPE: [
        r"(?:^|\n)(?:SCOPE|SERVICES|WORK|DELIVERABLES)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:Scope of (?:Work|Services|Agreement))\b(?:\s*:|\s*\n)",
    ],
    ClauseType.TERM: [
        r"(?:^|\n)(?:TERM|DURATION|PERIOD)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:Term of (?:Agreement|Contract))\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:This Agreement (?:commences|starts|begins))\b",
    ],
    ClauseType.TERMINATION: [
        r"(?:^|\n)(?:TERMINATION|TERMINATE|END)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:Either party may terminate)\b",
        r"(?:^|\n)(?:Termination (?:for|without) cause)\b(?:\s*:|\s*\n)",
    ],
    ClauseType.PAYMENT: [
        r"(?:^|\n)(?:PAYMENT|COMPENSATION|FEES|CONSIDERATION|PRICE)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:Payment (?:Terms|Schedule|Conditions))\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:In consideration (?:of|for))\b",
    ],
    ClauseType.CONFIDENTIALITY: [
        r"(?:^|\n)(?:CONFIDENTIALITY|NON-DISCLOSURE|CONFIDENTIAL INFORMATION)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:Confidential Information (?:means|includes))\b",
    ],
    ClauseType.INTELLECTUAL_PROPERTY: [
        r"(?:^|\n)(?:INTELLECTUAL PROPERTY|IP RIGHTS|OWNERSHIP)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:Intellectual Property Rights)\b(?:\s*:|\s*\n)",
    ],
    ClauseType.INDEMNITY: [
        r"(?:^|\n)(?:INDEMNITY|INDEMNIFICATION|HOLD HARMLESS)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:shall indemnify (?:and hold harmless)?)\b",
    ],
    ClauseType.LIMITATION_OF_LIABILITY: [
        r"(?:^|\n)(?:LIMITATION OF LIABILITY|LIABILITY CAP|EXCLUSION OF LIABILITY)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:In no event (?:shall|will) (?:either party|we|you) be liable)\b",
    ],
    ClauseType.FORCE_MAJEURE: [
        r"(?:^|\n)(?:FORCE MAJEURE|ACT OF GOD)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:Force Majeure (?:Event|Clause))\b(?:\s*:|\s*\n)",
    ],
    ClauseType.GOVERNING_LAW: [
        r"(?:^|\n)(?:GOVERNING LAW|APPLICABLE LAW|CHOICE OF LAW)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:This Agreement shall be governed by)\b",
    ],
    ClauseType.DISPUTE_RESOLUTION: [
        r"(?:^|\n)(?:DISPUTE RESOLUTION|ARBITRATION|MEDIATION|JURISDICTION)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:Any dispute (?:arising|relating) (?:out of|from|to))\b",
    ],
    ClauseType.ASSIGNMENT: [
        r"(?:^|\n)(?:ASSIGNMENT|ASSIGN|TRANSFER)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:Neither party (?:shall|may) assign)\b",
    ],
    ClauseType.NON_COMPETE: [
        r"(?:^|\n)(?:NON-COMPETE|NON COMPETE|RESTRICTIVE COVENANT)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:shall not compete)\b",
    ],
    ClauseType.NON_SOLICITATION: [
        r"(?:^|\n)(?:NON-SOLICITATION|NON SOLICITATION|SOLICITATION)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:shall not solicit)\b",
    ],
    ClauseType.WARRANTIES: [
        r"(?:^|\n)(?:WARRANTIES|WARRANTY|REPRESENTATIONS AND WARRANTIES)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:represents and warrants)\b",
    ],
    ClauseType.REPRESENTATIONS: [
        r"(?:^|\n)(?:REPRESENTATIONS|REPRESENTATION)\b(?:\s*:|\s*\n)",
    ],
    ClauseType.CONDITIONS_PRECEDENT: [
        r"(?:^|\n)(?:CONDITIONS PRECEDENT|CONDITIONS PRECEDENT TO)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:Condition Precedent)\b(?:\s*:|\s*\n)",
    ],
    ClauseType.CONDITIONS_SUBSEQUENT: [
        r"(?:^|\n)(?:CONDITIONS SUBSEQUENT|CONDITION SUBSEQUENT)\b(?:\s*:|\s*\n)",
    ],
    ClauseType.AMENDMENT: [
        r"(?:^|\n)(?:AMENDMENT|MODIFICATION|VARIATION)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:This Agreement may (?:only )?be amended)\b",
    ],
    ClauseType.WAIVER: [
        r"(?:^|\n)(?:WAIVER|NO WAIVER)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:No waiver (?:of|by))\b",
    ],
    ClauseType.SEVERABILITY: [
        r"(?:^|\n)(?:SEVERABILITY|INVALIDITY)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:If any provision (?:is|shall be) (?:invalid|unenforceable|void))\b",
    ],
    ClauseType.ENTIRE_AGREEMENT: [
        r"(?:^|\n)(?:ENTIRE AGREEMENT|WHOLE AGREEMENT|COMPLETE AGREEMENT)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:This Agreement constitutes the entire)\b",
    ],
    ClauseType.NOTICES: [
        r"(?:^|\n)(?:NOTICES|NOTICE)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:All notices (?:shall|must|will) be)\b",
    ],
    ClauseType.COUNTERPARTS: [
        r"(?:^|\n)(?:COUNTERPARTS|COUNTERPART)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:This Agreement may be executed in counterparts)\b",
    ],
    ClauseType.SIGNATURE: [
        r"(?:^|\n)(?:IN WITNESS WHEREOF|SIGNED|EXECUTED)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:Signature|Signed by)\b",
    ],
    ClauseType.SCHEDULES: [
        r"(?:^|\n)(?:SCHEDULES|SCHEDULE|ANNEXURES|ANNEXURE|EXHIBITS|EXHIBIT)\b(?:\s*:|\s*\n)",
    ],
    ClauseType.ANNEXURES: [
        r"(?:^|\n)(?:ANNEXURES|ANNEXURE|APPENDIX|APPENDICES)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:Annexure [A-Z])\b",
    ],
    ClauseType.STAMP_DUTY: [
        r"(?:^|\n)(?:STAMP DUTY|STAMP ACT|REGISTRATION CHARGES)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:stamp duty (?:shall be paid|payable|borne))\b",
    ],
    ClauseType.JURISDICTION: [
        r"(?:^|\n)(?:JURISDICTION|COURTS|VENUE|FORUM)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:The courts at [A-Z][a-zA-Z\s]+ shall have exclusive jurisdiction)\b",
    ],
    ClauseType.DATA_PROTECTION: [
        r"(?:^|\n)(?:DATA PROTECTION|PRIVACY|DATA PRIVACY|DPDP)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:Digital Personal Data Protection Act|personal data processing)\b",
    ],
    ClauseType.TAXATION: [
        r"(?:^|\n)(?:TAXES|TAXATION|GST|WITHHOLDING TAX|TDS)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:All taxes|Goods and Services Tax|Section 194)\b",
    ],
    ClauseType.ANTI_BRIBERY: [
        r"(?:^|\n)(?:ANTI-BRIBERY|ANTI CORRUPTION|CORRUPT PRACTICES|FCPA)\b(?:\s*:|\s*\n)",
        r"(?:^|\n)(?:Prevention of Corruption Act|anti-bribery laws)\b",
    ],
}


# Risk factor keywords for automatic risk scoring
RISK_KEYWORDS = {
    RiskLevel.CRITICAL: [
        "unlimited liability", "unlimited indemnity", "indemnify and hold harmless",
        "gross negligence exclusion", "wilful misconduct", "no limitation",
        "perpetual", "irrevocable", "absolute discretion", "sole discretion",
        "terminate without cause", "terminate immediately", "material breach",
        "liquidated damages", "penalty clause", "joint and several liability",
    ],
    RiskLevel.HIGH: [
        "broad indemnity", "uncapped liability", "consequential damages",
        "indirect damages", "loss of profits", "loss of revenue",
        "terminate for convenience", "change of control", "assignment without consent",
        "non-compete", "restrictive covenant", "exclusive", "sole source",
        "most favored nation", "price escalation", "automatic renewal",
    ],
    RiskLevel.MEDIUM: [
        "reasonable efforts", "best efforts", "commercially reasonable",
        "material adverse change", "force majeure", "confidential information",
        "intellectual property", "warranty", "representation", "covenant",
        "audit right", "inspection right", "insurance", "compliance",
    ],
    RiskLevel.LOW: [
        "notice", "governing law", "jurisdiction", "counterparts",
        "severability", "waiver", "amendment", "assignment with consent",
        "headings", "interpretation", "definitions",
    ],
}


# Indian law specific patterns
INDIAN_CONTRACT_PATTERNS = {
    "stamp_duty": r"(?:stamp duty|Stamp Act|Indian Stamp Act)",
    "registration": r"(?:Registration Act|registered|sub-registrar)",
    "arbitration_act": r"(?:Arbitration and Conciliation Act|Arbitration Act)",
    "specific_relief": r"(?:Specific Relief Act)",
    "contract_act": r"(?:Indian Contract Act|Contract Act, 1872)",
    "companies_act": r"(?:Companies Act, 2013|Companies Act)",
    "gst": r"(?:GST|Goods and Services Tax|CGST|SGST|IGST)",
    "tds": r"(?:TDS|Tax Deducted at Source|Section 194)",
    "foreign_exchange": r"(?:FEMA|Foreign Exchange Management Act)",
    "competition_act": r"(?:Competition Act, 2002)",
    "insolvency": r"(?:Insolvency and Bankruptcy Code|IBC)",
    "data_protection": r"(?:DPDP|Digital Personal Data Protection|Data Protection)",
}


class ContractIntelligenceEngine:
    """Contract intelligence engine for clause extraction, risk scoring, and redlining."""

    def __init__(self):
        self.clause_counter = 0

    def extract_clauses(self, text: str, contract_id: str = "") -> List[ContractClause]:
        """Extract clauses from contract text using pattern matching."""
        clauses = []
        self.clause_counter = 0

        # Normalize text
        normalized = self._normalize_text(text)
        print(f"DEBUG extract_clauses: normalized length = {len(normalized)}")

        # Find clause boundaries
        clause_positions = self._find_clause_boundaries(normalized)
        print(f"DEBUG extract_clauses: clause_positions = {len(clause_positions)}")

        for i, (clause_type, start_pos, end_pos, title) in enumerate(clause_positions):
            content = normalized[start_pos:end_pos].strip()

            if not content or len(content) < 20:
                continue

            self.clause_counter += 1
            clause_id = f"{contract_id}-CL-{self.clause_counter:03d}" if contract_id else f"CL-{self.clause_counter:03d}"

            # Assess risk
            risk_level, risk_factors = self._assess_clause_risk(content, clause_type)

            # Extract obligations from clause
            obligation_ids = self._extract_obligation_refs(content)

            clause = ContractClause(
                clause_id=clause_id,
                clause_type=clause_type,
                title=title,
                content=content,
                start_position=start_pos,
                end_position=end_pos,
                risk_level=risk_level,
                risk_factors=risk_factors,
                obligations=obligation_ids,
            )
            clauses.append(clause)

        return clauses

    def _normalize_text(self, text: str) -> str:
        """Normalize contract text for processing."""
        # Replace multiple spaces/newlines
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\r", "\n", text)
        text = re.sub(r"\t", " ", text)
        # Strip leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        # Replace multiple spaces
        text = re.sub(r" {2,}", " ", text)
        return text

    def _find_clause_boundaries(self, text: str) -> List[Tuple[ClauseType, int, int, str]]:
        """Find clause boundaries using pattern matching."""
        boundaries = []

        for clause_type, patterns in CLAUSE_PATTERNS.items():
            for pattern in patterns:
                matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
                for match in matches:
                    start = match.start()
                    # Find end (next clause or end of text)
                    end = self._find_clause_end(text, start, match.end())
                    title = self._extract_clause_title(text[start:end])
                    boundaries.append((clause_type, start, end, title))

        # Sort by position
        boundaries.sort(key=lambda x: x[1])

        # Merge overlapping/adjacent boundaries of same type
        merged = []
        for b in boundaries:
            if merged and b[1] <= merged[-1][2] + 50 and b[0] == merged[-1][0]:
                # Extend previous
                merged[-1] = (merged[-1][0], merged[-1][1], max(merged[-1][2], b[2]), merged[-1][3])
            else:
                merged.append(b)

        return merged

    def _find_clause_end(self, text: str, start: int, match_end: int) -> int:
        """Find the end of a clause."""
        # Look for next clause header or end of text
        next_positions = []

        for patterns in CLAUSE_PATTERNS.values():
            for pattern in patterns:
                for match in re.finditer(pattern, text[match_end:], re.IGNORECASE | re.MULTILINE):
                    next_positions.append(match_end + match.start())

        if next_positions:
            return min(next_positions)

        # If no next clause, go to end or reasonable length
        return min(len(text), match_end + 5000)

    def _extract_clause_title(self, text: str) -> str:
        """Extract clause title from text."""
        lines = text.strip().split("\n")
        for line in lines[:3]:
            line = line.strip()
            if line and len(line) < 100:
                # Remove numbering
                line = re.sub(r"^[\d\.\)\s]+", "", line)
                return line[:80]
        return "Untitled Clause"

    def _assess_clause_risk(self, content: str, clause_type: ClauseType) -> Tuple[RiskLevel, List[str]]:
        """Assess risk level of a clause based on content."""
        content_lower = content.lower()
        risk_factors = []

        # Check critical risk keywords
        for keyword in RISK_KEYWORDS[RiskLevel.CRITICAL]:
            if keyword in content_lower:
                risk_factors.append(f"Critical: '{keyword}'")
                return RiskLevel.CRITICAL, risk_factors

        # Check high risk keywords
        for keyword in RISK_KEYWORDS[RiskLevel.HIGH]:
            if keyword in content_lower:
                risk_factors.append(f"High: '{keyword}'")

        if risk_factors:
            return RiskLevel.HIGH, risk_factors

        # Check medium risk keywords
        for keyword in RISK_KEYWORDS[RiskLevel.MEDIUM]:
            if keyword in content_lower:
                risk_factors.append(f"Medium: '{keyword}'")

        if risk_factors:
            return RiskLevel.MEDIUM, risk_factors

        # Check low risk keywords
        for keyword in RISK_KEYWORDS[RiskLevel.LOW]:
            if keyword in content_lower:
                risk_factors.append(f"Low: '{keyword}'")

        if risk_factors:
            return RiskLevel.LOW, risk_factors

        # Indian Statutory Risk Specific Checks
        if clause_type == ClauseType.NON_COMPETE:
            post_term_terms = [
                "post-termination", "post termination", "after termination",
                "following termination", "following termination of employment",
                "upon termination", "upon cessation of services", "cessation of services",
                "following departure", "after departure", "subsequent to disassociation",
                "post disassociation", "post employment", "after employment", "post-employment",
                "months post-termination", "years post-termination",
                "following departure from", "subsequent to resignation",
            ]
            if any(term in content_lower for term in post_term_terms):
                risk_factors.append("Critical: Section 27 Indian Contract Act 1872 void restraint of trade (post-termination non-compete is void ab initio)")
                return RiskLevel.CRITICAL, risk_factors

        if clause_type == ClauseType.DISPUTE_RESOLUTION:
            if any(term in content_lower for term in ["unilateral appointment", "sole discretion to appoint", "exclusive right to appoint arbitrator"]):
                risk_factors.append("High: Unilateral arbitrator appointment invalid under Arbitration Act 1996 §12(5) (Perkins Eastman)")
                return RiskLevel.HIGH, risk_factors

        # Clause-type specific defaults
        type_risk_defaults = {
            ClauseType.INDEMNITY: RiskLevel.HIGH,
            ClauseType.LIMITATION_OF_LIABILITY: RiskLevel.HIGH,
            ClauseType.TERMINATION: RiskLevel.MEDIUM,
            ClauseType.PAYMENT: RiskLevel.MEDIUM,
            ClauseType.CONFIDENTIALITY: RiskLevel.MEDIUM,
            ClauseType.NON_COMPETE: RiskLevel.HIGH,
            ClauseType.INTELLECTUAL_PROPERTY: RiskLevel.HIGH,
            ClauseType.DISPUTE_RESOLUTION: RiskLevel.MEDIUM,
            ClauseType.STAMP_DUTY: RiskLevel.MEDIUM,
            ClauseType.DATA_PROTECTION: RiskLevel.MEDIUM,
            ClauseType.TAXATION: RiskLevel.LOW,
            ClauseType.JURISDICTION: RiskLevel.LOW,
            ClauseType.ANTI_BRIBERY: RiskLevel.MEDIUM,
            ClauseType.FORCE_MAJEURE: RiskLevel.LOW,
            ClauseType.GOVERNING_LAW: RiskLevel.LOW,
        }

        return type_risk_defaults.get(clause_type, RiskLevel.NEGLIGIBLE), risk_factors

    def _extract_obligation_refs(self, content: str) -> List[str]:
        """Extract obligation references from clause content."""
        # Simple extraction - in practice would be more sophisticated
        obligations = []

        # Look for obligation-like patterns
        patterns = [
            r"(?:shall|must|will|agrees? to|undertakes? to)\s+([^.]+)",
            r"(?:obligation|duty|responsibility)\s+(?:to|of)\s+([^.]+)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                obligations.append(match.group(1).strip()[:100])

        return obligations[:5]  # Limit

    def extract_obligations(self, contract: ContractDocument) -> List[ContractObligation]:
        """Extract trackable obligations from contract clauses."""
        obligations = []

        for clause in contract.clauses:
            # Extract obligations from clause content
            clause_obligations = self._parse_obligations_from_clause(clause, contract.contract_id)
            obligations.extend(clause_obligations)

        # Also check for obligations in full text not caught by clauses
        text_obligations = self._parse_obligations_from_text(contract.full_text, contract.contract_id)
        obligations.extend(text_obligations)

        contract.obligations = obligations
        return obligations

    def _parse_obligations_from_clause(self, clause: ContractClause, contract_id: str) -> List[ContractObligation]:
        """Parse obligations from a specific clause."""
        obligations = []
        content = clause.content

        # Pattern for obligations - each pattern is (regex, ob_type, group_map)
        # group_map: dict with keys 'responsible', 'description', 'due_date' mapping to group indices
        obligation_patterns = [
            # "Party shall do X by date"
            (r"(\w+(?:\s+\w+){0,3})\s+(?:shall|must|will|agrees? to)\s+([^.]+?)(?:\s+by\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}))?", ObligationType.PERFORMANCE, {'responsible': 1, 'description': 2, 'due_date': 3}),
            # "Payment of X due by date"
            (r"(?:payment|pay|remit)\s+(?:of\s+)?([^.]+?)(?:\s+(?:by|on|before)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}))", ObligationType.PAYMENT, {'description': 1, 'due_date': 2}),
            # "Deliver X by date"
            (r"(?:deliver|provide|supply|furnish)\s+([^.]+?)(?:\s+(?:by|on|before)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}))", ObligationType.DELIVERY, {'description': 1, 'due_date': 2}),
            # "Report X by date"
            (r"(?:report|notify|inform)\s+([^.]+?)(?:\s+(?:by|on|before)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}))", ObligationType.REPORTING, {'description': 1, 'due_date': 2}),
            # Header-based format: "PAYMENT: Company B pays INR 10,00,000 by 31/03/2024"
            (r"(?:PAYMENT|payment)\s*:\s*(\w+(?:\s+\w+){0,3})\s+(?:pays?|paying)\s+([^.]+?)(?:\s+(?:by|on|before)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}))", ObligationType.PAYMENT, {'responsible': 1, 'description': 2, 'due_date': 3}),
            # Header-based format: "SCOPE: Company A provides consulting"
            (r"(?:SCOPE|scope)\s*:\s*(\w+(?:\s+\w+){0,3})\s+(?:provides?|providing)\s+([^.]+)", ObligationType.PERFORMANCE, {'responsible': 1, 'description': 2}),
            # Header-based format: "TERMINATION: 30 days notice" - treated as performance obligation
            (r"(?:TERMINATION|termination)\s*:\s*([^.]+)", ObligationType.PERFORMANCE, {'description': 1}),
            # Header-based format: "DELIVERY: Company A delivers X by date"
            (r"(?:DELIVERY|delivery)\s*:\s*(\w+(?:\s+\w+){0,3})\s+(?:delivers?|delivering)\s+([^.]+?)(?:\s+(?:by|on|before)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}))", ObligationType.DELIVERY, {'responsible': 1, 'description': 2, 'due_date': 3}),
        ]

        # Extract party names from contract
        parties = [p.get("name", f"Party {chr(65+i)}") for i, p in enumerate(self._extract_parties(content))]

        for pattern, ob_type, group_map in obligation_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                responsible = match.group(group_map.get('responsible')).strip() if group_map.get('responsible') and match.group(group_map['responsible']) else (parties[0] if parties else "Party A")
                description = match.group(group_map.get('description')).strip() if group_map.get('description') and match.group(group_map['description']) else ""
                due_date_str = match.group(group_map.get('due_date')) if group_map.get('due_date') and match.lastindex and match.lastindex >= group_map['due_date'] else None

                due_date = None
                if due_date_str:
                    try:
                        due_date = self._parse_date(due_date_str)
                    except:
                        pass

                obl_id = f"{contract_id}-OBL-{len(obligations)+1:03d}"
                obligations.append(ContractObligation(
                    obligation_id=obl_id,
                    obligation_type=ob_type,
                    description=description,
                    responsible_party=responsible,
                    beneficiary_party=parties[1] if len(parties) > 1 else "Counterparty",
                    due_date=due_date,
                    clause_ref=clause.clause_id,
                    contract_id=contract_id,
                ))

        return obligations

    def _parse_obligations_from_text(self, text: str, contract_id: str) -> List[ContractObligation]:
        """Parse obligations from full contract text."""
        # Additional pass for obligations not in extracted clauses
        return []

    def _extract_parties(self, text: str) -> List[Dict[str, str]]:
        """Extract party names from contract text."""
        parties = []

        # Look for party definitions
        patterns = [
            r"(?:Party|PARTY)\s+([A-Z])\s*[:\-]\s*([^\n,]+)",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*\(?(?:\"[A-Z]\")?\)?",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                name = match.group(2) if match.lastindex >= 2 else match.group(1)
                if name and len(name) > 2:
                    parties.append({"name": name.strip()})

        return parties[:5]  # Limit

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string in various formats."""
        formats = [
            "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
            "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
            "%Y-%m-%d", "%Y/%m/%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
            except:
                continue
        raise ValueError(f"Cannot parse date: {date_str}")

    def assess_risk(self, contract: ContractDocument) -> ContractRiskAssessment:
        """Perform comprehensive risk assessment of contract."""
        clause_risks = {}
        critical_issues = []
        high_risk_issues = []
        recommendations = []
        compliance_gaps = []

        for clause in contract.clauses:
            clause_risks[clause.clause_id] = clause.risk_level

            if clause.risk_level == RiskLevel.CRITICAL:
                critical_issues.append(f"{clause.title}: {', '.join(clause.risk_factors)}")
            elif clause.risk_level == RiskLevel.HIGH:
                high_risk_issues.append(f"{clause.title}: {', '.join(clause.risk_factors)}")

        # Check for missing critical clauses
        required_clauses = [
            ClauseType.TERMINATION,
            ClauseType.GOVERNING_LAW,
            ClauseType.DISPUTE_RESOLUTION,
            ClauseType.CONFIDENTIALITY,
            ClauseType.LIMITATION_OF_LIABILITY,
        ]

        found_types = {c.clause_type for c in contract.clauses}
        for req in required_clauses:
            if req not in found_types:
                compliance_gaps.append(f"Missing {req.value} clause")

        # Check Indian law compliance
        text_lower = contract.full_text.lower()
        if "arbitration" in text_lower and "arbitration act" not in text_lower:
            recommendations.append("Reference Arbitration and Conciliation Act, 1996 in arbitration clause")

        if "stamp duty" not in text_lower and contract.contract_type in ["sale", "lease", "mortgage"]:
            compliance_gaps.append("Stamp duty clause recommended for this contract type")

        # Overall risk calculation
        risk_weights = {
            RiskLevel.CRITICAL: 25,
            RiskLevel.HIGH: 15,
            RiskLevel.MEDIUM: 8,
            RiskLevel.LOW: 3,
            RiskLevel.NEGLIGIBLE: 1,
        }

        total_score = sum(risk_weights.get(r, 0) for r in clause_risks.values())
        risk_score = min(100, total_score)

        if risk_score >= 70:
            overall_risk = RiskLevel.CRITICAL
        elif risk_score >= 50:
            overall_risk = RiskLevel.HIGH
        elif risk_score >= 30:
            overall_risk = RiskLevel.MEDIUM
        elif risk_score >= 15:
            overall_risk = RiskLevel.LOW
        else:
            overall_risk = RiskLevel.NEGLIGIBLE

        # Generate recommendations
        if critical_issues:
            recommendations.append("URGENT: Review critical risk clauses with senior counsel")
        if high_risk_issues:
            recommendations.append("Negotiate high-risk clauses before execution")
        if compliance_gaps:
            recommendations.append("Address compliance gaps for Indian law applicability")

        assessment = ContractRiskAssessment(
            contract_id=contract.contract_id,
            overall_risk=overall_risk,
            risk_score=risk_score,
            clause_risks=clause_risks,
            critical_issues=critical_issues,
            high_risk_issues=high_risk_issues,
            recommendations=recommendations,
            compliance_gaps=compliance_gaps,
        )

        contract.risk_assessment = assessment
        return assessment

    def compare_contracts(
        self,
        original: ContractDocument,
        modified: ContractDocument,
    ) -> List[RedlineChange]:
        """Compare two contract versions and generate redline changes."""
        changes = []

        # Simple diff-based comparison
        # In production, use difflib or specialized diff library
        orig_clauses = {c.clause_id: c for c in original.clauses}
        mod_clauses = {c.clause_id: c for c in modified.clauses}

        all_ids = set(orig_clauses.keys()) | set(mod_clauses.keys())

        for cid in all_ids:
            orig = orig_clauses.get(cid)
            mod = mod_clauses.get(cid)

            if orig and not mod:
                changes.append(RedlineChange(
                    change_id=f"DEL-{cid}",
                    change_type="deletion",
                    original_text=orig.content,
                    modified_text="",
                    clause_id=cid,
                    position=orig.start_position,
                ))
            elif mod and not orig:
                changes.append(RedlineChange(
                    change_id=f"INS-{cid}",
                    change_type="insertion",
                    original_text="",
                    modified_text=mod.content,
                    clause_id=cid,
                    position=mod.start_position,
                ))
            elif orig and mod and orig.content != mod.content:
                changes.append(RedlineChange(
                    change_id=f"MOD-{cid}",
                    change_type="modification",
                    original_text=orig.content,
                    modified_text=mod.content,
                    clause_id=cid,
                    position=orig.start_position,
                ))

        return changes

    def generate_redline_document(
        self,
        original: ContractDocument,
        modified: ContractDocument,
        changes: List[RedlineChange],
    ) -> str:
        """Generate redline document showing changes."""
        # This would generate a formatted document with track changes
        # For now, return a summary
        lines = [
            f"REDLINE COMPARISON: {original.title} vs {modified.title}",
            f"Original Contract ID: {original.contract_id}",
            f"Modified Contract ID: {modified.contract_id}",
            f"Comparison Date: {datetime.now(timezone.utc).isoformat()}",
            "",
            f"Total Changes: {len(changes)}",
            f"  Insertions: {len([c for c in changes if c.change_type == 'insertion'])}",
            f"  Deletions: {len([c for c in changes if c.change_type == 'deletion'])}",
            f"  Modifications: {len([c for c in changes if c.change_type == 'modification'])}",
            "",
            "CHANGES:",
        ]

        for change in changes:
            lines.append(f"\n--- {change.change_type.upper()} ({change.change_id}) ---")
            if change.clause_id:
                lines.append(f"Clause: {change.clause_id}")
            if change.original_text:
                lines.append(f"Original: {change.original_text[:200]}...")
            if change.modified_text:
                lines.append(f"Modified: {change.modified_text[:200]}...")
            if change.comment:
                lines.append(f"Comment: {change.comment}")

        return "\n".join(lines)

    def check_indian_law_compliance(self, contract: ContractDocument) -> List[str]:
        """Check contract for Indian law compliance issues."""
        issues = []
        text_lower = contract.full_text.lower()

        # Check for required Indian law references
        if "governing law" in text_lower:
            if "india" not in text_lower and "indian" not in text_lower:
                issues.append("Governing law clause should specify Indian jurisdiction")

        # Check stamp duty
        contract_types_requiring_stamp = ["sale", "lease", "mortgage", "gift", "partition", "power of attorney"]
        if contract.contract_type and any(t in contract.contract_type.lower() for t in contract_types_requiring_stamp):
            if "stamp duty" not in text_lower:
                issues.append(f"Stamp duty clause required for {contract.contract_type} under Indian Stamp Act")

        # Check registration
        if contract.contract_type and "lease" in contract.contract_type.lower():
            if "registration" not in text_lower:
                issues.append("Lease deeds > 11 months require registration under Registration Act, 1908")

        # Check TDS
        if "payment" in text_lower and "tds" not in text_lower:
            issues.append("Consider TDS provisions under Income Tax Act for payments")

        # Check GST
        if "gst" not in text_lower and "goods and services tax" not in text_lower:
            if any(w in text_lower for w in ["supply", "service", "goods", "consideration"]):
                issues.append("GST clause recommended for commercial contracts")

        # Check data protection
        if "personal data" in text_lower or "personal information" in text_lower:
            if "dpdp" not in text_lower and "data protection" not in text_lower:
                issues.append("DPDP Act 2023 compliance clause needed for personal data processing")

        # Check arbitration
        if "arbitration" in text_lower:
            if "arbitration and conciliation act" not in text_lower:
                issues.append("Reference Arbitration and Conciliation Act, 1996 in arbitration clause")

        return issues

    def generate_risk_heatmap(self, contract: ContractDocument) -> Dict[str, Any]:
        """Generate structured risk heatmap matrix across functional categories."""
        categories = {
            "Liability & Indemnity": [ClauseType.INDEMNITY, ClauseType.LIMITATION_OF_LIABILITY, ClauseType.WARRANTIES],
            "Commercial & Term": [ClauseType.PAYMENT, ClauseType.TERM, ClauseType.TERMINATION, ClauseType.SCOPE],
            "Restrictive Covenants": [ClauseType.NON_COMPETE, ClauseType.NON_SOLICITATION, ClauseType.CONFIDENTIALITY],
            "Compliance & Statutory": [ClauseType.STAMP_DUTY, ClauseType.DATA_PROTECTION, ClauseType.TAXATION, ClauseType.ANTI_BRIBERY],
            "Dispute & Governance": [ClauseType.GOVERNING_LAW, ClauseType.DISPUTE_RESOLUTION, ClauseType.JURISDICTION, ClauseType.ENTIRE_AGREEMENT],
        }

        category_scores: Dict[str, Dict[str, Any]] = {}
        risk_value_map = {
            RiskLevel.CRITICAL: 100,
            RiskLevel.HIGH: 75,
            RiskLevel.MEDIUM: 45,
            RiskLevel.LOW: 20,
            RiskLevel.NEGLIGIBLE: 5,
        }

        for cat_name, clause_types in categories.items():
            cat_clauses = [c for c in contract.clauses if c.clause_type in clause_types]
            if cat_clauses:
                scores = [risk_value_map.get(c.risk_level, 10) for c in cat_clauses]
                avg_score = sum(scores) / len(scores)
                highest_risk = max(cat_clauses, key=lambda c: risk_value_map.get(c.risk_level, 0)).risk_level.value
            else:
                avg_score = 0.0
                highest_risk = "negligible"

            category_scores[cat_name] = {
                "score": round(avg_score, 1),
                "highest_risk": highest_risk,
                "clause_count": len(cat_clauses),
                "clauses": [
                    {
                        "clause_id": c.clause_id,
                        "title": c.title,
                        "type": c.clause_type.value,
                        "risk_level": c.risk_level.value,
                        "risk_factors": c.risk_factors,
                    }
                    for c in cat_clauses
                ],
            }

        return {
            "contract_id": contract.contract_id,
            "overall_score": contract.risk_assessment.risk_score if contract.risk_assessment else 0.0,
            "overall_risk": contract.risk_assessment.overall_risk.value if contract.risk_assessment else "negligible",
            "categories": category_scores,
        }


# ============================================================================
# High-level Analysis Functions
# ============================================================================

def analyze_contract(
    text: str,
    contract_id: str = "",
    title: str = "Contract",
    contract_type: Optional[str] = None,
) -> ContractDocument:
    """Full contract analysis pipeline."""
    if not contract_id:
        contract_id = f"CTR-{uuid4().hex[:8]}"

    engine = ContractIntelligenceEngine()

    # Create contract document
    contract = ContractDocument(
        contract_id=contract_id,
        title=title,
        contract_type=contract_type,
        full_text=text,
    )

    # Extract parties
    contract.parties = engine._extract_parties(text)

    # Extract clauses
    contract.clauses = engine.extract_clauses(text, contract_id)

    # Extract obligations
    contract.obligations = engine.extract_obligations(contract)

    # Assess risk
    contract.risk_assessment = engine.assess_risk(contract)

    # Check Indian law compliance
    contract.metadata["indian_law_compliance"] = engine.check_indian_law_compliance(contract)

    return contract


def track_obligations(
    contract: ContractDocument,
    as_of_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Track obligation status and generate alerts."""
    if as_of_date is None:
        as_of_date = datetime.now(timezone.utc)

    overdue = []
    due_soon = []
    pending = []
    completed = []

    for obl in contract.obligations:
        if obl.status == ObligationStatus.COMPLETED:
            completed.append(obl)
        elif obl.due_date:
            if obl.due_date < as_of_date:
                overdue.append(obl)
            elif obl.due_date <= as_of_date + timedelta(days=7):
                due_soon.append(obl)
            else:
                pending.append(obl)
        else:
            pending.append(obl)

    return {
        "contract_id": contract.contract_id,
        "as_of": as_of_date.isoformat(),
        "summary": {
            "total": len(contract.obligations),
            "overdue": len(overdue),
            "due_soon": len(due_soon),
            "pending": len(pending),
            "completed": len(completed),
        },
        "overdue": [{"id": o.obligation_id, "description": o.description, "due": o.due_date.isoformat() if o.due_date else None, "party": o.responsible_party} for o in overdue],
        "due_soon": [{"id": o.obligation_id, "description": o.description, "due": o.due_date.isoformat() if o.due_date else None, "party": o.responsible_party} for o in due_soon],
        "pending": [{"id": o.obligation_id, "description": o.description, "due": o.due_date.isoformat() if o.due_date else None, "party": o.responsible_party} for o in pending],
    }


# ============================================================================
# Example Usage / Demo
# ============================================================================

if __name__ == "__main__":
    # Demo contract
    sample_contract = """
    SOFTWARE DEVELOPMENT AGREEMENT

    This Software Development Agreement ("Agreement") is made on 15th January 2024
    BETWEEN:
    TechCorp Solutions Private Limited, a company incorporated under the Companies Act, 2013,
    having its registered office at Bangalore, Karnataka ("Client" or "Party A")
    AND
    DevSoft India LLP, a limited liability partnership registered under the LLP Act, 2008,
    having its registered office at Mumbai, Maharashtra ("Developer" or "Party B")

    RECITALS
    WHEREAS, Client desires to engage Developer for custom software development services.
    WHEREAS, Developer represents it has the expertise to deliver such services.

    DEFINITIONS
    "Deliverables" means the software code, documentation, and related materials.
    "Intellectual Property Rights" means all patents, copyrights, trademarks, and trade secrets.

    SCOPE OF WORK
    Developer shall design, develop, test, and deploy a web-based application
    as specified in Schedule A.

    TERM
    This Agreement commences on 15th January 2024 and continues for 12 months
    unless terminated earlier per the Termination clause.

    PAYMENT TERMS
    Client shall pay Developer INR 50,00,000 (Fifty Lakhs) in four milestones:
    Milestone 1: INR 15,00,000 upon signing
    Milestone 2: INR 15,00,000 upon design completion by 15/03/2024
    Milestone 3: INR 10,00,000 upon development completion by 15/06/2024
    Milestone 4: INR 10,00,000 upon deployment by 15/09/2024
    All payments subject to TDS deduction under Section 194J.

    CONFIDENTIALITY
    Both parties shall maintain confidentiality of all proprietary information
    for a period of 3 years post-termination.

    INTELLECTUAL PROPERTY
    All Intellectual Property Rights in the Deliverables shall vest in Client
    upon full payment. Developer retains rights to pre-existing code.

    INDEMNITY
    Developer shall indemnify and hold harmless Client from all claims,
    damages, losses arising from Developer's breach or negligence.
    Developer's liability shall be capped at the total contract value.

    LIMITATION OF LIABILITY
    In no event shall either party be liable for indirect, consequential,
    or punitive damages including loss of profits.

    FORCE MAJEURE
    Neither party shall be liable for delays due to force majeure events
    including natural disasters, government actions, pandemics.

    GOVERNING LAW
    This Agreement shall be governed by the laws of India.
    Courts at Bangalore shall have exclusive jurisdiction.

    DISPUTE RESOLUTION
    Disputes shall be resolved by arbitration under the Arbitration
    and Conciliation Act, 1996. Seat of arbitration: Bangalore.

    TERMINATION
    Either party may terminate for material breach with 30 days notice.
    Client may terminate for convenience with 60 days notice.

    NON-COMPETE
    Developer shall not compete with Client in India for 12 months post-termination.

    ENTIRE AGREEMENT
    This Agreement constitutes the entire understanding between parties.

    IN WITNESS WHEREOF, parties have executed this Agreement.
    """

    # Analyze
    contract = analyze_contract(
        text=sample_contract,
        title="Software Development Agreement",
        contract_type="service agreement",
    )

    # Print results
    print(f"=== CONTRACT ANALYSIS: {contract.title} ===")
    print(f"Contract ID: {contract.contract_id}")
    print(f"Parties: {[p['name'] for p in contract.parties]}")
    print(f"\n--- CLAUSES EXTRACTED ({len(contract.clauses)}) ---")
    for c in contract.clauses:
        print(f"  {c.clause_id}: {c.title} [{c.clause_type.value}] Risk: {c.risk_level.value}")
        if c.risk_factors:
            print(f"    Risk Factors: {', '.join(c.risk_factors)}")

    print(f"\n--- OBLIGATIONS ({len(contract.obligations)}) ---")
    for o in contract.obligations:
        print(f"  {o.obligation_id}: {o.obligation_type.value} - {o.description[:60]}... (Due: {o.due_date})")

    print(f"\n--- RISK ASSESSMENT ---")
    ra = contract.risk_assessment
    print(f"  Overall Risk: {ra.overall_risk.value} (Score: {ra.risk_score}/100)")
    print(f"  Critical Issues: {len(ra.critical_issues)}")
    print(f"  High Risk Issues: {len(ra.high_risk_issues)}")
    for issue in ra.critical_issues[:3]:
        print(f"    CRITICAL: {issue}")
    for issue in ra.high_risk_issues[:3]:
        print(f"    HIGH: {issue}")

    print(f"\n--- RECOMMENDATIONS ---")
    for rec in ra.recommendations:
        print(f"  - {rec}")

    print(f"\n--- COMPLIANCE GAPS ---")
    for gap in ra.compliance_gaps:
        print(f"  - {gap}")

    print(f"\n--- INDIAN LAW COMPLIANCE ---")
    for issue in contract.metadata.get("indian_law_compliance", []):
        print(f"  - {issue}")

    # Track obligations
    print(f"\n--- OBLIGATION TRACKING ---")
    tracking = track_obligations(contract)
    print(f"  Overdue: {tracking['summary']['overdue']}")
    print(f"  Due Soon: {tracking['summary']['due_soon']}")
    print(f"  Pending: {tracking['summary']['pending']}")