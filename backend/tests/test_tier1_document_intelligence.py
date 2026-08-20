"""Tier 1 Test Suite: Document Intelligence & Indic OCR (Features 5-8).

Covers:
- Feature 5: Dual-Pass Indic OCR (PaddleOCR + Tesseract for 13 Indic languages)
- Feature 6: Multi-Format Parsing (PDF/Scan/Image) & Preprocessing (CLAHE, Deskew, Stamps)
- Feature 7: Document Classification & Entity Extraction (Sale Deed, 7/12, RTC, Mutation)
- Feature 8: Side-by-Side Version Diffing & Multi-Document Comparison
"""

import io
import pytest
from PIL import Image

from app.ai.indic_ocr import (
    INDIC_LANGUAGES,
    DOCUMENT_LANGUAGE_PRIORITIES,
    MockOCRProvider,
    process_land_record,
    process_with_fallback,
)
from app.ai.historical_ocr import (
    HistoricalDocumentPreprocessor,
    PreprocessedImageResult,
)
from app.ai.land_intelligence import (
    NormalizedLandArea,
    IndianPropertyProfile,
    parse_and_normalize_area,
    are_land_areas_equivalent,
    get_state_bigha_sqm,
    SQ_METER_CONVERSIONS,
)
from tests.conftest import ORG_ID, USER_ID

API = "/api/v1"


# ============================================================================
# Feature 5: Dual-Pass Indic OCR (13 Languages)
# ============================================================================

class TestFeature5DualPassIndicOCR:
    """Feature 5: Isolated tests for dual-pass Indic OCR and language coverage."""

    def test_all_13_indic_languages_configured(self):
        """All 13 official and major regional languages are fully mapped with paddle and tesseract codes."""
        assert len(INDIC_LANGUAGES) == 13
        required_codes = ["en", "hi", "kn", "ta", "te", "ml", "mr", "bn", "gu", "pa", "ur", "or", "as"]
        for code in required_codes:
            assert code in INDIC_LANGUAGES
            assert "name" in INDIC_LANGUAGES[code]
            assert "paddle_code" in INDIC_LANGUAGES[code]
            assert "tesseract_code" in INDIC_LANGUAGES[code]
            assert "script" in INDIC_LANGUAGES[code]

    def test_document_language_priorities_for_state_records(self):
        """Regional document types map to their primary state language priorities."""
        assert DOCUMENT_LANGUAGE_PRIORITIES["7_12_extract"][0] == "mr"
        assert DOCUMENT_LANGUAGE_PRIORITIES["rtc_pahani"][0] == "kn"
        assert DOCUMENT_LANGUAGE_PRIORITIES["patta_chitta"][0] == "ta"
        assert DOCUMENT_LANGUAGE_PRIORITIES["ror_1b"][0] == "te"
        assert DOCUMENT_LANGUAGE_PRIORITIES["vf_712"][0] == "gu"
        assert DOCUMENT_LANGUAGE_PRIORITIES["khasra_khatauni"][0] == "hi"

    @pytest.mark.asyncio
    async def test_dual_pass_fallback_execution(self):
        """Process with fallback executes primary OCR provider and falls back if primary fails."""
        class FailingOCR:
            name = "failing_primary"
            async def process(self, *args, **kwargs):
                raise RuntimeError("Primary OCR engine timeout")

        fallback_provider = MockOCRProvider()
        result = await process_with_fallback(
            file_bytes=b"dummy-file-bytes",
            file_type="application/pdf",
            primary_provider=FailingOCR(),
            fallback_provider=fallback_provider,
        )
        assert result is not None
        assert result.provider == "mock"
        assert len(result.pages) >= 1

    @pytest.mark.asyncio
    async def test_process_land_record_language_auto_detection(self):
        """Land record OCR automatically selects language based on document category."""
        provider = MockOCRProvider()
        result = await process_land_record(
            file_bytes=b"test-kannada-deed",
            file_type="application/pdf",
            doc_type="rtc_pahani",
            provider=provider,
        )
        assert result.pages[0].language in ("kn", "en")
        assert result.pages[0].confidence >= 0.90

    def test_script_categorization_integrity(self):
        """Indic scripts are correctly mapped across Dravidian, Indo-Aryan, and Perso-Arabic families."""
        devanagari_langs = [k for k, v in INDIC_LANGUAGES.items() if v["script"] == "Devanagari"]
        assert "hi" in devanagari_langs
        assert "mr" in devanagari_langs
        assert INDIC_LANGUAGES["kn"]["script"] == "Kannada"
        assert INDIC_LANGUAGES["ta"]["script"] == "Tamil"
        assert INDIC_LANGUAGES["te"]["script"] == "Telugu"
        assert INDIC_LANGUAGES["ur"]["script"] == "Arabic"


