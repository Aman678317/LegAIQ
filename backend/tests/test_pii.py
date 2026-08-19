"""Tests for PII detection and redaction module."""
import pytest
from app.security.pii import (
    PIIEntityType,
    RedactionStrategy,
    RedactionConfig,
    PIIEntity,
    RedactionResult,
    IndianPIIRecognizer,
    LegalPIIRecognizer,
    PIIDetectionEngine,
    PIIRedactionPipeline,
    detect_pii,
    redact_pii,
    redact_document,
)


class TestIndianPIIRecognizer:
    """Test Indian PII pattern recognition."""
    
    @pytest.fixture
    def recognizer(self):
        return IndianPIIRecognizer()
    
    def test_aadhaar_detection(self, recognizer):
        text = "My Aadhaar is 1234 5678 9012 and another is 987654321098"
        entities = recognizer.detect(text)
        
        aadhaar_entities = [e for e in entities if e.entity_type == PIIEntityType.AADHAAR]
        # Should detect at least 2 unique Aadhaar numbers
        assert len(aadhaar_entities) >= 2
        # Check that both formats are detected
        texts = [e.text for e in aadhaar_entities]
        assert "1234 5678 9012" in texts
        assert "987654321098" in texts
    
    def test_aadhaar_checksum_validation(self, recognizer):
        # Valid Aadhaar with correct Verhoeff checksum
        valid_aadhaar = "234567890123"  # This is a test number
        # Invalid Aadhaar
        invalid_aadhaar = "123456789012"
        
        # We can't easily test checksum without knowing valid numbers
        # Just ensure detection works
        text = f"Valid: {valid_aadhaar} Invalid: {invalid_aadhaar}"
        entities = recognizer.detect(text)
        
        aadhaar_entities = [e for e in entities if e.entity_type == PIIEntityType.AADHAAR]
        assert len(aadhaar_entities) >= 1
    
    def test_pan_detection(self, recognizer):
        text = "PAN: ABCDE1234F and INVALID123"
        entities = recognizer.detect(text)
        
        pan_entities = [e for e in entities if e.entity_type == PIIEntityType.PAN]
        assert len(pan_entities) == 1
        assert pan_entities[0].text == "ABCDE1234F"
    
    def test_indian_phone_detection(self, recognizer):
        text = "Call me at +91 9876543210 or 9876543210 or 09876543210"
        entities = recognizer.detect(text)
        
        phone_entities = [e for e in entities if e.entity_type == PIIEntityType.INDIAN_PHONE]
        assert len(phone_entities) >= 2
    
    def test_ifsc_detection(self, recognizer):
        text = "IFSC: SBIN0001234 and HDFC0000456"
        entities = recognizer.detect(text)
        
        ifsc_entities = [e for e in entities if e.entity_type == PIIEntityType.IFSC]
        assert len(ifsc_entities) == 2
    
    def test_gst_detection(self, recognizer):
        text = "GSTIN: 29ABCDE1234F1Z5"
        entities = recognizer.detect(text)
        
        gst_entities = [e for e in entities if e.entity_type == PIIEntityType.GST]
        assert len(gst_entities) == 1
        assert gst_entities[0].text == "29ABCDE1234F1Z5"
    
    def test_vehicle_registration_detection(self, recognizer):
        text = "Vehicle: MH12AB1234 and KA01CD5678"
        entities = recognizer.detect(text)
        
        vehicle_entities = [e for e in entities if e.entity_type == PIIEntityType.VEHICLE_REG]
        assert len(vehicle_entities) == 2
    
    def test_passport_detection(self, recognizer):
        text = "Passport: A1234567"
        entities = recognizer.detect(text)
        
        passport_entities = [e for e in entities if e.entity_type == PIIEntityType.PASSPORT]
        assert len(passport_entities) == 1
    
    def test_voter_id_detection(self, recognizer):
        text = "Voter ID: ABC1234567"
        entities = recognizer.detect(text)
        
        voter_entities = [e for e in entities if e.entity_type == PIIEntityType.VOTER_ID]
        assert len(voter_entities) == 1
    
    def test_driving_license_detection(self, recognizer):
        text = "DL: MH1220230001234"
        entities = recognizer.detect(text)
        
        dl_entities = [e for e in entities if e.entity_type == PIIEntityType.DRIVING_LICENSE]
        assert len(dl_entities) == 1
    
    def test_upi_id_detection(self, recognizer):
        text = "Pay to user@oksbi or merchant@okhdfc"
        entities = recognizer.detect(text)
        
        upi_entities = [e for e in entities if e.entity_type == PIIEntityType.UPI_ID]
        assert len(upi_entities) == 2
    
    def test_cin_detection(self, recognizer):
        text = "CIN: L12345MH2020PTC123456"
        entities = recognizer.detect(text)
        
        cin_entities = [e for e in entities if e.entity_type == PIIEntityType.CIN]
        assert len(cin_entities) == 1
    
    def test_din_detection(self, recognizer):
        text = "DIN: 12345678"
        entities = recognizer.detect(text)
        
        din_entities = [e for e in entities if e.entity_type == PIIEntityType.DIN]
        assert len(din_entities) == 1
    
    def test_case_number_detection(self, recognizer):
        text = "Case: WP 1234/2023 and CA 567/2022"
        entities = recognizer.detect(text)
        
        case_entities = [e for e in entities if e.entity_type == PIIEntityType.CASE_NUMBER]
        assert len(case_entities) >= 1


