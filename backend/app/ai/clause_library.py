"""Enterprise Clause Library Module.

Curated repository of Standard, Fallback (Tier 1 / Tier 2), and Walkaway
clause language with Indian statutory guidance notes and negotiation rules.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class ClauseLibraryItem:
    """Enterprise clause repository entry with multi-tier fallback options."""
    clause_id: str
    clause_type: str
    title: str
    category: str
    standard_language: str
    fallback_tier_1: str
    fallback_tier_2: Optional[str] = None
    walkaway_language: Optional[str] = None
    guidance_notes: str = ""
    statutory_reference: Optional[str] = None
    jurisdiction: str = "India"
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clause_id": self.clause_id,
            "clause_type": self.clause_type,
            "title": self.title,
            "category": self.category,
            "standard_language": self.standard_language,
            "fallback_tier_1": self.fallback_tier_1,
            "fallback_tier_2": self.fallback_tier_2,
            "walkaway_language": self.walkaway_language,
            "guidance_notes": self.guidance_notes,
            "statutory_reference": self.statutory_reference,
            "jurisdiction": self.jurisdiction,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# Pre-populated Enterprise Legal Clause Repository
PRELOADED_CLAUSE_LIBRARY: List[ClauseLibraryItem] = [
    ClauseLibraryItem(
        clause_id="LIB-INDEM-001",
        clause_type="indemnity",
        title="Mutual Indemnification with Cap",
        category="Commercial",
        standard_language=(
            "Each party ('Indemnifying Party') agrees to defend, indemnify, and hold harmless "
            "the other party and its officers, directors, and employees from and against any third-party claims, "
            "losses, or damages arising out of (a) material breach of this Agreement, or (b) gross negligence "
            "or willful misconduct. The total aggregate liability under this indemnity shall not exceed "
            "the total fees paid or payable in the preceding twelve (12) months."
        ),
        fallback_tier_1=(
            "Indemnifying Party shall indemnify the other party against direct damages arising from "
            "material breach or intellectual property infringement, capped at two times (2x) the total "
            "contract value. Consequential, special, and punitive damages are expressly excluded."
        ),
        fallback_tier_2=(
            "Indemnifying Party shall indemnify against third-party claims resulting directly from proven "
            "IP infringement or breach of confidentiality, capped at the applicable insurance proceeds."
        ),
        walkaway_language=(
            "WALKAWAY TRIGGER: Reject any unilateral unlimited indemnity, indemnity for consequential damages, "
            "or indemnity extending to ordinary negligence without monetary cap."
        ),
        guidance_notes=(
            "Under Indian law (Sections 124 & 125, Indian Contract Act 1872), indemnity covers loss caused "
            "by the conduct of the promisor or third party. Always insist on a monetary cap and exclusion of "
            "indirect damages under Section 73 ICA."
        ),
        statutory_reference="Indian Contract Act, 1872 §124, §125, §73",
        tags=["indemnity", "liability", "commercial", "risk-control"],
    ),
    ClauseLibraryItem(
        clause_id="LIB-LIAB-001",
        clause_type="limitation_of_liability",
        title="Mutual Limitation of Liability & Consequential Damages Waiver",
        category="Commercial",
        standard_language=(
            "To the maximum extent permitted by applicable law, in no event shall either party be liable "
            "to the other for any indirect, incidental, special, punitive, or consequential damages, including "
            "loss of profits, revenue, data, or business opportunity. Each party's total aggregate liability "
            "under this Agreement shall be limited to the total amounts paid or payable by Client in the "
            "twelve (12) months preceding the event giving rise to liability."
        ),
        fallback_tier_1=(
            "Neither party shall be liable for indirect or consequential damages. Aggregate liability shall "
            "not exceed the total contract price or INR 50,00,000, whichever is greater, except for breach of "
            "confidentiality or gross negligence."
        ),
        fallback_tier_2=(
            "Liability is capped at 1.5x total fees paid. No liability for loss of profits, but direct data "
            "restoration costs shall be deemed direct damages up to a sub-limit of INR 25,00,000."
        ),
        walkaway_language=(
            "WALKAWAY TRIGGER: Reject uncapped liability provisions or one-sided liability limitations where "
            "only one party's liability is capped."
        ),
        guidance_notes=(
            "Under Section 73 of Indian Contract Act, damages are recoverable only for natural/direct consequences. "
            "Exclusion of indirect damages and a 12-month trailing cap represents market standard for Indian IT/SaaS."
        ),
        statutory_reference="Indian Contract Act, 1872 §73, §74",
        tags=["liability-cap", "consequential-damages", "risk-mitigation"],
    ),
    ClauseLibraryItem(
        clause_id="LIB-NONCOMP-001",
        clause_type="non_compete",
        title="Enforceable Restrictive Covenant & Section 27 Compliance",
        category="Employment & Services",
        standard_language=(
            "During the term of this Agreement, the Service Provider shall not directly engage in any business "
            "that directly competes with the specific scope of services provided to Client. The parties explicitly "
            "acknowledge that following termination of this Agreement, no post-termination restraint on trade "
            "shall apply, in strict accordance with Section 27 of the Indian Contract Act, 1872."
        ),
        fallback_tier_1=(
            "During the active term only, Service Provider shall not solicit Client's existing customers for identical "
            "services. For a period of six (6) months post-termination, Service Provider shall not actively solicit "
            "Client's key personnel with whom they had direct contact."
        ),
        fallback_tier_2=(
            "Non-solicitation of employees and clients for twelve (12) months post-termination, restricted to "
            "geographic area where services were actively delivered."
        ),
        walkaway_language=(
            "WALKAWAY TRIGGER: Any post-termination non-compete clause attempting to prohibit trade, profession, "
            "or business is void ab initio under Indian law (Percept D'Mark v. Zaheer Khan, Supreme Court of India). "
            "Do not accept covenants in restraint of trade."
        ),
        guidance_notes=(
            "Under Section 27 of the Indian Contract Act, 1872, every agreement by which anyone is restrained from "
            "exercising a lawful profession, trade or business is void to that extent. Post-termination non-competes "
            "are completely unenforceable in India. Only in-term restrictions and reasonable non-solicitation survive."
        ),
        statutory_reference="Indian Contract Act, 1872 §27; Percept D'Mark (India) Pvt. Ltd. v. Zaheer Khan (2006) 4 SCC 227",
        tags=["non-compete", "section-27", "restraint-of-trade", "indian-contract-act"],
    ),
    ClauseLibraryItem(
        clause_id="LIB-GOVLAW-001",
        clause_type="governing_law",
        title="Governing Law & Institutional Arbitration (India)",
        category="Dispute Resolution",
        standard_language=(
            "This Agreement shall be governed by and construed in accordance with the substantive laws of India. "
            "Any dispute, controversy, or claim arising out of or relating to this Agreement shall be referred to "
            "and finally resolved by arbitration administered by the Mumbai Centre for International Arbitration "
            "(MCIA) or Delhi International Arbitration Centre (DIAC) in accordance with the Arbitration and Conciliation "
            "Act, 1996. The seat and venue of arbitration shall be Mumbai / Bengaluru, India, and the proceedings "
            "shall be conducted in the English language by a sole arbitrator mutually appointed."
        ),
        fallback_tier_1=(
            "Governed by Indian laws. Disputes resolved by a sole arbitrator appointed in accordance with the "
            "Arbitration and Conciliation Act, 1996. Seat of arbitration: New Delhi / Bengaluru. Courts at New Delhi / "
            "Bengaluru shall have exclusive supervisory jurisdiction."
        ),
        fallback_tier_2=(
            "Three (3) arbitrator panel (one nominated by each party, presiding umpire appointed by nominees). "
            "Parties shall first attempt amicable settlement through executive negotiation for thirty (30) days."
        ),
        walkaway_language=(
            "WALKAWAY TRIGGER: Reject foreign seat for purely domestic Indian entities, rejection of Arbitration Act 1996, "
            "or unilateral appointment of sole arbitrator by counterparty alone (violates Perkins Eastman Architects)."
        ),
        guidance_notes=(
            "Ensure clear distinction between 'Seat' (curial law jurisdiction) and 'Venue'. Under Perkins Eastman (2019) "
            "and TRF Ltd (2017), unilateral appointment of arbitrator is invalid under Section 12(5) of the Act."
        ),
        statutory_reference="Arbitration and Conciliation Act, 1996 §7, §11, §12(5), §20; Perkins Eastman (2019)",
        tags=["arbitration", "governing-law", "dispute-resolution", "mcia", "diac"],
    ),
    ClauseLibraryItem(
        clause_id="LIB-TERM-001",
        clause_type="termination",
        title="Termination for Cause & Convenience with Notice",
        category="Commercial",
        standard_language=(
            "Either party may terminate this Agreement immediately upon written notice if the other party: "
            "(a) commits a material breach and fails to cure such breach within thirty (30) days of written notice; "
            "or (b) becomes subject to insolvency, bankruptcy, or liquidation proceedings. Either party may terminate "
            "this Agreement for convenience upon sixty (60) days prior written notice, subject to payment for all "
            "services satisfactorily delivered prior to the effective date of termination."
        ),
        fallback_tier_1=(
            "Material breach cure period of forty-five (45) days. Termination for convenience upon ninety (90) days "
            "written notice with reimbursement of reasonable non-cancelable third-party commitments."
        ),
        fallback_tier_2=(
            "Termination for convenience available only after completion of initial minimum term of six (6) months, "
            "with sixty (60) days notice."
        ),
        walkaway_language=(
            "WALKAWAY TRIGGER: Reject provisions allowing counterparty termination without notice or forfeiture of "
            "accrued payments for completed deliverables."
        ),
        guidance_notes=(
            "Ensure explicit cure periods and clear entitlement to accrued compensation up to termination date. "
            "In commercial agreements, immediate termination without cause creates severe operational risk."
        ),
        statutory_reference="Indian Contract Act, 1872 §39, §64, §75",
        tags=["termination", "cure-period", "convenience", "breach"],
    ),
    ClauseLibraryItem(
        clause_id="LIB-STAMP-001",
        clause_type="stamp_duty",
        title="Stamp Duty & Registration Compliance (Indian Stamp Act)",
        category="Real Estate & Conveyancing",
        standard_language=(
            "All stamp duty, registration fees, transfer charges, and incidental statutory levies payable on this "
            "Agreement and any instruments executed pursuant hereto under the Indian Stamp Act, 1899 and the applicable "
            "State Stamp Act (e.g., Karnataka Stamp Act, 1957 / Maharashtra Stamp Act, 1958) shall be borne and paid "
            "by the Purchaser / Licensee / Tenant. Both parties undertake to present this instrument for registration "
            "before the Sub-Registrar within four (4) months of execution as required by Section 23 of the Registration Act, 1908."
        ),
        fallback_tier_1=(
            "Stamp duty and registration charges shall be shared equally (50:50) between the parties. Each party shall "
            "bear its own legal counsel fees."
        ),
        fallback_tier_2=(
            "Purchaser/Tenant pays stamp duty; Vendor/Landlord assists with physical attendance at Sub-Registrar office "
            "and provides all requisite NOCs and mutation extracts within 15 days."
        ),
        walkaway_language=(
            "WALKAWAY TRIGGER: Reject any clause attempting to avoid stamp duty or execution without proper stamping, "
            "as insufficiently stamped documents are inadmissible in evidence under Section 35 of the Indian Stamp Act."
        ),
        guidance_notes=(
            "Under Section 35 of the Indian Stamp Act, 1899 and landmark judgment in N.N. Global Mercantile (2023), "
            "unstamped or insufficiently stamped agreements cannot be acted upon or received in evidence. For leases "
            "exceeding 11 months, registration is mandatory under Section 17 of the Registration Act, 1908."
        ),
        statutory_reference="Indian Stamp Act, 1899 §33, §35; Registration Act, 1908 §17, §23, §49; N.N. Global (2023)",
        tags=["stamp-duty", "registration-act", "sub-registrar", "real-estate", "admissibility"],
    ),
    ClauseLibraryItem(
        clause_id="LIB-DPDP-001",
        clause_type="data_protection",
        title="Digital Personal Data Protection (DPDP Act 2023) Compliance",
        category="Privacy & Compliance",
        standard_language=(
            "Each party shall comply with its respective obligations under the Digital Personal Data Protection Act, 2023 "
            "(DPDP Act) in respect of any personal data processed under this Agreement. Service Provider shall act solely "
            "as a Data Processor on behalf of the Data Fiduciary, process data only on documented instructions, implement "
            "reasonable security safeguards to prevent data breaches, notify the Data Fiduciary of any confirmed personal data "
            "breach within twenty-four (24) hours, and delete or return all personal data upon termination of the Agreement."
        ),
        fallback_tier_1=(
            "DPDP Act compliance with data breach notification within forty-eight (48) hours. Cross-border transfers permitted "
            "only to territories not restricted by the Central Government under Section 16 of the DPDP Act."
        ),
        fallback_tier_2=(
            "Standard data processing terms with annual SOC2 / ISO 27001 audit summary report provided in lieu of direct on-site inspection."
        ),
        walkaway_language=(
            "WALKAWAY TRIGGER: Refusal to sign data processing obligations, unlimited indemnity for counterparty's own privacy breaches, "
            "or unrestricted processing of biometric/aadhaar data without statutory consent."
        ),
        guidance_notes=(
            "The DPDP Act 2023 imposes statutory penalties up to INR 250 Crores for failure to take reasonable security safeguards "
            "to prevent data breaches. Ensure clear allocation between Data Fiduciary and Data Processor."
        ),
        statutory_reference="Digital Personal Data Protection Act, 2023 §6, §8, §9, §16",
        tags=["dpdp-act", "data-privacy", "personal-data", "compliance", "india-first"],
    ),
    ClauseLibraryItem(
        clause_id="LIB-TAX-001",
        clause_type="taxation",
        title="GST & TDS Tax Compliance & Gross-Up",
        category="Commercial & Finance",
        standard_language=(
            "All fees and consideration specified in this Agreement are exclusive of Goods and Services Tax (GST), "
            "which shall be charged in addition at the prevailing statutory rates against valid GST invoices. Client shall "
            "deduct Tax Deducted at Source (TDS) as applicable under Section 194C / 194J of the Income Tax Act, 1961 and shall "
            "deposit the same with the Government treasury and issue Form 16A TDS certificates to Service Provider within "
            "fifteen (15) days from the end of the relevant calendar quarter."
        ),
        fallback_tier_1=(
            "Fees exclusive of GST. TDS deducted with certificates issued within thirty (30) days of quarter end. If GST input tax "
            "credit (ITC) is denied to Client due to Vendor's non-filing of GSTR-1, Vendor shall indemnify Client for denied ITC."
        ),
        fallback_tier_2=(
            "Mutual tax gross-up provision if new withholding taxes are introduced during the contract duration."
        ),
        walkaway_language=(
            "WALKAWAY TRIGGER: Reject clauses demanding inclusive of all taxes where vendor is made liable for client's statutory levies, "
            "or failure to issue TDS credit certificates."
        ),
        guidance_notes=(
            "Mandate explicit GST identification numbers (GSTIN) and timeline for GSTR-1 uploading to protect Input Tax Credit (ITC) "
            "under Section 16 of CGST Act, 2017."
        ),
        statutory_reference="Income Tax Act, 1961 §194C, §194J; Central Goods and Services Tax Act, 2017 §16, §31",
        tags=["gst", "tds", "taxation", "income-tax-act", "invoice"],
    ),
]


class EnterpriseClauseLibrary:
    """Enterprise Clause Library management and lookup service."""

    def __init__(self):
        self._items: Dict[str, ClauseLibraryItem] = {
            item.clause_id: item for item in PRELOADED_CLAUSE_LIBRARY
        }

    def list_clauses(
        self,
        category: Optional[str] = None,
        clause_type: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[ClauseLibraryItem]:
        """List and filter clause library items."""
        results = list(self._items.values())

        if category:
            results = [c for c in results if c.category.lower() == category.lower()]
        if clause_type:
            results = [c for c in results if c.clause_type.lower() == clause_type.lower()]
        if query:
            q = query.lower()
            results = [
                c for c in results
                if q in c.title.lower()
                or q in c.standard_language.lower()
                or q in c.guidance_notes.lower()
                or any(q in t.lower() for t in c.tags)
            ]

        return results

    def get_clause(self, clause_id: str) -> Optional[ClauseLibraryItem]:
        """Get clause by ID."""
        return self._items.get(clause_id)

    def add_clause(self, item: ClauseLibraryItem) -> ClauseLibraryItem:
        """Add custom clause to library."""
        if not item.clause_id:
            item.clause_id = f"LIB-CUSTOM-{uuid4().hex[:6].upper()}"
        self._items[item.clause_id] = item
        return item

    def update_clause(self, clause_id: str, updates: Dict[str, Any]) -> Optional[ClauseLibraryItem]:
        """Update existing clause."""
        item = self._items.get(clause_id)
        if not item:
            return None

        for k, v in updates.items():
            if hasattr(item, k) and v is not None:
                setattr(item, k, v)
        item.updated_at = datetime.now(timezone.utc).isoformat()
        return item

    def delete_clause(self, clause_id: str) -> bool:
        """Delete clause from library."""
        if clause_id in self._items:
            del self._items[clause_id]
            return True
        return False
