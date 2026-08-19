"""Unit tests for Enhanced Indic OCR module."""

import pytest
from app.ai.indic_ocr import (
    INDIC_LANGUAGES,
    DOCUMENT_LANGUAGE_PRIORITIES,
    TesseractProvider,
    PaddleOCRProvider,
    GoogleVisionProvider,
    MockOCRProvider,
    LegalDocumentLayoutAnalyzer,
    get_ocr_provider,
    process_land_record,
    process_with_fallback,
    IndicOCRTrainer,
)


class TestIndicLanguages:
    """Test Indic language definitions."""

    def test_all_languages_defined(self):
        """Verify all 13 languages are defined."""
        assert len(INDIC_LANGUAGES) == 13

    def test_required_languages_present(self):
        """Verify critical Indian languages are present."""
        required = ["hi", "kn", "ta", "te", "ml", "mr", "bn", "gu", "pa", "ur", "or", "as", "en"]
        for lang in required:
            assert lang in INDIC_LANGUAGES

    def test_language_structure(self):
        """Verify each language has required fields."""
        for code, info in INDIC_LANGUAGES.items():
            assert "name" in info
            assert "paddle_code" in info
            assert "tesseract_code" in info
            assert "script" in info

    def test_scripts_are_valid(self):
        """Verify script names are recognized."""
        scripts = {info["script"] for info in INDIC_LANGUAGES.values()}
        expected_scripts = {"Latin", "Devanagari", "Kannada", "Tamil", "Telugu", "Malayalam", "Bengali", "Gujarati", "Gurmukhi", "Arabic", "Odia"}
        assert scripts == expected_scripts


class TestDocumentLanguagePriorities:
    """Test document type to language mapping."""

    def test_all_document_types_defined(self):
        """Verify key document types have language priorities."""
        required_types = [
            "7_12_extract", "rtc_pahani", "patta_chitta",
            "ror_1b", "vf_712", "khasra_khatauni",
            "sale_deed", "general"
        ]
        for doc_type in required_types:
            assert doc_type in DOCUMENT_LANGUAGE_PRIORITIES

    def test_priorities_reference_valid_languages(self):
        """Verify all referenced languages exist in INDIC_LANGUAGES."""
        for doc_type, langs in DOCUMENT_LANGUAGE_PRIORITIES.items():
            for lang in langs:
                assert lang in INDIC_LANGUAGES, f"{doc_type} references unknown language: {lang}"

    def test_maharashtra_priority(self):
        """Maharashtra 7/12 should prioritize Marathi/Hindi."""
        assert DOCUMENT_LANGUAGE_PRIORITIES["7_12_extract"] == ["mr", "hi", "en"]

    def test_karnataka_priority(self):
        """Karnataka RTC should prioritize Kannada."""
        assert DOCUMENT_LANGUAGE_PRIORITIES["rtc_pahani"] == ["kn", "en"]

    def test_tamil_nadu_priority(self):
        """Tamil Nadu Patta should prioritize Tamil."""
        assert DOCUMENT_LANGUAGE_PRIORITIES["patta_chitta"] == ["ta", "en"]


class TestLegalDocumentLayoutAnalyzer:
    """Test legal document layout analysis."""

    @pytest.fixture
    def analyzer(self):
        return LegalDocumentLayoutAnalyzer()

    @pytest.fixture
    def sample_deed(self):
        return """
        GOVERNMENT OF MAHARASHTRA
        OFFICE OF THE SUB-REGISTRAR, WHITEFIELD
        SALE DEED
        
        VENDOR: RAM SHARMA S/O LATE SHYAM SHARMA
        VENDEE: PRIYA PATEL D/O RAMESH PATEL
        
        PROPERTY SCHEDULE:
        Survey No: 124/2
        Area: 2 Acres 12 Guntas
        Boundaries:
        East by: Road
        West by: Land of Kumar
        North by: Nala
        South by: Land of Singh
        
        Executed on 04/06/2003
        Registered as Doc No. 445/2003-04
        """

    def test_analyze_sections(self, analyzer, sample_deed):
        """Test section detection."""
        sections = analyzer.analyze(sample_deed)
        
        assert "header" in sections
        assert "parties" in sections
        assert "property" in sections
        assert "execution" in sections
        assert "registration" in sections
        
        assert len(sections["header"]) >= 2
        assert len(sections["parties"]) >= 2
        assert len(sections["property"]) >= 4

    def test_extract_parties(self, analyzer, sample_deed):
        """Test party extraction."""
        parties = analyzer.extract_parties(sample_deed)
        
        # Should find at least the vendor and vendee
        assert len(parties) >= 2
        
        # Check for expected names
        names = [p["name"] for p in parties]
        assert "RAM SHARMA" in names
        assert "PRIYA PATEL" in names

    def test_extract_property_schedule(self, analyzer, sample_deed):
        """Test property schedule extraction."""
        schedule = analyzer.extract_property_schedule(sample_deed)
        
        assert "124/2" in schedule["survey_numbers"]
        assert "2 Acres 12 Guntas" in schedule["areas"]
        assert "Road" in str(schedule["boundaries"]["east"])
        assert "Kumar" in str(schedule["boundaries"]["west"])

    def test_boundary_extraction_all_directions(self, analyzer):
        """Test all four boundary directions."""
        text = "East by: Road\nWest by: River\nNorth by: Hill\nSouth by: Lake"
        schedule = analyzer.extract_property_schedule(text)
        
        assert schedule["boundaries"]["east"]
        assert schedule["boundaries"]["west"]
        assert schedule["boundaries"]["north"]
        assert schedule["boundaries"]["south"]