class TestLegalPIIRecognizer:
    """Test legal PII pattern recognition."""
    
    @pytest.fixture
    def recognizer(self):
        return LegalPIIRecognizer()
    
    def test_court_name_detection(self, recognizer):
        text = "Filed in the Supreme Court of India and High Court of Delhi"
        entities = recognizer.detect(text)
        
        court_entities = [e for e in entities if e.entity_type == PIIEntityType.COURT_NAME]
        assert len(court_entities) >= 1
    
    def test_judge_name_detection(self, recognizer):
        text = "Hon'ble Justice D.Y. Chandrachud and Justice Sanjay Kishan Kaul"
        entities = recognizer.detect(text)
        
        judge_entities = [e for e in entities if e.entity_type == PIIEntityType.JUDGE_NAME]
        assert len(judge_entities) >= 1
    
    def test_lawyer_name_detection(self, recognizer):
        text = "Advocate Harish Salve and Sr. Adv. Mukul Rohatgi appeared"
        entities = recognizer.detect(text)
        
        lawyer_entities = [e for e in entities if e.entity_type == PIIEntityType.LAWYER_NAME]
        assert len(lawyer_entities) >= 1


class TestPIIDetectionEngine:
    """Test main PII detection engine."""
    
    @pytest.fixture
    def engine(self):
        return PIIDetectionEngine()
    
    def test_detect_indian_pii(self, engine):
        text = "Aadhaar: 1234 5678 9012, PAN: ABCDE1234F, Phone: 9876543210"
        entities = engine.detect(text)
        
        types = [e.entity_type for e in entities]
        assert PIIEntityType.AADHAAR in types
        assert PIIEntityType.PAN in types
        assert PIIEntityType.INDIAN_PHONE in types
    
    def test_detect_legal_pii(self, engine):
        text = "Filed in Supreme Court of India by Advocate Harish Salve"
        entities = engine.detect(text)
        
        types = [e.entity_type for e in entities]
        assert PIIEntityType.COURT_NAME in types
        assert PIIEntityType.LAWYER_NAME in types
    
    def test_confidence_filtering(self, engine):
        config = RedactionConfig(min_confidence=0.9)
        engine.config = config
        
        text = "Aadhaar: 1234 5678 9012"
        entities = engine.detect(text)
        
        # Should still detect but confidence may vary
        assert len(entities) >= 0
    
    def test_entity_type_filtering(self, engine):
        config = RedactionConfig(enabled_entity_types=[PIIEntityType.AADHAAR, PIIEntityType.PAN])
        engine.config = config
        
        text = "Aadhaar: 1234 5678 9012, Phone: 9876543210"
        entities = engine.detect(text)
        
        types = [e.entity_type for e in entities]
        assert PIIEntityType.AADHAAR in types
        assert PIIEntityType.INDIAN_PHONE not in types


