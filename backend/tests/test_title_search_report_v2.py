"""Tests for Title Search Report v2 generator."""
import pytest
from datetime import datetime, timezone, timedelta
from app.ai.title_search_report import (
    TitleSearchReport,
    TitleSearchReportGenerator,
    ReportSection,
    PortalState,
)
from app.ai.land_intelligence import IndianPropertyProfile, NormalizedLandArea


class TestTitleSearchReportV2:
    """Test suite for Title Search Report v2 generation."""

    def _create_sample_report(self) -> TitleSearchReport:
        """Create a sample report for testing."""
        return TitleSearchReport(
            report_id="TSR-TEST-001",
            case_id="case-001",
            organization_id="org-001",
            title="Title Search Report - Survey 124/2, Varthur",
            property_address="Survey 124/2, Varthur, Whitefield, Bangalore Urban",
            survey_number="124/2",
            district="Bangalore Urban",
            taluk="Whitefield",
            village="Varthur",
            state=PortalState.KARNATAKA,
            client_name="ABC Developers Pvt Ltd",
            prepared_by="Adv. Rajesh Kumar",
            prepared_on=datetime.now(timezone.utc),
            search_period_years=30,
            search_date_from=datetime.now(timezone.utc) - timedelta(days=30*365),
            search_date_to=datetime.now(timezone.utc),
            property_profile=IndianPropertyProfile(
                survey_or_gat_number="124/2",
                district="Bangalore Urban",
                taluk_or_tehsil="Whitefield",
                village="Varthur",
                state="karnataka",
                recorded_owners=[
                    {"name": "Shri Ramachandra Rao", "father_husband": "S/o Late Narayana Rao", 
                     "share": "1/2", "category": "Bhumidhari", "acquisition_mode": "Purchase",
                     "acquisition_date": "15/03/2010"},
                    {"name": "Smt Lakshmi Devi", "father_husband": "W/o Ramachandra Rao", 
                     "share": "1/2", "category": "Bhumidhari", "acquisition_mode": "Inheritance",
                     "acquisition_date": "20/05/2015"},
                ],
                land_tenure_class="Bhumidhari (Ryotwari)",
                total_area=NormalizedLandArea(
                    raw_text="2.5 acres",
                    formatted_standard="2.5 acres",
                    acres=2.5,
                    guntas=0,
                    sq_feet=108900,
                    sq_meters=10117.14,
                ),
                khatoni_number="1234",
                mutation_entries=[
                    {"mutation_no": "MUT/2020/1234", "date": "15/03/2020", 
                     "type": "Sale", "from": "Original Owner", "to": "Ramachandra Rao",
                     "extent": "2.5 acres", "order_ref": "Order No. 45/2020", "status": "Sanctioned"},
                ],
                encumbrances_and_liens=[
                    {"type": "Mortgage", "party": "State Bank of India", "amount": "50 Lakhs",
                     "date": "20/05/2018", "doc_ref": "Doc No. 5678/2018", "status": "Active"},
                ],
                boundary_schedule={
                    "north": "Survey No. 124/1 (Road)",
                    "south": "Survey No. 124/3 (Agricultural Land)",
                    "east": "Survey No. 125 (Varthur Lake)",
                    "west": "Survey No. 123 (Residential Layout)",
                },
            ),
            portal_records=[],
            chain_of_title=[
                {
                    "document_type": "Sale Deed",
                    "document_number": "5678/2018",
                    "registration_date": "20/05/2018",
                    "sro": "Whitefield Sub-Registrar",
                    "transfer_type": "Sale",
                    "transferors": ["Original Owner"],
                    "transferees": ["Shri Ramachandra Rao", "Smt Lakshmi Devi"],
                    "consideration": "INR 75 Lakhs",
                    "stamp_duty": "INR 3.75 Lakhs",
                    "registration_fee": "INR 75,000",
                    "area_transferred": "2.5 acres",
                    "survey_numbers": ["124/2"],
                    "verification_status": "Verified from registered document",
                },
                {
                    "document_type": "Gift Deed",
                    "document_number": "1234/2015",
                    "registration_date": "20/05/2015",
                    "sro": "Whitefield Sub-Registrar",
                    "transfer_type": "Gift",
                    "transferors": ["Father of Lakshmi Devi"],
                    "transferees": ["Smt Lakshmi Devi"],
                    "consideration": "Natural Love and Affection",
                    "stamp_duty": "INR 1.5 Lakhs",
                    "registration_fee": "INR 30,000",
                    "area_transferred": "1.25 acres (half share)",
                    "survey_numbers": ["124/2"],
                    "verification_status": "Verified from registered document",
                },
            ],
            encumbrances=[
                {
                    "type": "Mortgage",
                    "party": "State Bank of India",
                    "amount": "INR 50 Lakhs",
                    "date": "20/05/2018",
                    "doc_ref": "Doc No. 5678/2018",
                    "status": "Active",
                    "registration": "Registered at Whitefield SRO",
                    "property_secured": "Survey 124/2, Varthur",
                    "terms": "Term loan for construction, 15 years",
                    "action": "Obtain NOC and registered Discharge Deed from SBI",
                },
            ],
            mutations=[
                {
                    "mutation_no": "MUT/2020/1234",
                    "date": "15/03/2020",
                    "type": "Sale",
                    "from": "Original Owner",
                    "to": "Ramachandra Rao",
                    "extent": "2.5 acres",
                    "order_ref": "Order No. 45/2020",
                    "status": "Sanctioned",
                    "remarks": "Khata transferred",
                },
            ],
            litigation_cases=[],
            tax_records=[
                {
                    "type": "Property Tax",
                    "year": "2023-24",
                    "amount_due": "15,000",
                    "amount_paid": "15,000",
                    "balance": "0",
                    "last_payment": "10/04/2023",
                    "arrears": "Nil",
                },
            ],
            registration_history=[],
            risks=[],
            discrepancies=[],
            recommendations=[
                "Obtain NOC and registered Discharge Deed from State Bank of India for mortgage release.",
                "Verify physical boundaries through licensed surveyor.",
                "Obtain updated Nil Encumbrance Certificate for full 30-year period.",
            ],
        )

    def test_report_creation(self):
        """Test that TitleSearchReport can be created with all fields."""
        report = self._create_sample_report()
        assert report.report_id == "TSR-TEST-001"
        assert report.survey_number == "124/2"
        assert report.state == PortalState.KARNATAKA
        assert report.property_profile is not None
        assert len(report.chain_of_title) == 2
        assert len(report.encumbrances) == 1
        assert len(report.mutations) == 1

    def test_pdf_generation(self):
        """Test PDF generation produces valid output."""
        report = self._create_sample_report()
        generator = TitleSearchReportGenerator(report)
        pdf_bytes = generator.generate_pdf()
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000  # Should be substantial
        assert pdf_bytes.startswith(b"%PDF-1.4")
        assert b"Title Search Report" in pdf_bytes
        assert b"124/2" in pdf_bytes
        assert b"KARNATAKA" in pdf_bytes.upper()

    def test_docx_generation(self):
        """Test DOCX generation produces valid output."""
        report = self._create_sample_report()
        generator = TitleSearchReportGenerator(report)
        docx_bytes = generator.generate_docx()
        
        assert isinstance(docx_bytes, bytes)
        assert len(docx_bytes) > 1000  # Should be substantial
        # DOCX is a ZIP file - check for ZIP signature
        assert docx_bytes.startswith(b"PK")  # ZIP magic bytes
        # Check for key content in the document by extracting word/document.xml
        import zipfile
        import io
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
            with z.open("word/document.xml") as f:
                docx_xml = f.read().decode("utf-8")
        assert "Title Search Report" in docx_xml
        assert "124/2" in docx_xml
        assert "Karnataka" in docx_xml

    def test_sections_built(self):
        """Test all required sections are built."""
        report = self._create_sample_report()
        generator = TitleSearchReportGenerator(report)
        sections = generator._build_sections()
        
        # Should have all 14 standard sections
        expected_sections = [
            "COVER PAGE",
            "EXECUTIVE SUMMARY",
            "1. PROPERTY IDENTIFICATION",
            "2. CHAIN OF TITLE (13-30 YEARS)",
            "3. CURRENT OWNERSHIP",
            "4. ENCUMBRANCES AND LIENS",
            "5. REVENUE RECORDS (RTC/7-12/PATTA)",
            "6. LITIGATION AND COURT CASES",
            "7. REGISTRATION HISTORY",
            "8. MUTATION HISTORY",
            "9. PROPERTY TAX AND GOVERNMENT DUES",
            "10. LEGAL OPINION AND RISK ASSESSMENT",
            "ANNEXURES",
            "DISCLAIMER",
            "SIGNATURE AND CERTIFICATION",
        ]
        
        section_headings = [s[0] for s in sections]
        for expected in expected_sections:
            assert expected in section_headings, f"Missing section: {expected}"

    def test_cover_page_content(self):
        """Test cover page has required information."""
        report = self._create_sample_report()
        generator = TitleSearchReportGenerator(report)
        sections = generator._build_sections()
        cover_page = [s[1] for s in sections if s[0] == "COVER PAGE"][0]
        
        assert "TSR-TEST-001" in cover_page
        assert "Survey 124/2" in cover_page
        assert "Varthur" in cover_page
        assert "Whitefield" in cover_page
        assert "Bangalore Urban" in cover_page
        assert "Karnataka" in cover_page
        assert "ABC Developers Pvt Ltd" in cover_page
        assert "Adv. Rajesh Kumar" in cover_page
        assert "CONFIDENTIAL" in cover_page

    def test_executive_summary(self):
        """Test executive summary is generated."""
        report = self._create_sample_report()
        generator = TitleSearchReportGenerator(report)
        sections = generator._build_sections()
        summary = [s[1] for s in sections if s[0] == "EXECUTIVE SUMMARY"][0]
        
        assert "Title Search Report" in summary
        assert "124/2" in summary
        assert "Varthur" in summary
        assert "chain of title" in summary.lower()

    def test_chain_of_title_section(self):
        """Test chain of title section has proper structure."""
        report = self._create_sample_report()
        generator = TitleSearchReportGenerator(report)
        sections = generator._build_sections()
        chain = [s[1] for s in sections if s[0] == "2. CHAIN OF TITLE (13-30 YEARS)"][0]
        
        assert "LINK 1" in chain
        assert "LINK 2" in chain
        assert "Sale Deed" in chain
        assert "Gift Deed" in chain
        assert "5678/2018" in chain
        assert "1234/2015" in chain
        assert "Whitefield Sub-Registrar" in chain

    def test_encumbrances_section(self):
        """Test encumbrances section formatting."""
        report = self._create_sample_report()
        generator = TitleSearchReportGenerator(report)
        sections = generator._build_sections()
        enc = [s[1] for s in sections if s[0] == "4. ENCUMBRANCES AND LIENS"][0]
        
        assert "State Bank of India" in enc
        assert "50 Lakhs" in enc
        assert "Mortgage" in enc
        assert "Active" in enc
        assert "NOC" in enc

    def test_current_ownership_section(self):
        """Test current ownership section."""
        report = self._create_sample_report()
        generator = TitleSearchReportGenerator(report)
        sections = generator._build_sections()
        ownership = [s[1] for s in sections if s[0] == "3. CURRENT OWNERSHIP"][0]
        
        assert "Ramachandra Rao" in ownership
        assert "Lakshmi Devi" in ownership
        assert "1/2" in ownership
        assert "Bhumidhari" in ownership
        assert "BOUNDARY SCHEDULE" in ownership
        assert "North:" in ownership

    def test_revenue_records_section(self):
        """Test revenue records section for Karnataka."""
        report = self._create_sample_report()
        generator = TitleSearchReportGenerator(report)
        sections = generator._build_sections()
        revenue = [s[1] for s in sections if s[0] == "5. REVENUE RECORDS (RTC/7-12/PATTA)"][0]
        
        assert "RTC (Record of Rights" in revenue or "Pahani" in revenue
        assert "1234" in revenue  # Khata number
        assert "Bhumidhari" in revenue

    def test_legal_opinion_section(self):
        """Test legal opinion section."""
        report = self._create_sample_report()
        generator = TitleSearchReportGenerator(report)
        sections = generator._build_sections()
        opinion = [s[1] for s in sections if s[0] == "10. LEGAL OPINION AND RISK ASSESSMENT"][0]
        
        assert "LEGAL OPINION ON TITLE" in opinion
        assert "BHARATIYA SAKSHYA ADHIYINIYAM" in opinion
        assert "DPDP ACT 2023" in opinion
        assert "CLEAR AND MARKETABLE" in opinion or "SUBJECT TO" in opinion

    def test_disclaimer_section(self):
        """Test disclaimer has required elements."""
        report = self._create_sample_report()
        generator = TitleSearchReportGenerator(report)
        sections = generator._build_sections()
        disclaimer = [s[1] for s in sections if s[0] == "DISCLAIMER"][0]
        
        assert "SCOPE OF SEARCH" in disclaimer
        assert "30-year" in disclaimer
        assert "LIMITATIONS" in disclaimer
        assert "DPDP ACT 2023" in disclaimer
        assert "NO LEGAL ADVICE" in disclaimer

    def test_signature_block(self):
        """Test signature block has digital signature readiness."""
        report = self._create_sample_report()
        generator = TitleSearchReportGenerator(report)
        sections = generator._build_sections()
        signature = [s[1] for s in sections if s[0] == "SIGNATURE AND CERTIFICATION"][0]
        
        assert "CERTIFICATION" in signature
        assert "Adv. Rajesh Kumar" in signature
        assert "DIGITAL SIGNATURE BLOCK" in signature
        assert "Digital Signature Hash" in signature
        assert "NOTARY" in signature

    def test_annexures_list(self):
        """Test annexures section has standard list."""
        report = self._create_sample_report()
        generator = TitleSearchReportGenerator(report)
        sections = generator._build_sections()
        annexures = [s[1] for s in sections if s[0] == "ANNEXURES"][0]
        
        assert "Annexure A" in annexures
        assert "Encumbrance Certificate" in annexures
        assert "RTC" in annexures or "7-12" in annexures
        assert "Mutation Register" in annexures
        assert "Property Tax Clearance" in annexures

    def test_empty_data_handling(self):
        """Test report handles empty data gracefully."""
        report = TitleSearchReport(
            report_id="TSR-EMPTY-001",
            case_id="case-002",
            organization_id="org-001",
            title="Title Search Report - Empty",
            property_address="Survey 100, Test Village",
            survey_number="100",
            district="Test District",
            taluk="Test Taluk",
            village="Test Village",
            state=PortalState.MAHARASHTRA,
            client_name="Test Client",
            prepared_by="Test Advocate",
            prepared_on=datetime.now(timezone.utc),
            search_period_years=13,
            search_date_from=datetime.now(timezone.utc) - timedelta(days=13*365),
            search_date_to=datetime.now(timezone.utc),
            property_profile=None,
            portal_records=[],
            chain_of_title=[],
            encumbrances=[],
            mutations=[],
            litigation_cases=[],
            tax_records=[],
            registration_history=[],
            risks=[],
            discrepancies=[],
            recommendations=[],
        )
        generator = TitleSearchReportGenerator(report)
        pdf_bytes = generator.generate_pdf()
        docx_bytes = generator.generate_docx()
        
        assert len(pdf_bytes) > 500
        assert len(docx_bytes) > 500
        assert b"NO ENCUMBRANCES FOUND" in pdf_bytes

    def test_all_portal_states(self):
        """Test report generation for all supported portal states."""
        for state in PortalState:
            report = TitleSearchReport(
                report_id=f"TSR-{state.value}-001",
                case_id=f"case-{state.value}",
                organization_id="org-001",
                title=f"Title Search Report - {state.value}",
                property_address=f"Survey 1, Village, Taluk, District, {state.value}",
                survey_number="1",
                district="Test District",
                taluk="Test Taluk",
                village="Test Village",
                state=state,
                client_name="Test Client",
                prepared_by="Test Advocate",
                prepared_on=datetime.now(timezone.utc),
                search_period_years=13,
                search_date_from=datetime.now(timezone.utc) - timedelta(days=13*365),
                search_date_to=datetime.now(timezone.utc),
            )
            generator = TitleSearchReportGenerator(report)
            pdf = generator.generate_pdf()
            docx = generator.generate_docx()
            
            assert len(pdf) > 500
            assert len(docx) > 500
            state_name = state.value.replace("_", " ").title().upper()
            assert state_name.encode() in pdf.upper()

    def test_risk_levels_in_opinion(self):
        """Test legal opinion reflects risk levels correctly."""
        report = self._create_sample_report()
        # Add high risk
        report.risks.append({
            "level": "CRITICAL",
            "category": "OWNERSHIP",
            "title": "Disputed ownership",
            "description": "Third party claims ownership",
            "recommended_action": "File declaratory suit",
        })
        
        generator = TitleSearchReportGenerator(report)
        sections = generator._build_sections()
        opinion = [s[1] for s in sections if s[0] == "10. LEGAL OPINION AND RISK ASSESSMENT"][0]
        
        assert "CRITICAL" in opinion
        assert "Disputed ownership" in opinion
        assert "SUBJECT TO RESOLUTION" in opinion

    def test_state_document_names(self):
        """Test state-specific document names in revenue section."""
        # Test Maharashtra (7/12)
        report_mh = self._create_sample_report()
        report_mh.state = PortalState.MAHARASHTRA
        gen_mh = TitleSearchReportGenerator(report_mh)
        sections_mh = gen_mh._build_sections()
        revenue_mh = [s[1] for s in sections_mh if "REVENUE RECORDS" in s[0]][0]
        assert "7/12" in revenue_mh or "Satbara" in revenue_mh
        
        # Test Karnataka (RTC/Pahani)
        report_ka = self._create_sample_report()
        report_ka.state = PortalState.KARNATAKA
        gen_ka = TitleSearchReportGenerator(report_ka)
        sections_ka = gen_ka._build_sections()
        revenue_ka = [s[1] for s in sections_ka if "REVENUE RECORDS" in s[0]][0]
        assert "RTC" in revenue_ka or "Pahani" in revenue_ka
        
        # Test Tamil Nadu (Patta/Chitta)
        report_tn = self._create_sample_report()
        report_tn.state = PortalState.TAMIL_NADU
        gen_tn = TitleSearchReportGenerator(report_tn)
        sections_tn = gen_tn._build_sections()
        revenue_tn = [s[1] for s in sections_tn if "REVENUE RECORDS" in s[0]][0]
        assert "Patta" in revenue_tn or "Chitta" in revenue_tn
        
        # Test Telangana (ROR-1B)
        report_tg = self._create_sample_report()
        report_tg.state = PortalState.TELANGANA
        gen_tg = TitleSearchReportGenerator(report_tg)
        sections_tg = gen_tg._build_sections()
        revenue_tg = [s[1] for s in sections_tg if "REVENUE RECORDS" in s[0]][0]
        assert "ROR-1B" in revenue_tg or "Pattadar" in revenue_tg
        
        # Test Gujarat (VF 7/12)
        report_gj = self._create_sample_report()
        report_gj.state = PortalState.GUJARAT
        gen_gj = TitleSearchReportGenerator(report_gj)
        sections_gj = gen_gj._build_sections()
        revenue_gj = [s[1] for s in sections_gj if "REVENUE RECORDS" in s[0]][0]
        assert "VF 7/12" in revenue_gj or "Village Form" in revenue_gj

    def test_report_without_property_profile(self):
        """Test report works when property_profile is None."""
        report = self._create_sample_report()
        report.property_profile = None
        generator = TitleSearchReportGenerator(report)
        pdf = generator.generate_pdf()
        docx = generator.generate_docx()
        
        assert len(pdf) > 500
        assert len(docx) > 500
        sections = generator._build_sections()
        revenue = [s[1] for s in sections if "REVENUE RECORDS" in s[0]][0]
        # Should mention RTC/7-12/Patta even without profile
        assert "REVENUE RECORD" in revenue


if __name__ == "__main__":
    pytest.main([__file__, "-v"])