class TestOCRProviders:
    """Test OCR provider configurations."""

    def test_mock_provider_always_configured(self):
        """Mock provider should always be available."""
        provider = MockOCRProvider()
        assert provider.is_configured() is True
        assert provider.name == "mock"

    def test_provider_names(self):
        """Verify provider names are correct."""
        assert TesseractProvider().name == "tesseract"
        assert PaddleOCRProvider().name == "paddleocr"
        assert GoogleVisionProvider().name == "google_vision"
        assert MockOCRProvider().name == "mock"

    def test_get_ocr_provider_returns_mock_when_none_configured(self):
        """Factory should return mock when mock requested or unconfigured."""
        provider = get_ocr_provider("mock")
        assert isinstance(provider, MockOCRProvider)

        provider = get_ocr_provider("paddleocr")
        assert isinstance(provider, MockOCRProvider)

        provider = get_ocr_provider("google_vision")
        assert isinstance(provider, MockOCRProvider)

        provider = get_ocr_provider("unknown")
        assert isinstance(provider, MockOCRProvider)


class TestProcessLandRecord:
    """Test land record processing function."""

    @pytest.mark.asyncio
    async def test_process_land_record_maharashtra(self):
        """Test processing Maharashtra 7/12 record."""
        # Mock file bytes (empty for test)
        result = await process_land_record(
            b"fake pdf content",
            "application/pdf",
            "maharashtra",
            "7_12_extract",
            provider_name="mock",
        )

        assert result.provider == "mock"
        assert result.document_type == "7_12_extract"

    @pytest.mark.asyncio
    async def test_process_land_record_karnataka(self):
        """Test processing Karnataka RTC."""
        result = await process_land_record(
            b"fake pdf content",
            "application/pdf",
            "karnataka",
            "rtc_pahani",
            provider_name="mock",
        )

        assert result.document_type == "rtc_pahani"

    @pytest.mark.asyncio
    async def test_process_land_record_unknown_state(self):
        """Test unknown state falls back to general."""
        result = await process_land_record(
            b"fake pdf content",
            "application/pdf",
            "unknown_state",
            "general",
            provider_name="mock",
        )

        assert result.document_type == "general"


class TestIndicOCRTrainer:
    """Test OCR trainer utilities."""

    def test_get_model_config_hindi(self):
        """Test Hindi model config."""
        config = IndicOCRTrainer.get_model_config("hi")
        assert "algorithm" in config
        assert "character_dict" in config
        assert config["algorithm"] == "SVTR_LCNet"

    def test_get_model_config_unknown_defaults_to_english(self):
        """Unknown language should default to English config."""
        config = IndicOCRTrainer.get_model_config("xx")
        assert config == IndicOCRTrainer.get_model_config("en")


class TestProcessWithFallback:
    """Test fallback chain processing."""

    @pytest.mark.asyncio
    async def test_fallback_returns_mock_when_all_fail(self):
        """When all providers unavailable, should return mock result."""
        result = await process_with_fallback(
            b"fake content",
            "application/pdf",
            "general",
            ["paddleocr", "tesseract", "google_vision"]
        )
        
        assert result.provider == "mock"
        assert "Not configured" in result.full_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])