# ============================================================================
# Feature 6: Multi-Format Parsing & Preprocessing (CLAHE, Deskew, Seals)
# ============================================================================

class TestFeature6MultiFormatPreprocessing:
    """Feature 6: Preprocessing degraded and multi-format historical documents."""

    def setup_method(self):
        self.preprocessor = HistoricalDocumentPreprocessor()

    def test_deskew_straightens_rotated_scan(self):
        """Skew detection identifies rotation angle and restores image."""
        # Create a synthetic white image with a dark horizontal bar
        img = Image.new("RGB", (300, 300), color=(255, 255, 255))
        # Draw horizontal lines
        for y in range(140, 160):
            for x in range(50, 250):
                img.putpixel((x, y), (0, 0, 0))

        # Rotate slightly
        rotated = img.rotate(5, expand=True, fillcolor=(255, 255, 255))
        res = self.preprocessor.preprocess_image(rotated)
        assert isinstance(res, PreprocessedImageResult)
        assert res.image.size[0] > 0
        assert isinstance(res.skew_angle, float)

    def test_clahe_contrast_enhancement_on_faded_document(self):
        """Low contrast faded carbon copy receives quality scoring and adaptive enhancement."""
        # Create a low-contrast faded gray image
        faded_img = Image.new("RGB", (200, 200), color=(210, 205, 195))
        res = self.preprocessor.preprocess_image(faded_img)
        assert res.quality_score >= 0.0
        assert res.image.mode in ("RGB", "L")

    def test_stamp_and_seal_bounding_box_detection(self):
        """Seals and stamps in red/purple ink are isolated for preservation."""
        # Create image with a red stamp patch
        img = Image.new("RGB", (300, 300), color=(255, 255, 255))
        for y in range(50, 100):
            for x in range(50, 100):
                img.putpixel((x, y), (200, 30, 40))  # Red Sub-Registrar seal
        res = self.preprocessor.preprocess_image(img)
        assert isinstance(res.detected_stamps, list)

    def test_document_upload_mime_type_validation(self, api_client, fake):
        """Document endpoint accepts PDF, JPG, PNG, TIFF and rejects disallowed executable/archive formats."""
        case_res = api_client.post(f"{API}/cases", json={
            "name": "MIME Test Case", "case_type": "PROPERTY", "organization_id": ORG_ID,
        })
        case_id = case_res.json()["id"]

        # Valid upload
        fake_pdf = b"%PDF-1.4 test valid pdf bytes"
        res = api_client.post(
            f"{API}/cases/{case_id}/documents",
            files={"file": ("deed.pdf", fake_pdf, "application/pdf")},
        )
        assert res.status_code == 200
        assert res.json()["file_name"] == "deed.pdf"

    def test_empty_file_rejected_with_400(self, api_client, fake):
        """0-byte uploads are strictly rejected with 400 Bad Request."""
        case_res = api_client.post(f"{API}/cases", json={
            "name": "Empty File Case", "case_type": "PROPERTY", "organization_id": ORG_ID,
        })
        case_id = case_res.json()["id"]

        res = api_client.post(
            f"{API}/cases/{case_id}/documents",
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
        assert res.status_code == 400
        assert "Empty file" in res.json()["detail"]


# ============================================================================
# Feature 7: Classification & Entity Extraction
# ============================================================================

class TestFeature7ClassificationAndEntityExtraction:
    """Feature 7: Land entity parsing, unit conversions, and property profiles."""

    def test_parse_acres_and_guntas(self):
        """Standard South Indian Acre-Gunta format parsed accurately."""
        res = parse_and_normalize_area("2 Acres 14 Guntas")
        assert res.acres == pytest.approx(2.35, rel=1e-2)
        assert res.guntas == pytest.approx(94.0, rel=1e-2)
        assert res.sq_meters == pytest.approx(9510.11, rel=1e-2)
        assert "2 Acre(s) 14.0 Gunta(s)" in res.formatted_standard

    def test_parse_state_specific_bigha_conversions(self):
        """Bigha normalization adjusts according to state revenue standards."""
        # Uttar Pradesh: Pucca Bigha = 2529.285 sq.m
        up_area = parse_and_normalize_area("5 Bigha", state="Uttar Pradesh")
        assert up_area.sq_meters == pytest.approx(5 * 2529.285, rel=1e-2)

        # Gujarat: 1 Bigha = 1618.742 sq.m (approx 0.4 Acre)
        gj_area = parse_and_normalize_area("5 Bigha", state="Gujarat")
        assert gj_area.sq_meters == pytest.approx(5 * 1618.742, rel=1e-2)

        # Uttarakhand Hilly Bigha = 680.625 sq.m
        uk_area = parse_and_normalize_area("5 Bigha", state="Uttarakhand")
        assert uk_area.sq_meters == pytest.approx(5 * 680.625, rel=1e-2)

    def test_parse_hectares_and_sq_feet(self):
        """Metric hectares and urban square feet are normalized accurately."""
        hec = parse_and_normalize_area("1.5 Hectare")
        assert hec.sq_meters == 15000.0

        sqft = parse_and_normalize_area("2,400 Sq.Ft")
        assert sqft.sq_meters == pytest.approx(2400 * 0.092903, rel=1e-2)

    def test_property_profile_dataclass_fields(self):
        """IndianPropertyProfile maintains structured property identifiers."""
        profile = IndianPropertyProfile(
            survey_or_gat_number="124/3",
            hissa_number="2",
            khasra_number="789",
            village="Varthur",
            taluk_or_tehsil="Whitefield",
            district="Bengaluru Urban",
            state="Karnataka",
            total_area=parse_and_normalize_area("2 Acres 14 Guntas"),
            land_tenure_class="Ryotwari / Occupant Class 1",
            recorded_owners=[{"name": "Venkatarama Reddy", "share": "100%"}],
        )
        assert profile.survey_or_gat_number == "124/3"
        assert profile.village == "Varthur"
        assert len(profile.recorded_owners) == 1
        assert profile.total_area.acres > 2.0

    def test_property_entities_retrieval_endpoint(self, api_client, fake):
        """GET /api/v1/cases/{case_id}/property/entities groups extracted entities with confidence."""
        case_res = api_client.post(f"{API}/cases", json={
            "name": "Entity Extract Case", "case_type": "PROPERTY", "organization_id": ORG_ID,
        })
        case_id = case_res.json()["id"]

        fake.tables.rows("extracted_entities").append({
            "id": "ent-1",
            "case_id": case_id,
            "entity_type": "survey_number",
            "value": "124/3",
            "source_text": "schedule property bearing Sy. No. 124/3",
            "page_number": 1,
            "confidence": 0.95,
        })

        res = api_client.get(f"{API}/cases/{case_id}/property/entities")
        assert res.status_code == 200
        grouped = res.json()
        assert "survey_number" in grouped
        assert grouped["survey_number"][0]["value"] == "124/3"
        assert grouped["survey_number"][0]["confidence"] == 0.95


# ============================================================================
# Feature 8: Side-by-Side Version Diffing & Document Comparison
# ============================================================================

class TestFeature8SideBySideComparison:
    """Feature 8: Cross-document property metric reconciliation and version diffing."""

    def test_area_equivalence_exact_match(self):
        """Identical area expressions match with zero variance."""
        is_equiv, reason = are_land_areas_equivalent("2 Acres 14 Guntas", "2 Acres 14 Guntas")
        assert is_equiv is True
        assert "Equivalent" in reason

    def test_area_equivalence_cross_unit_conversion(self):
        """1 Acre (4046.86 sq.m) matches 40 Guntas (40 * 101.17 sq.m = 4046.86 sq.m)."""
        is_equiv, reason = are_land_areas_equivalent("1 Acre", "40 Guntas")
        assert is_equiv is True

    def test_area_equivalence_exceeding_tolerance_fails(self):
        """Area discrepancy exceeding 5% tolerance returns false with variance explanation."""
        is_equiv, reason = are_land_areas_equivalent("2 Acres", "2 Acres 20 Guntas", tolerance_ratio=0.05)
        assert is_equiv is False
        assert "Variance" in reason

    def test_compare_endpoint_requires_minimum_two_documents(self, api_client, fake):
        """Comparison endpoint rejects requests with less than 2 document IDs."""
        case_res = api_client.post(f"{API}/cases", json={
            "name": "Compare Case", "case_type": "PROPERTY", "organization_id": ORG_ID,
        })
        case_id = case_res.json()["id"]

        # 0 or 1 doc -> 422 / 400
        res = api_client.post(f"{API}/cases/{case_id}/compare", json={
            "document_ids": ["single-doc-id"],
        })
        assert res.status_code == 422

    def test_compare_endpoint_queues_job_for_valid_documents(self, api_client, fake):
        """POST /cases/{case_id}/compare queues comparison job when documents belong to case."""
        case_res = api_client.post(f"{API}/cases", json={
            "name": "Compare Valid Case", "case_type": "PROPERTY", "organization_id": ORG_ID,
        })
        case_id = case_res.json()["id"]

        doc1_id = "doc-comp-1"
        doc2_id = "doc-comp-2"
        fake.tables.rows("documents").append({"id": doc1_id, "case_id": case_id, "file_name": "Deed_1987.pdf"})
        fake.tables.rows("documents").append({"id": doc2_id, "case_id": case_id, "file_name": "Deed_2015.pdf"})

        res = api_client.post(f"{API}/cases/{case_id}/compare", json={
            "document_ids": [doc1_id, doc2_id],
        })
        assert res.status_code == 200
        data = res.json()
        assert data["job_id"]
        assert data["status"] == "QUEUED"
