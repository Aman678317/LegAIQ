"""Tests for Bharatiya Sakshya Adhiniyam 2023 Evidence Admissibility Engine."""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.ai.bharatiya_sakshya import (
    EvidenceType,
    AdmissibilityStatus,
    DocumentCategory,
    EvidenceItem,
    AdmissibilityReport,
    BharatiyaSakshyaEngine,
    analyze_case_evidence,
    check_section94_presumption,
    check_section95_presumption,
    check_section96_presumption,
    check_section97_presumption,
    generate_section63_certificate,
    _identify_critical_gaps,
    DPDPLawfulBasis,
    validate_dpdp_compliance,
)


class TestBharatiyaSakshyaEngine:
    """Test the BSA 2023 evidence admissibility engine."""
    
    def setup_method(self):
        self.engine = BharatiyaSakshyaEngine()
    
    def _make_evidence(self, **kwargs) -> EvidenceItem:
        """Helper to create evidence with defaults."""
        defaults = {
            "evidence_id": str(uuid4())[:8],
            "evidence_type": EvidenceType.DOCUMENTARY,
            "description": "Test document",
            "source": "Test source",
            "date_created": datetime.now(timezone.utc),
        }
        defaults.update(kwargs)
        return EvidenceItem(**defaults)
    
    # =========================================================================
    # Primary vs Secondary Evidence (Sections 57-60)
    # =========================================================================
    
    def test_original_document_is_admissible(self):
        """Original document should be admissible as primary evidence (Section 57)."""
        evidence = self._make_evidence(
            evidence_type=EvidenceType.DOCUMENTARY,
            is_original=True,
            document_category=DocumentCategory.PRIVATE_DOCUMENT,
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert result.admissibility_status == AdmissibilityStatus.ADMISSIBLE
        assert "57" in result.applicable_sections
        assert any("primary evidence" in c.lower() for c in result.conditions)
    
    def test_certified_copy_of_public_document_admissible(self):
        """Certified copy of public document admissible under Section 97."""
        evidence = self._make_evidence(
            evidence_type=EvidenceType.DOCUMENTARY,
            is_original=False,
            is_certified_copy=True,
            document_category=DocumentCategory.REVENUE_RECORD,
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert result.admissibility_status == AdmissibilityStatus.ADMISSIBLE
        assert "97" in result.applicable_sections
    
    def test_uncertified_secondary_evidence_conditional(self):
        """Uncertified secondary evidence requires foundation (Section 60)."""
        evidence = self._make_evidence(
            evidence_type=EvidenceType.DOCUMENTARY,
            is_original=False,
            is_certified_copy=False,
            document_category=DocumentCategory.PRIVATE_DOCUMENT,
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert result.admissibility_status == AdmissibilityStatus.CONDITIONALLY_ADMISSIBLE
        assert "60" in result.applicable_sections
        assert any("section 60" in c.lower() for c in result.conditions)
    
    # =========================================================================
    # Ancient Documents (Section 94)
    # =========================================================================
    
    def test_ancient_document_presumption(self):
        """Documents 30+ years old get Section 94 presumption."""
        old_date = datetime.now(timezone.utc) - timedelta(days=35*365)
        evidence = self._make_evidence(
            evidence_type=EvidenceType.DOCUMENTARY,
            is_original=True,
            date_created=old_date,
            document_category=DocumentCategory.PRIVATE_DOCUMENT,
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert result.document_category == DocumentCategory.ANCIENT_DOCUMENT
        assert "94" in result.applicable_sections
        assert any("ancient document" in c.lower() for c in result.conditions)
    
    def test_check_section94_presumption_direct(self):
        """Direct test of Section 94 check function."""
        old_date = datetime.now(timezone.utc) - timedelta(days=35*365)
        qualifies, msg = check_section94_presumption(old_date)
        
        assert qualifies is True
        assert "presumed genuine" in msg.lower()
        
        recent_date = datetime.now(timezone.utc) - timedelta(days=5*365)
        qualifies, msg = check_section94_presumption(recent_date)
        
        assert qualifies is False
        assert "30-year threshold" in msg.lower()
    
    # =========================================================================
    # Electronic Records (Sections 61-63)
    # =========================================================================
    
    def test_electronic_record_requires_section63(self):
        """Electronic record needs Section 63 certificate."""
        evidence = self._make_evidence(
            evidence_type=EvidenceType.ELECTRONIC,
            document_category=DocumentCategory.ELECTRONIC_RECORD,
            hash_value="abc123",
            metadata={"section63_certificate": False},
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert result.admissibility_status == AdmissibilityStatus.CONDITIONALLY_ADMISSIBLE
        assert "63" in " ".join(result.applicable_sections)
        assert any("section 63 certificate" in c.lower() for c in result.objections)
    
    def test_electronic_record_with_section63_admissible(self):
        """Electronic record with Section 63 certificate is admissible."""
        evidence = self._make_evidence(
            evidence_type=EvidenceType.ELECTRONIC,
            document_category=DocumentCategory.ELECTRONIC_RECORD,
            hash_value="abc123",
            metadata={
                "section63_certificate": True,
                "computer_generated": True,
                "regular_use": True,
                "regular_data_feed": True,
                "system_integrity_verified": True,
            },
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert result.admissibility_status == AdmissibilityStatus.ADMISSIBLE
        assert any("section 63 certificate provided" in c.lower() for c in result.conditions)
    
    def test_electronic_record_hash_verification(self):
        """Hash value enables integrity verification."""
        evidence = self._make_evidence(
            evidence_type=EvidenceType.ELECTRONIC,
            hash_value="sha256:abc123",
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert any("hash verified" in c.lower() for c in result.conditions)
    
    def test_electronic_record_no_hash_objection(self):
        """Missing hash creates objection."""
        evidence = self._make_evidence(
            evidence_type=EvidenceType.ELECTRONIC,
            hash_value=None,
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert any("no hash value" in o.lower() for o in result.objections)
    
    # =========================================================================
    # Section 95: Electronic Agreements
    # =========================================================================
    
    def test_check_section95_presumption(self):
        """Test Section 95 electronic agreement presumption."""
        complete_agreement = {
            "digital_signature": True,
            "timestamp": True,
            "certificate_authority": True,
            "integrity_check": True,
        }
        qualifies, msg = check_section95_presumption(complete_agreement)
        assert qualifies is True
        
        incomplete_agreement = {
            "digital_signature": True,
            "timestamp": False,
            "certificate_authority": True,
            "integrity_check": True,
        }
        qualifies, msg = check_section95_presumption(incomplete_agreement)
        assert qualifies is False
        assert "timestamp" in msg
    
    # =========================================================================
    # Section 96: Electronic Records & Signatures
    # =========================================================================
    
    def test_check_section96_presumption(self):
        """Test Section 96 electronic record/signature presumption."""
        record = {"hash_verified": True, "timestamp_verified": True, "certificate_valid": True}
        sig = {"signature_verified": True, "certificate_valid": True, "signer_identified": True}
        
        qualifies, msg = check_section96_presumption(record, sig)
        assert qualifies is True
        
        bad_record = {"hash_verified": False, "timestamp_verified": True, "certificate_valid": True}
        qualifies, msg = check_section96_presumption(bad_record, sig)
        assert qualifies is False
        assert "hash_verified" in msg
    
    # =========================================================================
    # Section 97: Certified Copies
    # =========================================================================
    
    def test_check_section97_presumption(self):
        """Test Section 97 certified copy presumption."""
        # Public document, certified
        qualifies, msg = check_section97_presumption(
            DocumentCategory.REVENUE_RECORD, True
        )
        assert qualifies is True
        
        # Public document, not certified
        qualifies, msg = check_section97_presumption(
            DocumentCategory.COURT_ORDER, False
        )
        assert qualifies is False
        
        # Private document, certified
        qualifies, msg = check_section97_presumption(
            DocumentCategory.PRIVATE_DOCUMENT, True
        )
        assert qualifies is False
    
    # =========================================================================
    # Hearsay Exceptions (Sections 22, 23, 27, 32, 33)
    # =========================================================================
    
    def test_oral_admission_section22(self):
        """Oral admissions relevant under Section 22."""
        evidence = self._make_evidence(
            evidence_type=EvidenceType.ORAL,
            metadata={"admission": True},
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert "22" in result.applicable_sections
    
    def test_civil_admission_section23(self):
        """Admissions in civil cases under Section 23."""
        evidence = self._make_evidence(
            evidence_type=EvidenceType.ADMISSION,
            metadata={},
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert "23" in result.applicable_sections
        assert any("section 23" in c.lower() for c in result.conditions)
    
    def test_without_prejudice_excluded(self):
        """Without prejudice communications may be excluded."""
        evidence = self._make_evidence(
            evidence_type=EvidenceType.ADMISSION,
            metadata={"without_prejudice": True},
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert any("without prejudice" in o.lower() for o in result.objections)
    
    def test_confession_to_police_inadmissible(self):
        """Confession to police officer inadmissible under Section 27."""
        evidence = self._make_evidence(
            evidence_type=EvidenceType.CONFESSION,
            metadata={"made_to_police": True},
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert any("police officer" in o.lower() for o in result.objections)
    
    def test_confession_in_custody_conditional(self):
        """Confession in custody admissible if leads to discovery."""
        evidence = self._make_evidence(
            evidence_type=EvidenceType.CONFESSION,
            metadata={"made_in_custody": True},
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert any("custody" in c.lower() for c in result.conditions)
    
    def test_dying_declaration_section32(self):
        """Dying declaration admissible under Section 32."""
        evidence = self._make_evidence(
            evidence_type=EvidenceType.HEARSAY_EXCEPTION,
            metadata={"witness_unavailable": True, "unavailability_reason": "death"},
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert "32" in result.applicable_sections
        assert any("death" in c.lower() for c in result.conditions)
    
    def test_prior_proceeding_section33(self):
        """Evidence from prior proceeding under Section 33."""
        evidence = self._make_evidence(
            evidence_type=EvidenceType.DOCUMENTARY,
            metadata={"prior_proceeding": True},
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert "33" in result.applicable_sections
        assert any("section 33" in c.lower() for c in result.conditions)
    
    # =========================================================================
    # Privilege
    # =========================================================================
    
    def test_legal_professional_privilege(self):
        """Legal professional privilege makes evidence privileged."""
        evidence = self._make_evidence(
            evidence_type=EvidenceType.DOCUMENTARY,
            metadata={"privilege": ["legal_professional"]},
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert result.admissibility_status == AdmissibilityStatus.PRIVILEGED
        assert any("legal professional privilege" in o.lower() for o in result.objections)
    
    def test_without_prejudice_privilege(self):
        """Without prejudice privilege."""
        evidence = self._make_evidence(
            evidence_type=EvidenceType.DOCUMENTARY,
            metadata={"privilege": ["without_prejudice"]},
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert any("without prejudice" in o.lower() for o in result.objections)
    
    # =========================================================================
    # DPDP Act 2023 Compliance
    # =========================================================================
    
    def test_dpdp_compliant_evidence(self):
        """Evidence with personal data and full DPDP compliance."""
        evidence = self._make_evidence(
            contains_personal_data=True,
            lawful_basis=DPDPLawfulBasis.LEGITIMATE_INTEREST.value,
            data_principal_consent=False,  # Not needed for legitimate interest
            retention_period_days=365,
            metadata={
                "purpose_specified": True,
                "minimized": True,
                "security_measures": True,
                "rights_informed": True,
            },
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert result.dpdp_compliant is True
        assert len(result.dpdp_issues) == 0
    
    def test_dpdp_missing_lawful_basis(self):
        """Missing lawful basis fails DPDP compliance."""
        evidence = self._make_evidence(
            contains_personal_data=True,
            lawful_basis=None,
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert result.dpdp_compliant is False
        assert any("lawful basis" in i.lower() for i in result.dpdp_issues)
    
    def test_dpdp_consent_basis_requires_consent(self):
        """Consent basis requires actual consent."""
        evidence = self._make_evidence(
            contains_personal_data=True,
            lawful_basis=DPDPLawfulBasis.CONSENT.value,
            data_principal_consent=False,
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert result.dpdp_compliant is False
        assert any("consent required" in i.lower() for i in result.dpdp_issues)
    
    def test_dpdp_no_retention_period(self):
        """Missing retention period is DPDP issue."""
        evidence = self._make_evidence(
            contains_personal_data=True,
            lawful_basis=DPDPLawfulBasis.LEGAL_OBLIGATION.value,
            retention_period_days=None,
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert any("retention period" in i.lower() for i in result.dpdp_issues)
    
    def test_validate_dpdp_compliance_function(self):
        """Test standalone DPDP validation function."""
        evidence = self._make_evidence(
            contains_personal_data=True,
            lawful_basis=DPDPLawfulBasis.CONSENT.value,
            data_principal_consent=True,
            retention_period_days=365,
            metadata={
                "purpose_specified": True,
                "minimized": True,
                "security_measures": True,
                "rights_informed": True,
            },
        )
        compliant, issues = validate_dpdp_compliance(evidence)
        
        assert compliant is True
        assert len(issues) == 0
    
    # =========================================================================
    # Full Case Analysis
    # =========================================================================
    
    def test_analyze_case_evidence_full_report(self):
        """Full case evidence analysis generates complete report."""
        evidence_list = [
            self._make_evidence(
                evidence_id="EVD-001",
                evidence_type=EvidenceType.DOCUMENTARY,
                description="Registered Sale Deed",
                document_category=DocumentCategory.REGISTERED_DOCUMENT,
                is_original=True,
                is_certified_copy=True,
            ),
            self._make_evidence(
                evidence_id="EVD-002",
                evidence_type=EvidenceType.ELECTRONIC,
                description="Email evidence",
                document_category=DocumentCategory.ELECTRONIC_RECORD,
                hash_value="hash123",
                metadata={"section63_certificate": True},
            ),
            self._make_evidence(
                evidence_id="EVD-003",
                evidence_type=EvidenceType.DOCUMENTARY,
                description="Uncertified copy",
                is_original=False,
                is_certified_copy=False,
            ),
        ]
        
        report = analyze_case_evidence("CASE-001", evidence_list)
        
        assert isinstance(report, AdmissibilityReport)
        assert report.report_id.startswith("ADM-CASE-001")
        assert report.total_items == 3
        assert report.admissible_count >= 1
        assert report.conditionally_admissible_count >= 1
        assert len(report.recommendations) > 0
    
    def test_critical_gaps_identification(self):
        """Critical gaps properly identified."""
        evidence_list = [
            self._make_evidence(
                evidence_type=EvidenceType.ELECTRONIC,
                metadata={"section63_certificate": False},
            ),
            self._make_evidence(
                evidence_type=EvidenceType.DOCUMENTARY,
                is_original=False,
                is_certified_copy=False,
            ),
        ]
        
        report = analyze_case_evidence("CASE-002", evidence_list)
        
        gaps = " ".join(report.critical_gaps)
        assert "section 63 certificate" in gaps.lower()
        assert "secondary evidence" in gaps.lower()
    
    def test_ancient_document_gap_detection(self):
        """Potential ancient documents flagged by gap detection (for unanalyzed evidence)."""
        old_date = datetime.now(timezone.utc) - timedelta(days=35*365)
        # Create unanalyzed evidence (not processed by engine)
        evidence_list = [
            EvidenceItem(
                evidence_id="EVD-OLD-001",
                evidence_type=EvidenceType.DOCUMENTARY,
                description="Old private document",
                source="Archives",
                date_created=old_date,
                document_category=DocumentCategory.PRIVATE_DOCUMENT,
                is_original=True,
            ),
        ]
        
        # Test gap detection directly on unanalyzed evidence
        gaps = _identify_critical_gaps(evidence_list)
        gaps_str = " ".join(gaps)
        assert "ancient document" in gaps_str.lower()
        
        # After engine analysis, gap should be resolved
        report = analyze_case_evidence("CASE-003", evidence_list)
        gaps_after = " ".join(report.critical_gaps)
        # Engine handles ancient documents, so no gap should remain
        assert "ancient document" not in gaps_after.lower()
    
    # =========================================================================
    # Section 63 Certificate Generation
    # =========================================================================
    
    def test_generate_section63_certificate(self):
        """Section 63 certificate generation."""
        evidence = self._make_evidence(
            evidence_id="EVD-CERT-001",
            evidence_type=EvidenceType.ELECTRONIC,
            description="Test electronic record",
            hash_value="abc123",
        )
        
        cert = generate_section63_certificate(
            evidence,
            custodian_name="John Doe",
            custodian_designation="System Administrator",
            organization="Test Corp",
        )
        
        assert cert["evidence_id"] == "EVD-CERT-001"
        assert cert["custodian"]["name"] == "John Doe"
        assert cert["legal_basis"] == "Section 63, Bharatiya Sakshya Adhiniyam, 2023"
        assert "certify that the electronic record" in cert["statement"].lower()
        assert "regular use" in cert["statement"].lower()
    
    # =========================================================================
    # Weight Assessment
    # =========================================================================
    
    def test_weight_assessment_ancient_document(self):
        """Ancient document gets high weight."""
        old_date = datetime.now(timezone.utc) - timedelta(days=35*365)
        evidence = self._make_evidence(
            date_created=old_date,
            document_category=DocumentCategory.PRIVATE_DOCUMENT,
            is_original=True,
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert result.weight_assessment is not None
        assert "high" in result.weight_assessment.lower()
    
    def test_weight_assessment_original_document(self):
        """Original document gets high weight."""
        evidence = self._make_evidence(
            is_original=True,
            document_category=DocumentCategory.PRIVATE_DOCUMENT,
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert "high" in result.weight_assessment.lower()
    
    def test_weight_assessment_certified_public(self):
        """Certified public document gets high weight."""
        evidence = self._make_evidence(
            is_original=False,
            is_certified_copy=True,
            document_category=DocumentCategory.REVENUE_RECORD,
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert "high" in result.weight_assessment.lower()
    
    def test_weight_assessment_conditional(self):
        """Conditional evidence gets conditional weight."""
        evidence = self._make_evidence(
            is_original=False,
            is_certified_copy=False,
            document_category=DocumentCategory.PRIVATE_DOCUMENT,
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert "conditional" in result.weight_assessment.lower()


class TestEdgeCases:
    """Edge case tests."""
    
    def setup_method(self):
        self.engine = BharatiyaSakshyaEngine()
    
    def test_evidence_without_date_created(self):
        """Evidence without date_created doesn't crash ancient doc check."""
        evidence = EvidenceItem(
            evidence_id="EVD-001",
            evidence_type=EvidenceType.DOCUMENTARY,
            description="Undated document",
            source="Unknown",
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert result.admissibility_status is not None
    
    def test_multiple_privilege_types(self):
        """Multiple privilege types handled."""
        evidence = EvidenceItem(
            evidence_id="EVD-001",
            evidence_type=EvidenceType.DOCUMENTARY,
            description="Privileged doc",
            source="Lawyer",
            metadata={"privilege": ["legal_professional", "work_product"]},
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert result.admissibility_status == AdmissibilityStatus.PRIVILEGED
    
    def test_dpdp_cross_border_transfer(self):
        """Cross-border transfer flagged."""
        evidence = EvidenceItem(
            evidence_id="EVD-001",
            evidence_type=EvidenceType.ELECTRONIC,
            description="Cloud stored doc",
            source="AWS US-East",
            contains_personal_data=True,
            lawful_basis=DPDPLawfulBasis.CONSENT.value,
            data_principal_consent=True,
            metadata={
                "cross_border_transfer": True,
                "adequacy_decision": False,
            },
        )
        result = self.engine.analyze_evidence(evidence)
        
        assert any("cross-border" in i.lower() for i in result.dpdp_issues)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])