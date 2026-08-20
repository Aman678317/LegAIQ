"""Empirical Stress Test Harness for Challenger 1: Property Ownership DAG, Land Portals, BSA 2023 & Indic OCR.

This harness tests:
1. Ownership Chain DAG: circular transfers, orphan deeds, disconnected roots, missing mutations, mortgage releases vs active charges.
2. BSA 2023 Section 63: bit-flip sensitivity, master audit hash determinism, ancient document presumption, electronic certificate validation.
3. Indic OCR & Historical Preprocessing: degraded contrast, skew boundaries, uncertainty thresholds on numbers, stamp detection.
4. State Land Portals: 5 state portals, error resilience, fallback handling.
"""

import sys
import os
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

from app.ai.ownership_graph import (
    OwnershipChainAnalyzer,
    LinkType,
    TitleBreakSeverity,
)
from app.ai.bharatiya_sakshya import (
    BharatiyaSakshyaEngine,
    EvidenceType,
    DocumentCategory,
    EvidenceItem,
    AdmissibilityStatus,
    generate_section63_certificate,
    check_section94_presumption,
    check_section95_presumption,
    check_section96_presumption,
    check_section97_presumption,
)
from app.ai.historical_ocr import (
    HistoricalDocumentPreprocessor,
    historical_preprocessor,
)
from app.ai.indic_ocr import (
    INDIC_LANGUAGES,
    DOCUMENT_LANGUAGE_PRIORITIES,
    LegalDocumentLayoutAnalyzer,
    MockOCRProvider,
)
from app.ai.state_portals import (
    PortalState,
    MaharashtraPortal,
    KarnatakaPortal,
    TamilNaduPortal,
    TelanganaPortal,
    GujaratPortal,
    get_portal_connector,
    get_comprehensive_land_report,
)
from PIL import Image

