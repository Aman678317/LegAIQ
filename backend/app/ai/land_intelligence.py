"""Indian Land & Property Document Intelligence Engine.

Specialized parsing, unit normalization, cross-document reconciliation,
and risk detection across all Indian Revenue and Property instruments:
- 7/12 Extracts (Maharashtra / Gujarat Satbara)
- RTC Pahani (Karnataka Bhoomi)
- Khasra & Khatoni Jamabandi (UP, MP, Bihar, Rajasthan, Delhi, Punjab, Haryana)
- Property Card & CTS Extract (Urban Land Records)
- Registered Conveyance Deeds (Sale, Gift, Partition, Release, Mortgage, GPA)
"""

import re
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple


# Standard land measurement conversions to Square Meters
SQ_METER_CONVERSIONS = {
    "sq_meter": 1.0,
    "sq_m": 1.0,
    "sq_feet": 0.092903,
    "sq_ft": 0.092903,
    "sq_yard": 0.836127,
    "sq_yd": 0.836127,
    "acre": 4046.8564224,
    "guntha": 101.17141056,
    "gunta": 101.17141056,
    "cent": 40.468564,
    "hectare": 10000.0,
    "ground": 222.967, # 2400 sq ft
    "bigha_standard": 2529.285, # Standard Pucca Bigha
    "biswa": 126.464, # 1/20 Bigha
    "katha": 66.89, # Bengal / Bihar Katha (1/20 Bigha)
    "kanal": 505.857, # 1/8 Acre
    "marla": 25.293, # 1/20 Kanal
}


@dataclass
class NormalizedLandArea:
    raw_text: str
    acres: float = 0.0
    guntas: float = 0.0
    sq_meters: float = 0.0
    sq_feet: float = 0.0
    formatted_standard: str = ""


@dataclass
class IndianPropertyProfile:
    survey_or_gat_number: Optional[str] = None
    hissa_number: Optional[str] = None
    khasra_number: Optional[str] = None
    khatoni_number: Optional[str] = None
    cts_number: Optional[str] = None
    plot_number: Optional[str] = None
    village: Optional[str] = None
    taluk_or_tehsil: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    total_area: Optional[NormalizedLandArea] = None
    potkharab_uncultivable_area: Optional[NormalizedLandArea] = None
    cultivable_area: Optional[NormalizedLandArea] = None
    recorded_owners: List[Dict[str, Any]] = field(default_factory=list)
    mutation_entries: List[Dict[str, Any]] = field(default_factory=list)
    encumbrances_and_liens: List[Dict[str, Any]] = field(default_factory=list)
    land_tenure_class: Optional[str] = None # e.g. Bhogwata Varg 1, Bhumidhari with transferable rights
    boundary_schedule: Dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0


def parse_and_normalize_area(raw: str) -> NormalizedLandArea:
    """Parses arbitrary Indian land area strings (e.g. '2 Acres 14 Guntas',
    '1.5 Hectare', '5 Bigha 10 Biswa', '1200 Sq.Ft') into unified metric & imperial metrics."""
    text = raw.strip().lower()
    total_sq_meters = 0.0

    # 1. Acres + Guntas / Cents (e.g. 2 Acres 14 Guntas or 2-14 A-G)
    ag_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:acre|acres|ac|a)[\s,]+(\d+(?:\.\d+)?)\s*(?:gunta|guntas|gts|g|cents|cent|c)", text)
    if ag_match:
        ac = float(ag_match.group(1))
        gt = float(ag_match.group(2))
        total_sq_meters = (ac * SQ_METER_CONVERSIONS["acre"]) + (gt * SQ_METER_CONVERSIONS["guntha"])
    else:
        # Single acre match
        ac_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:acre|acres|ac)\b", text)
        if ac_match:
            total_sq_meters += float(ac_match.group(1)) * SQ_METER_CONVERSIONS["acre"]

        # Single gunta match
        gt_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:gunta|guntas|gts)\b", text)
        if gt_match and not ac_match:
            total_sq_meters += float(gt_match.group(1)) * SQ_METER_CONVERSIONS["guntha"]

        # Hectare match
        hec_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hectare|hectares|hec|ha)\b", text)
        if hec_match:
            total_sq_meters += float(hec_match.group(1)) * SQ_METER_CONVERSIONS["hectare"]

        # Bigha & Biswa match
        bigha_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:bigha|bighas|b)\b", text)
        biswa_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:biswa|biswas)\b", text)
        if bigha_match:
            total_sq_meters += float(bigha_match.group(1)) * SQ_METER_CONVERSIONS["bigha_standard"]
        if biswa_match:
            total_sq_meters += float(biswa_match.group(1)) * SQ_METER_CONVERSIONS["biswa"]

        # Square Feet / Yards / Meters match
        sqft_match = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:sq\.?\s*ft|sq\.?\s*feet|square\s+feet)\b", text)
        if sqft_match:
            num = float(sqft_match.group(1).replace(",", ""))
            total_sq_meters += num * SQ_METER_CONVERSIONS["sq_feet"]

        sqm_match = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:sq\.?\s*m|sq\.?\s*meter|sq\.?\s*meters|square\s+meters)\b", text)
        if sqm_match:
            num = float(sqm_match.group(1).replace(",", ""))
            total_sq_meters += num

    if total_sq_meters <= 0.0:
        return NormalizedLandArea(raw_text=raw, formatted_standard=raw)

    acres_val = total_sq_meters / SQ_METER_CONVERSIONS["acre"]
    whole_acres = int(acres_val)
    rem_guntas = (acres_val - whole_acres) * 40.0
    sq_feet_val = total_sq_meters / SQ_METER_CONVERSIONS["sq_feet"]

    if whole_acres > 0 or rem_guntas > 0.05:
        std_fmt = f"{whole_acres} Acre(s) {round(rem_guntas, 2)} Gunta(s) ({round(total_sq_meters, 1)} Sq.M / {int(round(sq_feet_val))} Sq.Ft)"
    else:
        std_fmt = f"{round(total_sq_meters, 2)} Sq.M ({int(round(sq_feet_val))} Sq.Ft)"

    return NormalizedLandArea(
        raw_text=raw,
        acres=round(acres_val, 4),
        guntas=round(acres_val * 40.0, 2),
        sq_meters=round(total_sq_meters, 2),
        sq_feet=round(sq_feet_val, 1),
        formatted_standard=std_fmt,
    )


