"""Firm Playbook Deviation Engine.

Evaluates contracts against firm negotiation playbooks, flags non-compliant terms,
detects missing mandatory clauses, identifies statutory violations (e.g. §27 ICA),
and generates automated redline recommendations with replacement text.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.ai.clause_library import EnterpriseClauseLibrary, PRELOADED_CLAUSE_LIBRARY


@dataclass
class PlaybookRule:
    """Individual playbook rule for a specific clause type."""
    rule_id: str
    clause_type: str
    rule_name: str
    mandatory: bool = True
    standard_position: str = ""
    acceptable_fallbacks: List[str] = field(default_factory=list)
    forbidden_terms: List[str] = field(default_factory=list)
    risk_weight: int = 15  # Deduction on deviation
    recommended_redline: str = ""
    guidance_notes: str = ""
    statutory_reference: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "clause_type": self.clause_type,
            "rule_name": self.rule_name,
            "mandatory": self.mandatory,
            "standard_position": self.standard_position,
            "acceptable_fallbacks": self.acceptable_fallbacks,
            "forbidden_terms": self.forbidden_terms,
            "risk_weight": self.risk_weight,
            "recommended_redline": self.recommended_redline,
            "guidance_notes": self.guidance_notes,
            "statutory_reference": self.statutory_reference,
        }


@dataclass
class ContractPlaybook:
    """Firm standard negotiation playbook containing rules for a contract type."""
    playbook_id: str
    name: str
    description: str
    contract_type: str
    rules: List[PlaybookRule] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "playbook_id": self.playbook_id,
            "name": self.name,
            "description": self.description,
            "contract_type": self.contract_type,
            "rules": [r.to_dict() for r in self.rules],
            "created_at": self.created_at,
        }


@dataclass
class PlaybookDeviation:
    """Identified deviation from a playbook rule."""
    deviation_id: str
    rule_id: str
    clause_type: str
    clause_id: Optional[str] = None
    severity: str = "medium"  # critical, high, medium, low
    deviation_type: str = "unacceptable_deviation"  # missing_mandatory_clause, forbidden_term_detected, statutory_violation, fallback_tier_applied
    current_text: Optional[str] = None
    issue_description: str = ""
    recommended_redline: str = ""
    statutory_reference: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deviation_id": self.deviation_id,
            "rule_id": self.rule_id,
            "clause_type": self.clause_type,
            "clause_id": self.clause_id,
            "severity": self.severity,
            "deviation_type": self.deviation_type,
            "current_text": self.current_text,
            "issue_description": self.issue_description,
            "recommended_redline": self.recommended_redline,
            "statutory_reference": self.statutory_reference,
        }


@dataclass
class PlaybookEvaluationResult:
    """Complete evaluation report of a contract against a playbook."""
    contract_id: str
    playbook_id: str
    playbook_name: str
    compliance_score: float  # 0 to 100
    overall_status: str  # compliant, minor_deviations, high_risk_deviations, walkaway_triggered
    total_rules_evaluated: int
    passed_rules: int
    deviations: List[PlaybookDeviation] = field(default_factory=list)
    redline_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    evaluated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "playbook_id": self.playbook_id,
            "playbook_name": self.playbook_name,
            "compliance_score": round(self.compliance_score, 1),
            "overall_status": self.overall_status,
            "total_rules_evaluated": self.total_rules_evaluated,
            "passed_rules": self.passed_rules,
            "deviations": [d.to_dict() for d in self.deviations],
            "redline_recommendations": self.redline_recommendations,
            "evaluated_at": self.evaluated_at,
        }


# ============================================================================
# Standard Firm Playbooks Preloaded
# ============================================================================

STANDARD_PLAYBOOKS: List[ContractPlaybook] = [
    ContractPlaybook(
        playbook_id="PB-MSA-001",
        name="Enterprise Master Services Agreement (MSA) Playbook",
        description="Firm standard negotiation guidelines for B2B IT, SaaS, and Professional Services contracts in India.",
        contract_type="master_services_agreement",
        rules=[
            PlaybookRule(
                rule_id="RULE-MSA-INDEM",
                clause_type="indemnity",
                rule_name="Indemnity Cap & Direct Losses Only",
                mandatory=True,
                standard_position="Mutual indemnity capped at 1x 12-month fees for direct losses resulting from material breach or IP infringement.",
                forbidden_terms=["unlimited indemnity", "indemnify and hold harmless from any and all", "consequential damages under indemnity", "without cap"],
                risk_weight=25,
                recommended_redline=(
                    "Each party shall defend and indemnify the other party against direct third-party claims "
                    "arising from gross negligence or IP infringement, capped at the total fees paid in the preceding 12 months."
                ),
                guidance_notes="Never accept uncapped indemnity. Ensure indirect/consequential damages are excluded.",
                statutory_reference="Indian Contract Act, 1872 §73, §124",
            ),
            PlaybookRule(
                rule_id="RULE-MSA-LIAB",
                clause_type="limitation_of_liability",
                rule_name="Mutual Liability Cap & Consequential Damages Waiver",
                mandatory=True,
                standard_position="Mutual aggregate liability capped at 12-month trailing fees with express waiver of indirect/consequential damages.",
                forbidden_terms=["no limitation", "unlimited liability", "sole discretion", "uncapped"],
                risk_weight=20,
                recommended_redline=(
                    "In no event shall either party be liable for indirect, incidental, or consequential damages. "
                    "Each party's total aggregate liability shall be capped at total fees paid in the preceding 12 months."
                ),
                guidance_notes="Market standard is 1x trailing 12-month fees. Tier 1 fallback is 2x contract value.",
                statutory_reference="Indian Contract Act, 1872 §73",
            ),
            PlaybookRule(
                rule_id="RULE-MSA-GOVLAW",
                clause_type="governing_law",
                rule_name="Governing Law India & Institutional Arbitration",
                mandatory=True,
                standard_position="Governed by Indian substantive law with arbitration under the Arbitration & Conciliation Act 1996 in Mumbai/Bengaluru.",
                forbidden_terms=["laws of new york", "laws of england and wales", "laws of singapore", "unilateral appointment of arbitrator"],
                risk_weight=15,
                recommended_redline=(
                    "This Agreement is governed by the laws of India. Disputes shall be resolved by arbitration "
                    "under the Arbitration and Conciliation Act, 1996 seated in Mumbai/Bengaluru."
                ),
                guidance_notes="Unilateral arbitrator appointment violates Supreme Court ruling in Perkins Eastman.",
                statutory_reference="Arbitration and Conciliation Act, 1996 §7, §11, §12(5); Perkins Eastman (2019)",
            ),
            PlaybookRule(
                rule_id="RULE-MSA-TERM",
                clause_type="termination",
                rule_name="Termination with Cure Period & 30-Day Notice",
                mandatory=True,
                standard_position="Material breach termination requires minimum 30 days written cure notice. Convenience termination requires 60 days notice.",
                forbidden_terms=["terminate immediately without cause", "forfeiture of fees", "no refund"],
                risk_weight=15,
                recommended_redline=(
                    "Either party may terminate for material breach with 30 days cure notice, or for convenience with 60 days prior written notice."
                ),
                guidance_notes="Require pro-rata payment for work completed prior to termination.",
                statutory_reference="Indian Contract Act, 1872 §39, §64",
            ),
            PlaybookRule(
                rule_id="RULE-MSA-DPDP",
                clause_type="data_protection",
                rule_name="DPDP Act 2023 Compliance & 24h Breach Notice",
                mandatory=False,
                standard_position="Compliance with DPDP Act 2023 with mandatory 24-hour notification for confirmed personal data breaches.",
                forbidden_terms=["no liability for data breaches", "unrestricted processing of aadhaar"],
                risk_weight=10,
                recommended_redline=(
                    "Both parties shall comply with the Digital Personal Data Protection Act, 2023 and report data breaches within 24 hours."
                ),
                guidance_notes="Mandatory under DPDP Act 2023 for entities processing Indian personal data.",
                statutory_reference="Digital Personal Data Protection Act, 2023 §8",
            ),
            PlaybookRule(
                rule_id="RULE-MSA-TAX",
                clause_type="taxation",
                rule_name="GST Exclusive & TDS Certificate Timeline",
                mandatory=False,
                standard_position="Fees exclusive of GST; TDS certificates to be issued within 15 days of calendar quarter end.",
                forbidden_terms=["all taxes included with no tds certificate", "vendor responsible for client statutory taxes"],
                risk_weight=10,
                recommended_redline=(
                    "All fees are exclusive of GST. TDS will be deducted under Section 194 of the Income Tax Act with certificates issued within 15 days of quarter end."
                ),
                guidance_notes="Essential to protect Input Tax Credit under CGST Act 2017.",
                statutory_reference="CGST Act, 2017 §16; Income Tax Act, 1961 §194",
            ),
        ],
    ),
    ContractPlaybook(
        playbook_id="PB-EMPLOY-001",
        name="Employment & Executive Services (India §27 ICA Compliant) Playbook",
        description="Guidelines for Indian employment contracts ensuring strict compliance with Section 27 (Non-Compete prohibition) and BSA 2023.",
        contract_type="employment_agreement",
        rules=[
            PlaybookRule(
                rule_id="RULE-EMP-NONCOMP",
                clause_type="non_compete",
                rule_name="Section 27 ICA Strict Prohibition of Post-Term Non-Compete",
                mandatory=True,
                standard_position="Covenants restricted strictly to active term of employment. Post-employment non-compete clauses are void ab initio.",
                forbidden_terms=["shall not compete for 1 year post-termination", "shall not engage in any competing business post-termination", "restraint of trade post employment", "post-termination non-compete"],
                risk_weight=35,
                recommended_redline=(
                    "Employee shall not engage in any competing business during the active term of employment. "
                    "In accordance with Section 27 of the Indian Contract Act, 1872, no post-termination restraint on trade shall apply."
                ),
                guidance_notes="Under Supreme Court precedent (Percept D'Mark v. Zaheer Khan), post-employment non-competes are void in India.",
                statutory_reference="Indian Contract Act, 1872 Section 27 (§27); Percept D'Mark (2006) 4 SCC 227",
            ),
            PlaybookRule(
                rule_id="RULE-EMP-NONSOLICIT",
                clause_type="non_solicitation",
                rule_name="Reasonable Non-Solicitation (Max 12 Months)",
                mandatory=True,
                standard_position="Non-solicitation of clients and employees limited to 6-12 months post-employment.",
                forbidden_terms=["perpetual non-solicitation", "non-solicitation exceeding 24 months"],
                risk_weight=15,
                recommended_redline=(
                    "For a period of twelve (12) months following termination, Employee shall not solicit any existing clients or employees."
                ),
                guidance_notes="Non-solicitation clauses are generally upheld if reasonable in duration and scope.",
                statutory_reference="Indian Contract Act, 1872 §27",
            ),
            PlaybookRule(
                rule_id="RULE-EMP-IP",
                clause_type="intellectual_property",
                rule_name="Work for Hire & Moral Rights",
                mandatory=True,
                standard_position="All IP created during course of employment vests in employer under Copyright Act 1957 Section 17.",
                forbidden_terms=["employee retains patent ownership", "unrestricted moral rights waiver"],
                risk_weight=20,
                recommended_redline=(
                    "All inventions, code, and works created during employment are work-for-hire and vest exclusively in Employer."
                ),
                guidance_notes="Moral rights under Section 57 Copyright Act cannot be entirely waived, but assignment of economic rights is standard.",
                statutory_reference="Copyright Act, 1957 §17, §57",
            ),
        ],
    ),
    ContractPlaybook(
        playbook_id="PB-LEASE-001",
        name="Commercial Real Estate Lease Deed Playbook",
        description="Playbook for commercial leases, tenancy agreements, and licenses under Indian State Stamp Acts & Registration Act.",
        contract_type="lease_deed",
        rules=[
            PlaybookRule(
                rule_id="RULE-LEASE-STAMP",
                clause_type="stamp_duty",
                rule_name="Mandatory Stamp Duty & Sub-Registrar Registration",
                mandatory=True,
                standard_position="Instrument to be duly stamped under State Stamp Act and registered before Sub-Registrar if term > 11 months.",
                forbidden_terms=["agreement need not be stamped", "registration waived", "unregistered lease of 3 years"],
                risk_weight=30,
                recommended_redline=(
                    "This Lease Deed shall be properly stamped under the applicable State Stamp Act and registered before the Sub-Registrar within 4 months."
                ),
                guidance_notes="Unregistered lease exceeding 11 months cannot create tenancy rights and is inadmissible under Section 49 Registration Act.",
                statutory_reference="Registration Act, 1908 §17, §49; Indian Stamp Act, 1899 §35",
            ),
            PlaybookRule(
                rule_id="RULE-LEASE-TERM",
                clause_type="termination",
                rule_name="Notice Period & Security Deposit Refund",
                mandatory=True,
                standard_position="Tenant notice period 60-90 days; Security deposit refunded within 15 days of peaceful handover of possession.",
                forbidden_terms=["forfeiture of total security deposit without cause", "landlord may lock premises without notice"],
                risk_weight=20,
                recommended_redline=(
                    "Security deposit shall be refunded in full within 15 days of handover, subject only to deductions for unpaid rent or actual physical damages."
                ),
                guidance_notes="Forfeiture of security deposit without proven damages violates Section 74 Indian Contract Act.",
                statutory_reference="Indian Contract Act, 1872 §74",
            ),
        ],
    ),
]


class PlaybookDeviationEngine:
    """Evaluates contracts against firm playbooks to identify deviations and redline suggestions."""

    def __init__(self, clause_library: Optional[EnterpriseClauseLibrary] = None):
        self.clause_library = clause_library or EnterpriseClauseLibrary()
        self._playbooks: Dict[str, ContractPlaybook] = {
            pb.playbook_id: pb for pb in STANDARD_PLAYBOOKS
        }

    def list_playbooks(self) -> List[ContractPlaybook]:
        """List all available playbooks."""
        return list(self._playbooks.values())

    def get_playbook(self, playbook_id: str) -> Optional[ContractPlaybook]:
        """Get playbook by ID."""
        return self._playbooks.get(playbook_id)

    def add_playbook(self, playbook: ContractPlaybook) -> ContractPlaybook:
        """Register custom playbook."""
        self._playbooks[playbook.playbook_id] = playbook
        return playbook

    def evaluate_contract(
        self,
        contract_id: str,
        playbook_id: str,
        clauses: List[Any],
        full_text: str = "",
    ) -> PlaybookEvaluationResult:
        """Evaluate extracted clauses and full text against playbook rules."""
        playbook = self._playbooks.get(playbook_id)
        if not playbook:
            # Fallback to default MSA playbook if requested ID not found
            playbook = STANDARD_PLAYBOOKS[0]

        deviations: List[PlaybookDeviation] = []
        redlines: List[Dict[str, Any]] = []
        total_score_deduction = 0.0
        passed_rules_count = 0

        # Group extracted clauses by clause_type
        clauses_by_type: Dict[str, List[Any]] = {}
        for c in clauses:
            ctype = getattr(c, "clause_type", None)
            ctype_val = ctype.value if hasattr(ctype, "value") else str(ctype or "")
            if ctype_val:
                clauses_by_type.setdefault(ctype_val.lower(), []).append(c)

        # Evaluate each rule in the playbook
        for rule in playbook.rules:
            matched_clauses = clauses_by_type.get(rule.clause_type.lower(), [])
            rule_violated = False

            # 1. Check Mandatory Clause Presence
            if rule.mandatory and not matched_clauses:
                # Check if text mentions it generally
                text_has_mention = rule.clause_type.replace("_", " ") in full_text.lower()
                if not text_has_mention:
                    dev = PlaybookDeviation(
                        deviation_id=f"DEV-{uuid4().hex[:6].upper()}",
                        rule_id=rule.rule_id,
                        clause_type=rule.clause_type,
                        severity="high",
                        deviation_type="missing_mandatory_clause",
                        issue_description=f"Missing mandatory '{rule.rule_name}' clause. Playbook requires standard terms.",
                        recommended_redline=rule.recommended_redline,
                        statutory_reference=rule.statutory_reference,
                    )
                    deviations.append(dev)
                    total_score_deduction += rule.risk_weight
                    rule_violated = True
                    redlines.append({
                        "action": "insert",
                        "clause_type": rule.clause_type,
                        "title": rule.rule_name,
                        "suggested_text": rule.recommended_redline,
                        "rationale": f"Insert mandatory clause under {playbook.name}",
                    })
                    continue

            # 2. Inspect matched clauses for forbidden terms or statutory violations
            for c in matched_clauses:
                c_content = getattr(c, "content", "") or ""
                c_content_lower = c_content.lower()
                c_id = getattr(c, "clause_id", None)

                # Special Check: Section 27 Indian Contract Act (Non-Compete void ab initio)
                if rule.clause_type == "non_compete":
                    post_term_terms = [
                        "post-termination", "post termination", "after termination",
                        "following termination", "following termination of employment",
                        "upon termination", "upon cessation of services", "cessation of services",
                        "following departure", "after departure", "subsequent to disassociation",
                        "post disassociation", "post employment", "after employment", "post-employment",
                        "for 1 year following", "for a period following",
                    ]
                    if any(term in c_content_lower for term in post_term_terms):
                        dev = PlaybookDeviation(
                            deviation_id=f"DEV-{uuid4().hex[:6].upper()}",
                            rule_id=rule.rule_id,
                            clause_type=rule.clause_type,
                            clause_id=c_id,
                            severity="critical",
                            deviation_type="statutory_violation",
                            current_text=c_content[:200],
                            issue_description="CRITICAL STATUTORY VIOLATION: Post-termination non-compete is void ab initio under Section 27 of Indian Contract Act, 1872.",
                            recommended_redline=rule.recommended_redline,
                            statutory_reference="Indian Contract Act, 1872 Section 27 (§27); Percept D'Mark v. Zaheer Khan (2006)",
                        )
                        deviations.append(dev)
                        total_score_deduction += rule.risk_weight
                        rule_violated = True
                        redlines.append({
                            "action": "replace",
                            "clause_id": c_id,
                            "clause_type": rule.clause_type,
                            "original_text": c_content,
                            "replacement_text": rule.recommended_redline,
                            "rationale": "Replace void post-termination non-compete with enforceable in-term restriction (§27 ICA)",
                        })
                        continue

                # Check general forbidden terms
                found_forbidden = []
                for term in rule.forbidden_terms:
                    if term.lower() in c_content_lower:
                        found_forbidden.append(term)

                if found_forbidden:
                    severity = "critical" if any(k in " ".join(found_forbidden).lower() for k in ["unlimited", "void", "perpetual"]) else "high"
                    dev = PlaybookDeviation(
                        deviation_id=f"DEV-{uuid4().hex[:6].upper()}",
                        rule_id=rule.rule_id,
                        clause_type=rule.clause_type,
                        clause_id=c_id,
                        severity=severity,
                        deviation_type="forbidden_term_detected",
                        current_text=c_content[:200],
                        issue_description=f"Forbidden terms detected in '{rule.rule_name}': {', '.join(found_forbidden)}",
                        recommended_redline=rule.recommended_redline,
                        statutory_reference=rule.statutory_reference,
                    )
                    deviations.append(dev)
                    total_score_deduction += (rule.risk_weight * 0.8)
                    rule_violated = True
                    redlines.append({
                        "action": "replace",
                        "clause_id": c_id,
                        "clause_type": rule.clause_type,
                        "original_text": c_content,
                        "replacement_text": rule.recommended_redline,
                        "rationale": f"Remove non-compliant terms ({', '.join(found_forbidden)}) per {playbook.name}",
                    })

            if not rule_violated:
                passed_rules_count += 1

        # Calculate final compliance score
        final_score = max(0.0, min(100.0, 100.0 - total_score_deduction))

        # Determine overall status
        if any(d.severity == "critical" for d in deviations):
            overall_status = "walkaway_triggered"
        elif final_score < 60:
            overall_status = "high_risk_deviations"
        elif final_score < 90:
            overall_status = "minor_deviations"
        else:
            overall_status = "compliant"

        return PlaybookEvaluationResult(
            contract_id=contract_id,
            playbook_id=playbook.playbook_id,
            playbook_name=playbook.name,
            compliance_score=final_score,
            overall_status=overall_status,
            total_rules_evaluated=len(playbook.rules),
            passed_rules=passed_rules_count,
            deviations=deviations,
            redline_recommendations=redlines,
        )


# Alias for backward compatibility with test suites
PlaybookEvaluator = PlaybookDeviationEngine