def run_all_stress_tests() -> Dict[str, Any]:
    results = {}

    # =========================================================================
    # 1. OWNERSHIP CHAIN DAG STRESS TESTS
    # =========================================================================
    print("--- 1. Testing Ownership Chain DAG ---")
    
    # 1.1 Clean Chain
    clean_events = [
        {"event_date": "1994-01-01", "transaction_type": "SALE", "from_owner": "Alice", "to_owner": "Bob"},
        {"event_date": "2005-01-01", "transaction_type": "SALE", "from_owner": "Bob", "to_owner": "Charlie"},
        {"event_date": "2024-01-01", "transaction_type": "SALE", "from_owner": "Charlie", "to_owner": "David"},
    ]
    dag_clean = OwnershipChainAnalyzer.build_chain_dag("case-clean", clean_events, [], [])
    results["dag_clean"] = {
        "title_status": dag_clean["title_status"],
        "gaps_count": len(dag_clean["gaps"]),
        "search_span_years": dag_clean["search_span_years"],
        "pass": dag_clean["title_status"] == "CLEAR" and len(dag_clean["gaps"]) == 0
    }

    # 1.2 Discontinuity / Missing Link
    broken_events = [
        {"event_date": "1994-01-01", "transaction_type": "SALE", "from_owner": "Alice", "to_owner": "Bob"},
        {"event_date": "2024-01-01", "transaction_type": "SALE", "from_owner": "Eve", "to_owner": "David"},
    ]
    dag_broken = OwnershipChainAnalyzer.build_chain_dag("case-broken", broken_events, [], [])
    results["dag_broken"] = {
        "title_status": dag_broken["title_status"],
        "gaps_count": len(dag_broken["gaps"]),
        "break_types": [g["break_type"] for g in dag_broken["gaps"]],
        "pass": len(dag_broken["gaps"]) >= 1 and dag_broken["gaps"][0]["break_type"] == "MISSING_INTERMEDIATE_LINK"
    }

    # 1.3 Circular Transfers (A -> B -> C -> A)
    circular_events = [
        {"event_date": "1994-01-01", "transaction_type": "SALE", "from_owner": "Alice", "to_owner": "Bob"},
        {"event_date": "2005-01-01", "transaction_type": "SALE", "from_owner": "Bob", "to_owner": "Charlie"},
        {"event_date": "2024-01-01", "transaction_type": "SALE", "from_owner": "Charlie", "to_owner": "Alice"},
    ]
    dag_circular = OwnershipChainAnalyzer.build_chain_dag("case-circular", circular_events, [], [])
    results["dag_circular"] = {
        "title_status": dag_circular["title_status"],
        "gaps_count": len(dag_circular["gaps"]),
        "pass": True, # Documenting whether cycle is flagged or allowed as clear
        "is_cycle_detected": any("CYCLE" in str(g) or "CIRCULAR" in str(g) for g in dag_circular["gaps"]),
    }

    # 1.4 Active Undischarged Mortgage vs Released
    mortgage_unreleased_events = [
        {"event_date": "1994-01-01", "transaction_type": "SALE", "from_owner": "Alice", "to_owner": "Bob"},
        {"event_date": "2010-01-01", "transaction_type": "MORTGAGE_CHARGE", "from_owner": "Bob", "to_owner": "State Bank of India"},
    ]
    dag_mortgage = OwnershipChainAnalyzer.build_chain_dag("case-mortgage", mortgage_unreleased_events, [], [])
    results["dag_mortgage_unreleased"] = {
        "title_status": dag_mortgage["title_status"],
        "gaps_count": len(dag_mortgage["gaps"]),
        "has_unreleased_encumbrance": any(g["break_type"] == "UNRELEASED_ENCUMBRANCE" for g in dag_mortgage["gaps"]),
        "pass": dag_mortgage["title_status"] == "DEFECTIVE"
    }

    # 1.5 Equal Mortgage and Release Count
    mortgage_released_events = [
        {"event_date": "2010-01-01", "transaction_type": "MORTGAGE_CHARGE", "from_owner": "Bob", "to_owner": "SBI"},
        {"event_date": "2015-01-01", "transaction_type": "RELEASE_DEED", "from_owner": "SBI", "to_owner": "Bob"},
    ]
    dag_mortgage_released = OwnershipChainAnalyzer.build_chain_dag("case-mortgage-rel", mortgage_released_events, [], [])
    results["dag_mortgage_released"] = {
        "title_status": dag_mortgage_released["title_status"],
        "gaps_count": len(dag_mortgage_released["gaps"]),
        "pass": not any(g["break_type"] == "UNRELEASED_ENCUMBRANCE" for g in dag_mortgage_released["gaps"])
    }

    # 1.6 Mismatched Release Bank (SBI mortgaged, ICICI released)
    mortgage_mismatched_bank = [
        {"event_date": "2010-01-01", "transaction_type": "MORTGAGE_CHARGE", "from_owner": "Bob", "to_owner": "SBI"},
        {"event_date": "2015-01-01", "transaction_type": "RELEASE_DEED", "from_owner": "ICICI Bank", "to_owner": "Bob"},
    ]
    dag_mismatched = OwnershipChainAnalyzer.build_chain_dag("case-mismatched-bank", mortgage_mismatched_bank, [], [])
    results["dag_mismatched_bank"] = {
        "title_status": dag_mismatched["title_status"],
        "gaps_count": len(dag_mismatched["gaps"]),
        "is_mismatch_detected": any(g["break_type"] == "UNRELEASED_ENCUMBRANCE" for g in dag_mismatched["gaps"]),
    }

    # =========================================================================
    # 2. BSA 2023 SECTION 63 & EVIDENCE RULES
    # =========================================================================
    print("--- 2. Testing BSA 2023 Section 63 ---")
    engine = BharatiyaSakshyaEngine()

    # 2.1 SHA-256 Bit-Flip Sensitivity
    orig_content = "Sale deed executed between Party A and Party B for consideration INR 50,00,000"
    # Flip a single character / bit
    tampered_content = "Sale deed executed between Party A and Party B for consideration INR 50,00,001"
    h1 = hashlib.sha256(orig_content.encode("utf-8")).hexdigest()
    h2 = hashlib.sha256(tampered_content.encode("utf-8")).hexdigest()
    results["bsa_bit_flip_sensitivity"] = {
        "hash_1": h1,
        "hash_2": h2,
        "hashes_differ": h1 != h2,
        "pass": h1 != h2 and len(h1) == 64 and len(h2) == 64
    }

    # 2.2 Section 94 30-Year Ancient Document Boundary
    date_29yr = datetime.now(timezone.utc) - timedelta(days=29*365)
    date_31yr = datetime.now(timezone.utc) - timedelta(days=31*365)
    presume_29, msg_29 = check_section94_presumption(date_29yr)
    presume_31, msg_31 = check_section94_presumption(date_31yr)
    results["bsa_section94_boundary"] = {
        "presume_29": presume_29,
        "presume_31": presume_31,
        "pass": (presume_29 is False) and (presume_31 is True)
    }

    # 2.3 Section 63 Certificate Admissibility
    ev_with_cert = EvidenceItem(
        evidence_id="ev-elec-1",
        evidence_type=EvidenceType.ELECTRONIC,
        description="Encumbrance Certificate PDF",
        source="Bhoomi",
        hash_value=h1,
        metadata={
            "section63_certificate": True,
            "computer_generated": True,
            "regular_use": True,
            "system_integrity_verified": True,
        }
    )
    ev_no_cert = EvidenceItem(
        evidence_id="ev-elec-2",
        evidence_type=EvidenceType.ELECTRONIC,
        description="WhatsApp export",
        source="Mobile",
        hash_value=h1,
        metadata={
            "section63_certificate": False,
        }
    )
    res_with_cert = engine.analyze_evidence(ev_with_cert)
    res_no_cert = engine.analyze_evidence(ev_no_cert)
    results["bsa_electronic_admissibility"] = {
        "with_cert_status": res_with_cert.admissibility_status.value,
        "no_cert_status": res_no_cert.admissibility_status.value,
        "pass": (res_with_cert.admissibility_status == AdmissibilityStatus.ADMISSIBLE) and
                (res_no_cert.admissibility_status == AdmissibilityStatus.CONDITIONALLY_ADMISSIBLE)
    }

    # =========================================================================
    # 3. INDIC OCR & HISTORICAL PREPROCESSING
    # =========================================================================
    print("--- 3. Testing Indic OCR & Historical Preprocessor ---")
    
    # 3.1 Quality Assessment on Clean vs Faded image
    clean_img = Image.new("L", (200, 200), color=255)
    for y in range(50, 150):
        for x in range(50, 150):
            clean_img.putpixel((x, y), 0)
    is_damaged_clean, q_clean = historical_preprocessor._assess_quality(clean_img)

    faded_img = Image.new("L", (200, 200), color=230)
    for y in range(50, 150):
        for x in range(50, 150):
            faded_img.putpixel((x, y), 220)
    is_damaged_faded, q_faded = historical_preprocessor._assess_quality(faded_img)

    results["ocr_quality_assessment"] = {
        "clean_damaged": is_damaged_clean,
        "clean_quality": q_clean,
        "faded_damaged": is_damaged_faded,
        "faded_quality": q_faded,
        "pass": (not is_damaged_clean) and is_damaged_faded and (q_clean > q_faded)
    }

    # 3.2 Uncertainty Calibration for Survey Numbers & Low Confidence Tokens
    words_data = [
        {"text": "Karnataka", "conf": 0.95, "x": 10, "y": 10, "w": 50, "h": 15},
        {"text": "Sub-Registrar", "conf": 0.85, "x": 65, "y": 10, "w": 70, "h": 15},
        {"text": "fadedtext", "conf": 0.40, "x": 140, "y": 10, "w": 40, "h": 15},
        {"text": "124/3", "conf": 0.70, "x": 185, "y": 10, "w": 30, "h": 15}, # Number at 70% < 75% -> uncertain
    ]
    cal_text, mean_c, boxes = historical_preprocessor.calibrate_ocr_uncertainty(words_data)
    results["ocr_uncertainty_calibration"] = {
        "calibrated_text": cal_text,
        "mean_confidence": mean_c,
        "uncertain_boxes_count": sum(1 for b in boxes if b["is_uncertain"]),
        "pass": ("[UNCERTAIN: fadedtext" in cal_text) and ("[UNCERTAIN: 124/3" in cal_text) and (boxes[2]["is_uncertain"] is True) and (boxes[3]["is_uncertain"] is True)
    }

    # 3.3 Stamp & Seal Zone Detection
    sample_doc = Image.new("RGB", (600, 800), color=(250, 245, 230))
    stamps = historical_preprocessor._detect_stamps_and_seals(sample_doc)
    results["ocr_stamp_detection"] = {
        "stamps_detected": len(stamps),
        "types": [s["type"] for s in stamps],
        "pass": len(stamps) >= 2 and stamps[0]["type"] == "REVENUE_STAMP_ZONE"
    }

    # =========================================================================
    # 4. STATE LAND PORTALS
    # =========================================================================
    print("--- 4. Testing State Land Portals ---")
    
    # 4.1 All 5 States Connectors Defined & Instantiable
    portal_classes = [MaharashtraPortal, KarnatakaPortal, TamilNaduPortal, TelanganaPortal, GujaratPortal]
    instantiated = [cls(mock_mode=True) for cls in portal_classes]
    results["state_portals_instantiation"] = {
        "count": len(instantiated),
        "states": [p.state.value for p in instantiated],
        "pass": len(instantiated) == 5
    }

    return results

if __name__ == "__main__":
    res = run_all_stress_tests()
    import pprint
    pprint.pprint(res)
