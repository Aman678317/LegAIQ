"""Tests for 13-30 Year Ownership Chain DAG and Title Break Analyzer (Milestone 7)."""
import pytest
from app.ai.ownership_graph import (
    LinkType,
    OwnershipChainAnalyzer,
    TitleBreakSeverity,
)


def test_build_clear_ownership_chain_dag():
    """Verify clean 30-year ownership chain without title breaks."""
    events = [
        {
            "event_date": "1994-05-10",
            "transaction_type": "SALE_DEED",
            "from_owner": "Ramachandra Rao",
            "to_owner": "Venkatappa Gowda",
            "document_number": "DOC/1994/0842",
            "description": "Absolute Sale Deed registered for Sy No. 124/2",
            "verified": True,
        },
        {
            "event_date": "2005-08-20",
            "transaction_type": "INHERITANCE_MUTATION",
            "from_owner": "Venkatappa Gowda",
            "to_owner": "Narasimha Gowda",
            "document_number": "MR/2005/0112",
            "description": "Mutation Register extract following succession",
            "verified": True,
        },
        {
            "event_date": "2018-03-15",
            "transaction_type": "SALE_DEED",
            "from_owner": "Narasimha Gowda",
            "to_owner": "Brigade Enterprises Pvt Ltd",
            "document_number": "DOC/2018/4512",
            "description": "Registered Sale Deed for commercial development",
            "verified": True,
        },
    ]

    dag = OwnershipChainAnalyzer.build_chain_dag(
        case_id="test-case-101",
        events=events,
        entities=[],
        risks=[],
    )

    assert dag["case_id"] == "test-case-101"
    assert len(dag["nodes"]) >= 3
    assert len(dag["edges"]) == 3
    assert len(dag["gaps"]) == 0
    assert dag["title_status"] == "CLEAR"
    assert dag["is_30_year_search_complete"] is False or dag["search_span_years"] == 24


def test_detect_title_chain_discontinuity_break():
    """Verify detection of unexplained intermediate title gap."""
    events = [
        {
            "event_date": "1994-05-10",
            "transaction_type": "SALE_DEED",
            "from_owner": "Ramachandra Rao",
            "to_owner": "Venkatappa Gowda",
        },
        {
            "event_date": "2018-03-15",
            "transaction_type": "SALE_DEED",
            "from_owner": "Suresh Kumar",  # Unexplained seller disconnected from Venkatappa Gowda
            "to_owner": "Brigade Enterprises Pvt Ltd",
        },
    ]

    dag = OwnershipChainAnalyzer.build_chain_dag(
        case_id="test-case-broken",
        events=events,
        entities=[],
        risks=[],
    )

    assert len(dag["gaps"]) >= 1
    gap = dag["gaps"][0]
    assert gap["break_type"] == "MISSING_INTERMEDIATE_LINK"
    assert gap["severity"] == TitleBreakSeverity.HIGH.value
    assert "Venkatappa Gowda" in gap["description"]
    assert "Suresh Kumar" in gap["description"]


def test_detect_unreleased_mortgage_charge():
    """Verify alert when an active mortgage lacks a registered deed of release."""
    events = [
        {
            "event_date": "2010-01-15",
            "transaction_type": "MORTGAGE_CHARGE",
            "from_owner": "Owner A",
            "to_owner": "State Bank of India",
        },
    ]

    dag = OwnershipChainAnalyzer.build_chain_dag(
        case_id="test-case-mortgage",
        events=events,
        entities=[],
        risks=[],
    )

    assert any(g["break_type"] == "UNRELEASED_ENCUMBRANCE" for g in dag["gaps"])
    assert dag["title_status"] == "DEFECTIVE"
