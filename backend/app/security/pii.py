"""PII Detection and Redaction Module for Jurisiva AI.

This module provides automated PII detection and redaction for legal documents,
with special support for Indian legal contexts including:
- Aadhaar numbers (12-digit)
- PAN numbers (10-char alphanumeric)
- Indian phone numbers
- Indian email addresses
- Indian names (using NER)
- Bank account numbers
- IFSC codes
- Vehicle registration numbers
- Passport numbers
- Voter ID numbers
- Driving license numbers
- GST numbers

Also handles general PII: emails, phones, addresses, SSN-equivalents, credit cards.
"""

import re
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from functools import lru_cache

try:
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    AnalyzerEngine = None
    RecognizerRegistry = None
    NlpEngineProvider = None
    AnonymizerEngine = None
    OperatorConfig = None


class PIIEntityType(str, Enum):
    """Types of PII entities detected."""
    # Indian-specific
    AADHAAR = "AADHAAR"
    PAN = "PAN"
    INDIAN_PHONE = "INDIAN_PHONE"
    INDIAN_EMAIL = "INDIAN_EMAIL"
    INDIAN_NAME = "INDIAN_NAME"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    IFSC = "IFSC"
    VEHICLE_REG = "VEHICLE_REG"
    PASSPORT = "PASSPORT"
    VOTER_ID = "VOTER_ID"
    DRIVING_LICENSE = "DRIVING_LICENSE"
    GST = "GST"
    UPI_ID = "UPI_ID"
    CIN = "CIN"
    DIN = "DIN"
    
    # General PII
    EMAIL = "EMAIL_ADDRESS"
    PHONE = "PHONE_NUMBER"
    PERSON = "PERSON"
    LOCATION = "LOCATION"
    DATE = "DATE_TIME"
    CREDIT_CARD = "CREDIT_CARD"
    IP_ADDRESS = "IP_ADDRESS"
    URL = "URL"
    
    # Legal-specific
    CASE_NUMBER = "CASE_NUMBER"
    COURT_NAME = "COURT_NAME"
    LAWYER_NAME = "LAWYER_NAME"
    JUDGE_NAME = "JUDGE_NAME"
    
    # Custom
    CUSTOM = "CUSTOM"


class RedactionStrategy(str, Enum):
    """Redaction strategies."""
    MASK = "mask"              # Replace with *** or XXXX
    REPLACE = "replace"        # Replace with entity type label
    HASH = "hash"              # Replace with hash
    REMOVE = "remove"          # Remove entirely
    PSEUDONYMIZE = "pseudonymize"  # Replace with consistent pseudonym


@dataclass
class PIIEntity:
    """Detected PII entity."""
    entity_type: PIIEntityType
    text: str
    start: int
    end: int
    confidence: float
    context: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class RedactionResult:
    """Result of PII redaction."""
    original_text: str
    redacted_text: str
    entities: list[PIIEntity]
    redaction_map: dict[str, str] = field(default_factory=dict)  # original -> redacted
    stats: dict = field(default_factory=dict)


@dataclass
class RedactionConfig:
    """Configuration for PII redaction."""
    # Detection settings
    enabled_entity_types: list[PIIEntityType] = field(default_factory=lambda: list(PIIEntityType))
    min_confidence: float = 0.7
    language: str = "en"
    
    # Redaction settings
    strategy: RedactionStrategy = RedactionStrategy.MASK
    mask_char: str = "*"
    preserve_length: bool = True
    custom_replacements: dict[PIIEntityType, str] = field(default_factory=dict)
    
    # Indian context settings
    indian_context: bool = True
    legal_context: bool = True
    
    # Output settings
    return_entities: bool = True
    return_stats: bool = True
    return_redaction_map: bool = False