def are_land_areas_equivalent(area_str_a: str, area_str_b: str, tolerance_ratio: float = 0.05) -> Tuple[bool, str]:
    """Compares two land area expressions under different Indian measurement units.
    Allows for customary survey margin tolerance (default 5%)."""
    norm_a = parse_and_normalize_area(area_str_a)
    norm_b = parse_and_normalize_area(area_str_b)

    if norm_a.sq_meters == 0.0 or norm_b.sq_meters == 0.0:
        # Fallback to string equality check
        clean_a = re.sub(r"[^\w]", "", area_str_a.lower())
        clean_b = re.sub(r"[^\w]", "", area_str_b.lower())
        return (clean_a == clean_b), f"Literal match: {clean_a == clean_b}"

    diff = abs(norm_a.sq_meters - norm_b.sq_meters)
    avg = (norm_a.sq_meters + norm_b.sq_meters) / 2.0
    ratio = diff / avg if avg > 0 else 1.0

    is_equiv = ratio <= tolerance_ratio
    explanation = (
        f"Doc A: {norm_a.formatted_standard} vs Doc B: {norm_b.formatted_standard} "
        f"(Variance: {round(ratio * 100, 1)}% — {'Consistent within survey tolerance' if is_equiv else 'Significant Area Discrepancy'})"
    )
    return is_equiv, explanation


