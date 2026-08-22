"""Indian Date Format Parser.

Supports multiple Indian date formats:
- DD/MM/YYYY, DD-MM-YYYY, DD MM YYYY
- Devanagari numerals (०-९)
- Vikram Samvat (V.S. 2060 → 2003 CE, offset 57)
- Shalivahana Shaka (S.S. 1925 → 2003 CE, offset 78)
- Marathi months (चैत्र, वैशाख, ज्येष्ठ, आषाढ, श्रावण, भाद्रपद, आश्विन, कार्तिक, मार्गशीर्ष, पौष, माघ, फाल्गुन)
"""

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


class IndianDateParser:
    """Parse Indian date formats including Devanagari numerals and Vikram Samvat."""

    # Devanagari to Arabic numerals mapping
    DEVANAGARI_TO_ARABIC = {
        "०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
        "५": "5", "६": "6", "७": "7", "८": "8", "९": "9"
    }

    # Marathi months mapping
    MARATHI_MONTHS = {
        "चैत्र": 1, "वैशाख": 2, "ज्येष्ठ": 3, "आषाढ": 4,
        "श्रावण": 5, "भाद्रपद": 6, "आश्विन": 7, "कार्तिक": 8,
        "मार्गशीर्ष": 9, "पौष": 10, "माघ": 11, "फाल्गुन": 12,
        "chaitra": 1, "vaishakha": 2, "jyeshtha": 3, "ashadha": 4,
        "shravana": 5, "bhadrapada": 6, "ashwin": 7, "kartik": 8,
        "margashirsha": 9, "pausha": 10, "magha": 11, "phalguna": 12
    }

    # English months mapping
    ENGLISH_MONTHS = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }

    # Historical calendar offsets
    VIKRAM_SAMVAT_OFFSET = 57      # V.S. 2060 - 57 = 2003 CE
    SHALIVAHANA_SHAKA_OFFSET = -78  # S.S. 1925 + 78 = 2003 CE

    @classmethod
    def convert_devanagari_to_arabic(cls, text: str) -> str:
        """Convert Devanagari numerals to Arabic numerals."""
        for devanagari, arabic in cls.DEVANAGARI_TO_ARABIC.items():
            text = text.replace(devanagari, arabic)
        return text

    @classmethod
    def parse_date(cls, text: str) -> Optional[datetime]:
        """Parse Indian date formats returning datetime or None."""
        if not text or not isinstance(text, str):
            return None

        clean_text = text.strip()
        clean_text = cls.convert_devanagari_to_arabic(clean_text)

        # 1. Vikram Samvat or Shalivahana Shaka Era
        era_match = re.search(r'(?:V\.S\.|Vikram\s+Samvat)\s*[:\-]?\s*(\d{4})', clean_text, re.IGNORECASE)
        if era_match:
            try:
                vs_year = int(era_match.group(1))
                ce_year = vs_year - cls.VIKRAM_SAMVAT_OFFSET
                return datetime(ce_year, 1, 1, tzinfo=timezone.utc)
            except Exception:
                pass

        shaka_match = re.search(r'(?:S\.S\.|Shalivahana\s+Shaka|Shaka\s+Samvat)\s*[:\-]?\s*(\d{4})', clean_text, re.IGNORECASE)
        if shaka_match:
            try:
                ss_year = int(shaka_match.group(1))
                ce_year = ss_year + 78
                return datetime(ce_year, 1, 1, tzinfo=timezone.utc)
            except Exception:
                pass

        # 2. Standard DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
        dmy_match = re.search(r'\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b', clean_text)
        if dmy_match:
            try:
                day = int(dmy_match.group(1))
                month = int(dmy_match.group(2))
                year = int(dmy_match.group(3))
                if 1 <= day <= 31 and 1 <= month <= 12 and 1800 <= year <= 2100:
                    return datetime(year, month, day, tzinfo=timezone.utc)
            except Exception:
                pass

        # 3. Named Month: DD Month YYYY
        month_word_pattern = r'\b(\d{1,2})\s+([a-zA-Z\u0900-\u097F]+)\s+(\d{4})\b'
        named_match = re.search(month_word_pattern, clean_text)
        if named_match:
            day_str, m_str, y_str = named_match.groups()
            m_lower = m_str.lower()
            month_num = cls.MARATHI_MONTHS.get(m_lower) or cls.ENGLISH_MONTHS.get(m_lower)
            if month_num:
                try:
                    day = int(day_str)
                    year = int(y_str)
                    if 1 <= day <= 31 and 1800 <= year <= 2100:
                        return datetime(year, month_num, day, tzinfo=timezone.utc)
                except Exception:
                    pass

        return None

    @classmethod
    def extract_dates(cls, text: str) -> List[Tuple[datetime, str, int, int]]:
        """Extract all Indian dates from text returning (datetime, matched_text, start, end)."""
        if not text:
            return []

        results = []
        normalized_text = cls.convert_devanagari_to_arabic(text)

        # Regex for DD/MM/YYYY and DD-MM-YYYY
        for match in re.finditer(r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4}\b', normalized_text):
            raw = match.group(0)
            dt = cls.parse_date(raw)
            if dt:
                results.append((dt, raw, match.start(), match.end()))

        # Regex for Era matches
        for match in re.finditer(r'(?:V\.S\.|Vikram\s+Samvat|S\.S\.|Shaka\s+Samvat)\s*[:\-]?\s*\d{4}', normalized_text, re.IGNORECASE):
            raw = match.group(0)
            dt = cls.parse_date(raw)
            if dt:
                results.append((dt, raw, match.start(), match.end()))

        return results


def parse_indian_date(text: str) -> Optional[datetime]:
    """Parse Indian date formats from text."""
    return IndianDateParser.parse_date(text)


def extract_indian_dates(text: str) -> List[Tuple[datetime, str, int, int]]:
    """Extract all Indian dates from text."""
    return IndianDateParser.extract_dates(text)