class IndianPIIRecognizer:
    """Custom recognizer for Indian PII patterns."""
    
    # Indian PII patterns
    PATTERNS = {
        PIIEntityType.AADHAAR: [
            r'\b\d{4}\s?\d{4}\s?\d{4}\b',  # 12 digits with optional spaces
            r'\b\d{12}\b',  # 12 digits continuous
        ],
        PIIEntityType.PAN: [
            r'\b[A-Z]{5}\d{4}[A-Z]\b',  # Standard PAN format
        ],
        PIIEntityType.INDIAN_PHONE: [
            r'\b(?:\+91[\s-]?)?[6-9]\d{9}\b',  # Indian mobile
            r'\b(?:\+91[\s-]?)?0?\d{10}\b',  # Indian landline/mobile
            r'\b(?:\+91[\s-]?)?\d{5}[\s-]?\d{5}\b',  # 5-5 format
        ],
        PIIEntityType.INDIAN_EMAIL: [
            r'\b[A-Za-z0-9._%+-]+@(?:gmail|yahoo|hotmail|outlook|rediff|indiatimes|sify|nic|gov|ac)\.(?:in|co\.in|org\.in|net\.in|gov\.in|ac\.in)\b',
        ],
        PIIEntityType.BANK_ACCOUNT: [
            r'\b\d{9,18}\b',  # Bank account numbers (9-18 digits)
        ],
        PIIEntityType.IFSC: [
            r'\b[A-Z]{4}0[A-Z0-9]{6}\b',  # IFSC code format
        ],
        PIIEntityType.VEHICLE_REG: [
            r'\b[A-Z]{2}\d{2}[A-Z]{1,2}\d{1,4}\b',  # Vehicle registration
        ],
        PIIEntityType.PASSPORT: [
            r'\b[A-PR-WYa-pr-wy][1-9]\d{6}\b',  # Indian passport
        ],
        PIIEntityType.VOTER_ID: [
            r'\b[A-Z]{3}\d{7}\b',  # Voter ID (EPIC)
        ],
        PIIEntityType.DRIVING_LICENSE: [
            r'\b[A-Z]{2}\d{13}\b',  # Driving license
        ],
        PIIEntityType.GST: [
            r'\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b',  # GSTIN
        ],
        PIIEntityType.UPI_ID: [
            r'\b[\w.-]+@(?:oksbi|okhdfc|okicici|okaxis|okbob|okidfc|okindus|okkotak|okyes|okfederal|okrbl|okbandhan|okdbs|okciti|okhsbc|okscb|okidbi|okiob|okpnb|okcanara|okunion|okiobc|okcorp|okandhra|okkarnataka|okkerala|okmaharashtra|okmp|okrajasthan|oktamilnadu|oktelangana|okup|okwestbengal|okjharkhand|okchhattisgarh|okuttarakhand|okhimachal|okgoa|okpunjab|okharyana|okjammu|okladakh|okmanipur|okmeghalaya|okmizoram|oknagaland|oksikkim|oktripura|okarunachal|okassam|okbihar|okodisha)\b',
        ],
        PIIEntityType.CIN: [
            r'\b[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b',  # Corporate Identity Number
        ],
        PIIEntityType.DIN: [
            r'\b\d{8}\b',  # Director Identification Number
        ],
        PIIEntityType.CASE_NUMBER: [
            r'\b(?:WP|WA|CR|CA|MA|SA|RA|FA|OA|IA|TA|PA|BA|CA|DA|EA|GA|HA|IA|JA|KA|LA|MA|NA|OA|PA|QA|RA|SA|TA|UA|VA|WA|XA|YA|ZA)\s*\d{1,6}(?:\/\d{2,4})?\b',
            r'\b\d{1,6}(?:\/\d{2,4})?\s*(?:WP|WA|CR|CA|MA|SA|RA|FA|OA|IA|TA|PA|BA|CA|DA|EA|GA|HA|IA|JA|KA|LA|MA|NA|OA|PA|QA|RA|SA|TA|UA|VA|WA|XA|YA|ZA)\b',
        ],
    }
    
    # Context words that increase confidence for Indian PII
    CONTEXT_KEYWORDS = {
        PIIEntityType.AADHAAR: ["aadhaar", "aadhar", "uid", "unique identification", "uidai"],
        PIIEntityType.PAN: ["pan", "permanent account", "income tax", "tan"],
        PIIEntityType.INDIAN_PHONE: ["mobile", "phone", "contact", "whatsapp", "telephone"],
        PIIEntityType.BANK_ACCOUNT: ["account", "bank", "savings", "current", "ifsc", "branch"],
        PIIEntityType.IFSC: ["ifsc", "branch", "bank", "neft", "rtgs", "imps"],
        PIIEntityType.VEHICLE_REG: ["vehicle", "registration", "rc", "rto", "number plate"],
        PIIEntityType.PASSPORT: ["passport", "travel", "visa", "immigration"],
        PIIEntityType.VOTER_ID: ["voter", "epic", "election", "voting", "electoral"],
        PIIEntityType.DRIVING_LICENSE: ["driving", "license", "dl", "rto", "transport"],
        PIIEntityType.GST: ["gst", "gstin", "goods and services tax", "tax invoice"],
        PIIEntityType.UPI_ID: ["upi", "bhim", "phonepe", "gpay", "paytm", "upi id"],
        PIIEntityType.CIN: ["cin", "corporate identity", "company", "roc", "mca"],
        PIIEntityType.DIN: ["din", "director identification", "director", "mca"],
        PIIEntityType.CASE_NUMBER: ["case", "suit", "petition", "appeal", "writ", "court", "case no", "case number"],
    }
    
    def __init__(self):
        self._compiled_patterns = {}
        for entity_type, patterns in self.PATTERNS.items():
            self._compiled_patterns[entity_type] = [re.compile(p, re.IGNORECASE) for p in patterns]
    
    def detect(self, text: str) -> list[PIIEntity]:
        """Detect Indian PII entities in text."""
        entities = []
        
        for entity_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    start, end = match.span()
                    matched_text = match.group()
                    
                    # Calculate confidence based on context
                    confidence = self._calculate_confidence(text, start, end, entity_type)
                    
                    # Get surrounding context
                    context_start = max(0, start - 50)
                    context_end = min(len(text), end + 50)
                    context = text[context_start:context_end]
                    
                    entities.append(PIIEntity(
                        entity_type=entity_type,
                        text=matched_text,
                        start=start,
                        end=end,
                        confidence=confidence,
                        context=context,
                    ))
        
        return entities
    
    def _calculate_confidence(self, text: str, start: int, end: int, entity_type: PIIEntityType) -> float:
        """Calculate confidence score based on context."""
        base_confidence = 0.8
        
        # Check context keywords
        context_start = max(0, start - 100)
        context_end = min(len(text), end + 100)
        context = text[context_start:context_end].lower()
        
        keywords = self.CONTEXT_KEYWORDS.get(entity_type, [])
        for keyword in keywords:
            if keyword.lower() in context:
                base_confidence = min(0.95, base_confidence + 0.1)
                break
        
        # Additional validation for specific types
        if entity_type == PIIEntityType.AADHAAR:
            # Verify checksum (Verhoeff algorithm)
            if self._verify_aadhaar_checksum(text[start:end]):
                base_confidence = 0.95
            else:
                base_confidence = 0.6
        elif entity_type == PIIEntityType.PAN:
            # PAN format validation
            if self._validate_pan(text[start:end]):
                base_confidence = 0.95
            else:
                base_confidence = 0.6
        elif entity_type == PIIEntityType.GST:
            # GST format validation
            if self._validate_gst(text[start:end]):
                base_confidence = 0.95
            else:
                base_confidence = 0.6
        
        return base_confidence
    
    def _verify_aadhaar_checksum(self, aadhaar: str) -> bool:
        """Verify Aadhaar number using Verhoeff algorithm."""
        # Remove spaces
        aadhaar = re.sub(r'\s', '', aadhaar)
        if len(aadhaar) != 12 or not aadhaar.isdigit():
            return False
        
        # Verhoeff algorithm
        d = [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
            [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
            [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
            [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
            [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
            [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
            [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
            [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
            [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
        ]
        
        p = [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
            [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
            [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
            [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
            [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
            [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
            [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
        ]
        
        c = 0
        for i, ch in enumerate(reversed(aadhaar)):
            c = d[c][p[i % 8][int(ch)]]
        
        return c == 0
    
    def _validate_pan(self, pan: str) -> bool:
        """Validate PAN format."""
        if len(pan) != 10:
            return False
        if not pan[:5].isalpha() or not pan[5:9].isdigit() or not pan[9].isalpha():
            return False
        return pan[:5].isupper() and pan[9].isupper()
    
    def _validate_gst(self, gst: str) -> bool:
        """Validate GSTIN format."""
        if len(gst) != 15:
            return False
        # Basic format check
        if not gst[:2].isdigit():
            return False
        if not gst[2:7].isalpha():
            return False
        if not gst[7:11].isdigit():
            return False
        if not gst[11].isalpha():
            return False
        if not gst[12].isalnum():
            return False
        if gst[13] != 'Z':
            return False
        if not gst[14].isalnum():
            return False
        return True


class LegalPIIRecognizer:
    """Custom recognizer for legal document PII."""
    
    PATTERNS = {
        PIIEntityType.COURT_NAME: [
            r'\b(?:Supreme Court|High Court|District Court|Sessions Court|Civil Court|Criminal Court|Family Court|Consumer Court|Tribunal|Commission|Forum|Authority|Board)\s+(?:of\s+)?[A-Za-z\s]{1,30}?\b(?=\s+(?:by|in|at|on|for|vs|v\.|versus|,|;|\.|$))',
            r'\b(?:Hon\'ble|Honorable)\s+(?:Supreme Court|High Court|District Court)\b',
        ],
        PIIEntityType.LAWYER_NAME: [
            r'\b(?:Adv|Advocate|Sr\.?\s*Adv|Senior\s+Advocate|Mr\.?|Mrs\.?|Ms\.?)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b',
        ],
        PIIEntityType.JUDGE_NAME: [
            r'\b(?:Hon\'ble|Honorable|Justice|Judge)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b',
        ],
    }
    
    def __init__(self):
        self._compiled_patterns = {}
        for entity_type, patterns in self.PATTERNS.items():
            self._compiled_patterns[entity_type] = [re.compile(p, re.IGNORECASE) for p in patterns]
    
    def detect(self, text: str) -> list[PIIEntity]:
        """Detect legal PII entities in text."""
        entities = []
        
        for entity_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    start, end = match.span()
                    matched_text = match.group()
                    
                    entities.append(PIIEntity(
                        entity_type=entity_type,
                        text=matched_text,
                        start=start,
                        end=end,
                        confidence=0.85,
                        context=text[max(0, start-50):min(len(text), end+50)],
                    ))
        
        return entities


class PIIDetectionEngine:
    """Main PII detection engine combining multiple recognizers."""
    
    def __init__(self, config: Optional[RedactionConfig] = None):
        self.config = config or RedactionConfig()
        self.indian_recognizer = IndianPIIRecognizer()
        self.legal_recognizer = LegalPIIRecognizer()
        self._presidio_analyzer = None
        self._presidio_anonymizer = None
        self._init_presidio()
    
    def _init_presidio(self):
        """Initialize Presidio analyzer and anonymizer."""
        if not PRESIDIO_AVAILABLE:
            self._presidio_analyzer = None
            self._presidio_anonymizer = None
            return

        try:
            # Configure NLP engine
            nlp_provider = NlpEngineProvider(nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [
                    {"lang_code": "en", "model_name": "en_core_web_lg"},
                    {"lang_code": "hi", "model_name": "xx_ent_wiki_sm"},  # Multilingual for Hindi/Devanagari
                ],
            })
            nlp_engine = nlp_provider.create_engine()
            
            # Create analyzer with custom recognizers
            registry = RecognizerRegistry()
            registry.load_predefined_recognizers()
            
            self._presidio_analyzer = AnalyzerEngine(
                nlp_engine=nlp_engine,
                registry=registry,
                supported_languages=["en", "hi"],
            )
            self._presidio_anonymizer = AnonymizerEngine()
        except Exception:
            # Presidio not available, fall back to regex-only
            self._presidio_analyzer = None
            self._presidio_anonymizer = None
    
    def detect(self, text: str) -> list[PIIEntity]:
        """Detect all PII entities in text."""
        all_entities = []
        
        # 1. Indian PII patterns
        if self.config.indian_context:
            indian_entities = self.indian_recognizer.detect(text)
            all_entities.extend(indian_entities)
        
        # 2. Legal PII patterns
        if self.config.legal_context:
            legal_entities = self.legal_recognizer.detect(text)
            all_entities.extend(legal_entities)
        
        # 3. Presidio (general PII)
        if self._presidio_analyzer:
            try:
                results = self._presidio_analyzer.analyze(
                    text=text,
                    language=self.config.language,
                    entities=[e.value for e in self.config.enabled_entity_types if e not in [
                        PIIEntityType.AADHAAR, PIIEntityType.PAN, PIIEntityType.INDIAN_PHONE,
                        PIIEntityType.INDIAN_EMAIL, PIIEntityType.BANK_ACCOUNT, PIIEntityType.IFSC,
                        PIIEntityType.VEHICLE_REG, PIIEntityType.PASSPORT, PIIEntityType.VOTER_ID,
                        PIIEntityType.DRIVING_LICENSE, PIIEntityType.GST, PIIEntityType.UPI_ID,
                        PIIEntityType.CIN, PIIEntityType.DIN, PIIEntityType.CASE_NUMBER,
                        PIIEntityType.COURT_NAME, PIIEntityType.LAWYER_NAME, PIIEntityType.JUDGE_NAME,
                    ]],
                    return_decision_process=False,
                )
                
                for result in results:
                    if result.score >= self.config.min_confidence:
                        entity_type = self._map_presidio_entity(result.entity_type)
                        if entity_type:
                            all_entities.append(PIIEntity(
                                entity_type=entity_type,
                                text=text[result.start:result.end],
                                start=result.start,
                                end=result.end,
                                confidence=result.score,
                                context=text[max(0, result.start-50):min(len(text), result.end+50)],
                            ))
            except Exception:
                pass
        
        # Filter by enabled entity types
        if self.config.enabled_entity_types:
            all_entities = [e for e in all_entities if e.entity_type in self.config.enabled_entity_types]
        
        # Deduplicate overlapping entities
        return self._deduplicate_entities(all_entities)
    
    def _map_presidio_entity(self, presidio_type: str) -> Optional[PIIEntityType]:
        """Map Presidio entity type to our enum."""
        mapping = {
            "EMAIL_ADDRESS": PIIEntityType.EMAIL,
            "PHONE_NUMBER": PIIEntityType.PHONE,
            "PERSON": PIIEntityType.PERSON,
            "LOCATION": PIIEntityType.LOCATION,
            "DATE_TIME": PIIEntityType.DATE,
            "CREDIT_CARD": PIIEntityType.CREDIT_CARD,
            "IP_ADDRESS": PIIEntityType.IP_ADDRESS,
            "URL": PIIEntityType.URL,
            "NRP": PIIEntityType.PERSON,  # Nationality/Religion/Political
        }
        return mapping.get(presidio_type)
    
    def _deduplicate_entities(self, entities: list[PIIEntity]) -> list[PIIEntity]:
        """Remove overlapping entities, keeping highest confidence."""
        if not entities:
            return []
        
        # Sort by start position, then by confidence descending
        entities.sort(key=lambda e: (e.start, -e.confidence))
        
        deduplicated = []
        for entity in entities:
            # Check overlap with existing
            overlap = False
            for existing in deduplicated:
                if entity.start < existing.end and entity.end > existing.start:
                    # Overlap detected - keep higher confidence
                    if entity.confidence > existing.confidence:
                        deduplicated.remove(existing)
                        deduplicated.append(entity)
                    overlap = True
                    break
            
            if not overlap:
                deduplicated.append(entity)
        
        # Sort by position
        deduplicated.sort(key=lambda e: e.start)
        return deduplicated
    
    def redact(self, text: str, config: Optional[RedactionConfig] = None) -> RedactionResult:
        """Redact PII from text."""
        config = config or self.config
        entities = self.detect(text)
        
        # Filter by confidence
        entities = [e for e in entities if e.confidence >= config.min_confidence]
        # Filter by enabled types
        entities = [e for e in entities if e.entity_type in config.enabled_entity_types]
        
        if not entities:
            return RedactionResult(
                original_text=text,
                redacted_text=text,
                entities=[],
                stats={"total_entities": 0, "by_type": {}},
            )
        
        # Build redacted text
        redacted_parts = []
        last_end = 0
        redaction_map = {}
        
        for entity in entities:
            # Add text before entity
            redacted_parts.append(text[last_end:entity.start])
            
            # Generate replacement
            replacement = self._generate_replacement(entity, config)
            redaction_map[entity.text] = replacement
            redacted_parts.append(replacement)
            
            last_end = entity.end
        
        # Add remaining text
        redacted_parts.append(text[last_end:])
        redacted_text = "".join(redacted_parts)
        
        # Stats
        stats = {
            "total_entities": len(entities),
            "by_type": {},
        }
        for entity in entities:
            t = entity.entity_type.value
            stats["by_type"][t] = stats["by_type"].get(t, 0) + 1
        
        return RedactionResult(
            original_text=text,
            redacted_text=redacted_text,
            entities=entities if config.return_entities else [],
            redaction_map=redaction_map if config.return_redaction_map else {},
            stats=stats if config.return_stats else {},
        )
    
    def _generate_replacement(self, entity: PIIEntity, config: RedactionConfig) -> str:
        """Generate replacement text based on strategy."""
        # Check custom replacement
        if entity.entity_type in config.custom_replacements:
            return config.custom_replacements[entity.entity_type]
        
        original = entity.text
        length = len(original)
        
        if config.strategy == RedactionStrategy.MASK:
            if config.preserve_length:
                # Preserve non-alphanumeric characters (spaces, dashes, etc.)
                return "".join(config.mask_char if c.isalnum() else c for c in original)
            else:
                return f"[{entity.entity_type.value}]"
        
        elif config.strategy == RedactionStrategy.REPLACE:
            return f"[{entity.entity_type.value}]"
        
        elif config.strategy == RedactionStrategy.HASH:
            hash_val = hashlib.sha256(original.encode()).hexdigest()[:8]
            return f"[{entity.entity_type.value}_{hash_val}]"
        
        elif config.strategy == RedactionStrategy.REMOVE:
            return ""
        
        elif config.strategy == RedactionStrategy.PSEUDONYMIZE:
            # Generate consistent pseudonym
            hash_val = hashlib.sha256(f"{entity.entity_type.value}:{original}".encode()).hexdigest()[:8]
            return f"{entity.entity_type.value}_{hash_val}"
        
        return f"[{entity.entity_type.value}]"
    
    def redact_document(self, document: dict, config: Optional[RedactionConfig] = None) -> dict:
        """Redact PII from a document dictionary."""
        config = config or self.config
        redacted_doc = document.copy()
        
        # Redact text fields
        text_fields = ["content", "text", "body", "description", "summary", "title"]
        for field in text_fields:
            if field in redacted_doc and isinstance(redacted_doc[field], str):
                result = self.redact(redacted_doc[field], config)
                redacted_doc[field] = result.redacted_text
                if config.return_entities:
                    redacted_doc[f"{field}_pii_entities"] = [
                        {"type": e.entity_type.value, "text": e.text, "confidence": e.confidence}
                        for e in result.entities
                    ]
        
        return redacted_doc


# ==================== Convenience Functions ====================

@lru_cache(maxsize=1)
def get_pii_engine() -> PIIDetectionEngine:
    """Get singleton PII detection engine."""
    return PIIDetectionEngine()


def detect_pii(text: str, config: Optional[RedactionConfig] = None) -> list[PIIEntity]:
    """Detect PII in text."""
    engine = get_pii_engine()
    if config:
        engine.config = config
    return engine.detect(text)


def redact_pii(text: str, config: Optional[RedactionConfig] = None) -> RedactionResult:
    """Redact PII from text."""
    engine = get_pii_engine()
    return engine.redact(text, config)


def redact_document(document: dict, config: Optional[RedactionConfig] = None) -> dict:
    """Redact PII from document."""
    engine = get_pii_engine()
    return engine.redact_document(document, config)


# ==================== Document Pipeline Integration ====================

class PIIRedactionPipeline:
    """Pipeline for redacting PII from documents during ingestion."""
    
    def redact(self, text: str, strategy: Optional[RedactionStrategy] = None) -> RedactionResult:
        """Redact text using configured or specified strategy."""
        cfg = self.config
        if strategy:
            cfg = RedactionConfig(
                strategy=strategy,
                mask_char=self.config.mask_char,
                preserve_length=self.config.preserve_length,
                enabled_entity_types=self.config.enabled_entity_types,
                min_confidence=self.config.min_confidence,
                custom_replacements=self.config.custom_replacements,
                indian_context=self.config.indian_context,
                legal_context=self.config.legal_context,
            )
        return self.engine.redact_text(text, cfg)

    def process_document(self, document: dict, config: Optional[RedactionConfig] = None) -> dict:
        """Process a single document for PII redaction."""
        cfg = config or self.config
        return self.engine.redact_document(document, cfg)
    
    def process_batch(self, documents: list[dict], config: Optional[RedactionConfig] = None) -> list[dict]:
        """Process multiple documents."""
        cfg = config or self.config
        return [self.engine.redact_document(doc, cfg) for doc in documents]
    
    def process_case_documents(self, case_id: str) -> dict:
        """Process all documents for a case."""
        from app.config import get_settings
        from supabase import create_client
        
        settings = get_settings()
        db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        
        # Get documents
        docs = db.table("documents").select("*").eq("case_id", case_id).execute().data or []
        
        results = {
            "case_id": case_id,
            "total_documents": len(docs),
            "processed": 0,
            "entities_found": 0,
            "by_type": {},
        }
        
        for doc in docs:
            redacted = self.process_document(doc)
            
            # Update document in database
            update_data = {
                "content": redacted.get("content", doc.get("content")),
                "pii_redacted": True,
                "pii_entities": redacted.get("content_pii_entities", []),
                "pii_redacted_at": "now()",
            }
            db.table("documents").update(update_data).eq("id", doc["id"]).execute()
            
            results["processed"] += 1
            for entity in redacted.get("content_pii_entities", []):
                results["entities_found"] += 1
                t = entity["type"]
                results["by_type"][t] = results["by_type"].get(t, 0) + 1
        
        return results


# ==================== Export ====================

__all__ = [
    "PIIEntityType",
    "RedactionStrategy",
    "PIIEntity",
    "RedactionResult",
    "RedactionConfig",
    "PIIDetectionEngine",
    "IndianPIIRecognizer",
    "LegalPIIRecognizer",
    "PIIRedactionPipeline",
    "get_pii_engine",
    "detect_pii",
    "redact_pii",
    "redact_document",
]