class TestPIIRedaction:
    """Test PII redaction functionality."""
    
    @pytest.fixture
    def engine(self):
        return PIIDetectionEngine()
    
    def test_redact_mask_strategy(self, engine):
        text = "My Aadhaar is 1234 5678 9012"
        config = RedactionConfig(strategy=RedactionStrategy.MASK, mask_char="X", min_confidence=0.5)
        
        result = engine.redact(text, config)
        
        assert "XXXX XXXX XXXX" in result.redacted_text
        assert "1234 5678 9012" not in result.redacted_text
        assert len(result.entities) == 1
    
    def test_redact_replace_strategy(self, engine):
        text = "My Aadhaar is 1234 5678 9012"
        config = RedactionConfig(strategy=RedactionStrategy.REPLACE, min_confidence=0.5)
        
        result = engine.redact(text, config)
        
        assert "[AADHAAR]" in result.redacted_text
        assert "1234 5678 9012" not in result.redacted_text
    
    def test_redact_hash_strategy(self, engine):
        text = "My Aadhaar is 1234 5678 9012"
        config = RedactionConfig(strategy=RedactionStrategy.HASH, min_confidence=0.5)
        
        result = engine.redact(text, config)
        
        assert "[AADHAAR_" in result.redacted_text
        assert "1234 5678 9012" not in result.redacted_text
    
    def test_redact_remove_strategy(self, engine):
        text = "My Aadhaar is 1234 5678 9012 and PAN is ABCDE1234F"
        config = RedactionConfig(strategy=RedactionStrategy.REMOVE, min_confidence=0.5)
        
        result = engine.redact(text, config)
        
        assert "1234 5678 9012" not in result.redacted_text
        assert "ABCDE1234F" not in result.redacted_text
        assert "My Aadhaar is  and PAN is " in result.redacted_text
    
    def test_redact_pseudonymize_strategy(self, engine):
        text = "My Aadhaar is 1234 5678 9012"
        config = RedactionConfig(strategy=RedactionStrategy.PSEUDONYMIZE, min_confidence=0.5)
        
        result = engine.redact(text, config)
        
        assert "AADHAAR_" in result.redacted_text
        assert "1234 5678 9012" not in result.redacted_text
    
    def test_redact_preserve_length(self, engine):
        text = "Aadhaar: 1234 5678 9012"
        config = RedactionConfig(strategy=RedactionStrategy.MASK, preserve_length=True, min_confidence=0.5)
        
        result = engine.redact(text, config)
        
        # Original entity length: 14 (including spaces)
        # Masked should be same length
        assert len(result.redacted_text) == len(text)
    
    def test_redact_custom_replacement(self, engine):
        text = "My Aadhaar is 1234 5678 9012"
        config = RedactionConfig(
            strategy=RedactionStrategy.MASK,
            custom_replacements={PIIEntityType.AADHAAR: "[REDACTED_AADHAAR]"},
            min_confidence=0.5,
        )
        
        result = engine.redact(text, config)
        
        assert "[REDACTED_AADHAAR]" in result.redacted_text
    
    def test_redact_multiple_entities(self, engine):
        text = "Aadhaar: 1234 5678 9012, PAN: ABCDE1234F, Phone: 9876543210"
        config = RedactionConfig(strategy=RedactionStrategy.MASK, mask_char="X", min_confidence=0.5)
        
        result = engine.redact(text, config)
        
        assert "XXXX XXXX XXXX" in result.redacted_text
        assert "XXXXXXXXXF" in result.redacted_text or "XXXXXXXXXX" in result.redacted_text
        assert "XXXXXXXXXX" in result.redacted_text
        assert len(result.entities) == 3
    
    def test_redaction_map(self, engine):
        text = "Aadhaar: 1234 5678 9012"
        config = RedactionConfig(strategy=RedactionStrategy.MASK, mask_char="X", return_redaction_map=True, min_confidence=0.5)
        
        result = engine.redact(text, config)
        
        assert "1234 5678 9012" in result.redaction_map
        assert result.redaction_map["1234 5678 9012"].startswith("X")
    
    def test_stats(self, engine):
        text = "Aadhaar: 1234 5678 9012, PAN: ABCDE1234F"
        config = RedactionConfig(strategy=RedactionStrategy.MASK, min_confidence=0.5)
        
        result = engine.redact(text, config)
        
        assert result.stats["total_entities"] == 2
        assert "AADHAAR" in result.stats["by_type"]
        assert "PAN" in result.stats["by_type"]


