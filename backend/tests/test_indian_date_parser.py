"""Tests for Indian Date Parser Multi-Format Support."""

import pytest
from datetime import datetime, timezone
from app.utils.indian_date_parser import (
    IndianDateParser,
    parse_indian_date,
    extract_indian_dates,
)


def test_standard_dmy_parsing():
    """Test standard DD/MM/YYYY and DD-MM-YYYY formats."""
    d1 = parse_indian_date("15/06/2003")
    assert d1 is not None
    assert d1.day == 15
    assert d1.month == 6
    assert d1.year == 2003

    d2 = parse_indian_date("26-01-1950")
    assert d2 is not None
    assert d2.day == 26
    assert d2.month == 1
    assert d2.year == 1950


def test_devanagari_numeral_parsing():
    """Test dates written in Devanagari numerals (०-९)."""
    # १५/६/२००३ -> 15/6/2003
    d = parse_indian_date("१५/०६/२००३")
    assert d is not None
    assert d.day == 15
    assert d.month == 6
    assert d.year == 2003


def test_vikram_samvat_conversion():
    """Test Vikram Samvat year conversion to CE (V.S. 2060 -> 2003 CE)."""
    d = parse_indian_date("V.S. 2060")
    assert d is not None
    assert d.year == 2003

    d2 = parse_indian_date("Vikram Samvat: 2075")
    assert d2 is not None
    assert d2.year == 2018


def test_shalivahana_shaka_conversion():
    """Test Shalivahana Shaka year conversion to CE (S.S. 1925 -> 2003 CE)."""
    d = parse_indian_date("S.S. 1925")
    assert d is not None
    assert d.year == 2003


def test_marathi_month_parsing():
    """Test named Marathi months (चैत्र, वैशाख, etc.)."""
    d = parse_indian_date("15 चैत्र 2024")
    assert d is not None
    assert d.day == 15
    assert d.month == 1
    assert d.year == 2024


def test_extract_multiple_dates():
    """Test extracting multiple dates from legal text."""
    text = "Sale deed executed on 15/06/2003 and registered on 20/07/2003 under V.S. 2060."
    dates = extract_indian_dates(text)
    assert len(dates) >= 2
    years = [dt[0].year for dt in dates]
    assert 2003 in years
