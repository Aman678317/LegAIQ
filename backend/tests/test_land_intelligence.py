"""Tests for Indian Land & Property Document Intelligence Engine."""
from app.ai.land_intelligence import (
    parse_and_normalize_area,
    are_land_areas_equivalent,
    land_extractor,
)


def test_parse_and_normalize_area_acres_and_guntas():
    norm = parse_and_normalize_area("2 Acres 14 Guntas")
    assert norm.acres > 2.3
    assert norm.sq_meters > 9000
    assert norm.sq_feet > 100000
    assert "Acre" in norm.formatted_standard
    assert "Gunta" in norm.formatted_standard


def test_parse_and_normalize_area_sq_feet():
    norm = parse_and_normalize_area("1200 Sq.Ft")
    assert round(norm.sq_meters, 1) == 111.5
    assert "Sq.Ft" in norm.formatted_standard


def test_parse_and_normalize_area_hectares():
    norm = parse_and_normalize_area("1.5 Hectares")
    assert norm.sq_meters == 15000.0
    assert norm.acres > 3.7


def test_are_land_areas_equivalent_units():
    # 1 Guntha = 1089 Sq.Ft
    is_equiv, expl = are_land_areas_equivalent("1 Gunta", "1089 Sq.Ft")
    assert is_equiv is True

    # 1 Acre = 40 Guntas
    is_equiv2, expl2 = are_land_areas_equivalent("1 Acre", "40 Guntas")
    assert is_equiv2 is True

    # Mismatch check: 2 Acres vs 1 Gunta
    is_equiv3, expl3 = are_land_areas_equivalent("2 Acres", "1 Gunta")
    assert is_equiv3 is False


def test_land_extractor_revenue_entities():
    sample_text = """
    7/12 Extract (Satbara) - Maharashtra
    Gao: Hinjawadi, Taluka: Mulshi, Jilha: Pune
    Gat No: 142/2/A, Khata No: 581, CTS No: 492
    Hissa No: 3, Plot No: 12
    Total Shetra: measuring 1 Acre 20 Guntas
    Itar Adhikar (Bojha): Bank of Maharashtra Mortgage Charge Rs. 15,00,000/-
    Bounded on East by: Survey 141, West by: Road, North by: Nalla, South by: Survey 143
    """
    entities = land_extractor.extract_from_text(sample_text)
    types = {e["entity_type"] for e in entities}
    values_by_type = {e["entity_type"]: e["value"] for e in entities}

    assert "gat_number" in types
    assert values_by_type["gat_number"] == "142/2/A"
    assert "khata_number" in types
    assert values_by_type["khata_number"] == "581"
    assert "cts_number" in types
    assert values_by_type["cts_number"] == "492"
    assert "village" in types
    assert values_by_type["village"] == "Hinjawadi"
    assert "taluk" in types
    assert values_by_type["taluk"] == "Mulshi"
    assert "district" in types
    assert values_by_type["district"] == "Pune"
    assert "area" in types
    assert "encumbrance" in types
    assert "boundary_east" in types


def test_generate_lawyer_questions():
    entities = [
        {"entity_type": "survey_number", "value": "124/3"},
        {"entity_type": "encumbrance", "value": "Bank Mortgage"},
    ]
    mismatches = [
        {"field_name": "survey_number", "explanation": "Sale Deed records 124/3, Partition Deed records 124/2"}
    ]
    risks = []
    questions = land_extractor.generate_lawyer_questions("Whitefield Land", entities, mismatches, risks)
    assert len(questions) >= 4
    assert any("Survey Number Mismatch" in q for q in questions)
    assert any("Mortgage / Charge Noted" in q for q in questions)


def test_land_extractor_location_and_survey_variations():
    # Test Taluk, Taluka, Tehsil, Hobli and variations
    text1 = "Taluk: Mulshi, Village: Hinjawadi, District: Pune, Survey No: 124/3"
    e1 = {e["entity_type"]: e["value"] for e in land_extractor.extract_from_text(text1)}
    assert e1["taluk"] == "Mulshi"
    assert e1["village"] == "Hinjawadi"
    assert e1["district"] == "Pune"
    assert e1["survey_number"] == "124/3"

    text2 = "Tehsil: Haveli, Mauza: Wakad, Dist.: Pune, Gat Number: 55/1"
    e2 = {e["entity_type"]: e["value"] for e in land_extractor.extract_from_text(text2)}
    assert e2["taluk"] == "Haveli"
    assert e2["village"] == "Wakad"
    assert e2["district"] == "Pune"
    assert e2["gat_number"] == "55/1"

    text3 = "Hobli: Kasaba, Grama: Kadugodi, Dist: Bengaluru, Khasra No: 88"
    e3 = {e["entity_type"]: e["value"] for e in land_extractor.extract_from_text(text3)}
    assert e3["taluk"] == "Kasaba"
    assert e3["village"] == "Kadugodi"
    assert e3["district"] == "Bengaluru"
    assert e3["khasra_number"] == "88"