class IndianLandExtractor:
    """Extracts specialized Indian revenue and property entities."""

    SURVEY_PATTERNS = [
        (r"(?:Survey|Sy\.?|S\.No\.?|Survey\s*No\.?)\s*[:#-]?\s*([\d]+[/-][\d\w/-]+|\d+)", "survey_number"),
        (r"(?:Gat|Gut|Gat\s*No\.?)\s*[:#-]?\s*([\d]+[/-][\d\w/-]+|\d+)", "gat_number"),
        (r"(?:Khasra|Khesra|Khasra\s*No\.?)\s*[:#-]?\s*([\d]+[/-][\d\w/-]+|\d+)", "khasra_number"),
        (r"(?:Khata|Khatauni|Katha)\s*(?:No\.?)?\s*[:#-]?\s*([\d/-]+)", "khata_number"),
        (r"(?:CTS|City\s*Survey)\s*(?:No\.?)?\s*[:#-]?\s*([\d/\w-]+)", "cts_number"),
        (r"(?:Hissa|Hisse|Sub-division)\s*(?:No\.?)?\s*[:#-]?\s*([\d/\w]+)", "hissa"),
        (r"(?:Plot|Site)\s*(?:No\.?)?\s*[:#-]?\s*([\d/\w-]+)", "plot_number"),
        (r"(?:Doc|Document|Reg\.?\s*No\.?)\s*[:#-]?\s*([\d/\w-]+)", "registration_number"),
    ]

    LOCATION_PATTERNS = [
        (r"(?:Village|Mauza|Grama|Gao)\s*[:#-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", "village"),
        (r"(?:Taluk|Taluka|Tehsil|Hobli)\s*[:#-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", "taluk"),
        (r"(?:District|Dist\.?|Jilha)\s*[:#-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", "district"),
    ]

    BOUNDARY_PATTERNS = [
        (r"(?:East\s*by|East\s*[:-])\s*([^\n;.,]+)", "east"),
        (r"(?:West\s*by|West\s*[:-])\s*([^\n;.,]+)", "west"),
        (r"(?:North\s*by|North\s*[:-])\s*([^\n;.,]+)", "north"),
        (r"(?:South\s*by|South\s*[:-])\s*([^\n;.,]+)", "south"),
    ]

    def extract_from_text(self, text: str, page_number: int = 1) -> List[Dict[str, Any]]:
        results = []

        # 1. Survey & Identification Numbers
        for pattern, etype in self.SURVEY_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                val = m.group(1).strip()
                snippet = text[max(0, m.start() - 30):min(len(text), m.end() + 30)]
                results.append({
                    "entity_type": etype,
                    "value": val,
                    "source_text": snippet,
                    "page_number": page_number,
                    "confidence": 0.85,
                })

        # 2. Location
        for pattern, etype in self.LOCATION_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                val = m.group(1).strip()
                snippet = text[max(0, m.start() - 30):min(len(text), m.end() + 30)]
                results.append({
                    "entity_type": etype,
                    "value": val,
                    "source_text": snippet,
                    "page_number": page_number,
                    "confidence": 0.80,
                })

        # 3. Boundaries (Schedules)
        for pattern, direct in self.BOUNDARY_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                val = m.group(1).strip()
                results.append({
                    "entity_type": f"boundary_{direct}",
                    "value": val,
                    "source_text": text[max(0, m.start() - 20):min(len(text), m.end() + 20)],
                    "page_number": page_number,
                    "confidence": 0.85,
                })

        # 4. Land Area
        area_match = re.search(r"(?:measuring|extent\s*of|area|shetra)\s*[:#-]?\s*([^\n;.]+?(?:acre|acres|gunta|guntas|sq\.?\s*ft|sq\.?\s*meter|hectare|bigha|cents)\b[^\n;.]*)", text, re.IGNORECASE)
        if area_match:
            raw_area = area_match.group(1).strip()
            norm = parse_and_normalize_area(raw_area)
            results.append({
                "entity_type": "area",
                "value": norm.formatted_standard if norm.sq_meters > 0 else raw_area,
                "source_text": text[max(0, area_match.start() - 20):min(len(text), area_match.end() + 20)],
                "page_number": page_number,
                "confidence": 0.90,
            })

        # 5. Encumbrances / Bojha / Bank charges
        enc_match = re.search(r"(?:mortgage|hypothecation|bank\s+charge|encumbrance|bojha|itar\s+adhikar)\s*[:#-]?\s*([^\n;.]+)", text, re.IGNORECASE)
        if enc_match:
            results.append({
                "entity_type": "encumbrance",
                "value": enc_match.group(1).strip()[:200],
                "source_text": text[max(0, enc_match.start() - 20):min(len(text), enc_match.end() + 20)],
                "page_number": page_number,
                "confidence": 0.80,
            })

        return results

    def generate_lawyer_questions(
        self,
        case_name: str,
        entities: List[Dict[str, Any]],
        mismatches: List[Dict[str, Any]],
        risks: List[Dict[str, Any]]
    ) -> List[str]:
        """Generates tailored legal due diligence inquiry questions for an Indian property advocate."""
        questions = []

        # Survey mismatch questions
        survey_mismatches = [m for m in mismatches if "survey" in m.get("field_name", "").lower() or "gat" in m.get("field_name", "").lower()]
        if survey_mismatches:
            questions.append(
                "Survey Number Mismatch Detected: Request certified 11E survey sketch / Tippani and Akarbandh from the Taluk Survey Office to verify official sub-division and hissa bifurcation."
            )

        # Area discrepancy questions
        area_mismatches = [m for m in mismatches if "area" in m.get("field_name", "").lower()]
        if area_mismatches:
            questions.append(
                "Area Extent Discrepancy: Measure actual physical boundaries on site and compare against the original grant order and revenue RTC/7-12 record."
            )

        # Encumbrance & EC gap questions
        has_mortgage = any(e.get("entity_type") == "encumbrance" for e in entities)
        if has_mortgage:
            questions.append(
                "Mortgage / Charge Noted: Obtain a formal No Objection Certificate (NOC) and registered Deed of Reconveyance / Discharge from the lending bank."
            )
        else:
            questions.append(
                "Encumbrance Verification: Obtain a 30-year Nil Encumbrance Certificate (Form 15) from the jurisdictional Sub-Registrar Office."
            )

        # Revenue Mutation & Chain of Title
        questions.append(
            "Mutation Register Verification: Verify certified copies of all J-Slips / MR entries (Mutation Register) corresponding to each historic conveyance in the chain of title."
        )

        # Conversion & Land Use
        questions.append(
            "Agricultural to Non-Agricultural (NA) Status: Confirm whether an official DC Conversion Order under Section 95 (or state equivalent) has been issued for residential/commercial use."
        )

        return questions


land_extractor = IndianLandExtractor()