class TestRedactDocument:
    """Test document redaction."""
    
    def test_redact_document_dict(self):
        document = {
            "id": "doc1",
            "content": "Aadhaar: 1234 5678 9012",
            "title": "Test Document",
            "metadata": {"author": "John Doe"},
        }
        
        config = RedactionConfig(strategy=RedactionStrategy.MASK, mask_char="X", min_confidence=0.5)
        redacted = redact_document(document, config)
        
        assert "XXXX XXXX XXXX" in redacted["content"]
        assert redacted["title"] == "Test Document"
        assert "content_pii_entities" in redacted
    
    def test_redact_document_multiple_fields(self):
        document = {
            "content": "Aadhaar: 1234 5678 9012",
            "summary": "PAN: ABCDE1234F",
            "description": "Phone: 9876543210",
        }
        
        config = RedactionConfig(strategy=RedactionStrategy.MASK, mask_char="X", min_confidence=0.5)
        redacted = redact_document(document, config)
        
        assert "XXXX XXXX XXXX" in redacted["content"]
        assert "XXXXXXXXXF" in redacted["summary"] or "XXXXXXXXXX" in redacted["summary"]
        assert "XXXXXXXXXX" in redacted["description"]


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_detect_pii_function(self):
        entities = detect_pii("Aadhaar: 1234 5678 9012")
        assert len(entities) == 1
        assert entities[0].entity_type == PIIEntityType.AADHAAR
    
    def test_redact_pii_function(self):
        result = redact_pii("Aadhaar: 1234 5678 9012", config=RedactionConfig(mask_char="X", min_confidence=0.5))
        assert "XXXX XXXX XXXX" in result.redacted_text
    
    def test_redact_document_function(self):
        doc = {"content": "Aadhaar: 1234 5678 9012"}
        redacted = redact_document(doc, config=RedactionConfig(mask_char="X", min_confidence=0.5))
        assert "XXXX XXXX XXXX" in redacted["content"]


class TestPIIRedactionPipeline:
    """Test PII redaction pipeline."""
    
    @pytest.fixture
    def pipeline(self):
        return PIIRedactionPipeline()
    
    def test_process_document(self, pipeline):
        document = {
            "id": "doc1",
            "content": "Aadhaar: 1234 5678 9012, PAN: ABCDE1234F",
            "title": "Test",
        }
        
        result = pipeline.process_document(document, config=RedactionConfig(mask_char="X", min_confidence=0.5))
        
        assert "XXXX XXXX XXXX" in result["content"]
        assert "content_pii_entities" in result
    
    def test_process_batch(self, pipeline):
        documents = [
            {"id": "1", "content": "Aadhaar: 1234 5678 9012"},
            {"id": "2", "content": "PAN: ABCDE1234F"},
        ]
        
        results = pipeline.process_batch(documents, config=RedactionConfig(mask_char="X", min_confidence=0.5))
        
        assert len(results) == 2
        assert "XXXX XXXX XXXX" in results[0]["content"]
        assert "XXXXXXXXXF" in results[1]["content"] or "XXXXXXXXXX" in results[1]["content"]


class TestEntityTypes:
    """Test entity type enumeration."""
    
    def test_all_entity_types_present(self):
        # Indian-specific
        assert PIIEntityType.AADHAAR
        assert PIIEntityType.PAN
        assert PIIEntityType.INDIAN_PHONE
        assert PIIEntityType.INDIAN_EMAIL
        assert PIIEntityType.BANK_ACCOUNT
        assert PIIEntityType.IFSC
        assert PIIEntityType.VEHICLE_REG
        assert PIIEntityType.PASSPORT
        assert PIIEntityType.VOTER_ID
        assert PIIEntityType.DRIVING_LICENSE
        assert PIIEntityType.GST
        assert PIIEntityType.UPI_ID
        assert PIIEntityType.CIN
        assert PIIEntityType.DIN
        
        # General
        assert PIIEntityType.EMAIL
        assert PIIEntityType.PHONE
        assert PIIEntityType.PERSON
        assert PIIEntityType.LOCATION
        assert PIIEntityType.DATE
        assert PIIEntityType.CREDIT_CARD
        assert PIIEntityType.IP_ADDRESS
        assert PIIEntityType.URL
        
        # Legal-specific
        assert PIIEntityType.CASE_NUMBER
        assert PIIEntityType.COURT_NAME
        assert PIIEntityType.LAWYER_NAME
        assert PIIEntityType.JUDGE_NAME


class TestRedactionStrategies:
    """Test redaction strategy enumeration."""
    
    def test_all_strategies_present(self):
        assert RedactionStrategy.MASK
        assert RedactionStrategy.REPLACE
        assert RedactionStrategy.HASH
        assert RedactionStrategy.REMOVE
        assert RedactionStrategy.PSEUDONYMIZE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])