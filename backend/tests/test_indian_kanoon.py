"""Tests for Indian Kanoon Case Law Research & Citation Network (Milestone 7)."""
import pytest
from app.ai.indian_kanoon import BENCHMARK_INDIAN_JUDGMENTS, IndianKanoonClient


@pytest.mark.asyncio
async def test_search_kanoon_judgments():
    """Verify search returns matching Indian precedents with ratio and citation metrics."""
    res = await IndianKanoonClient.search_judgments(
        query="GPA sale transfer of title",
        court="Supreme Court of India",
    )
    assert res["total_found"] > 0
    assert len(res["judgments"]) > 0
    top_hit = res["judgments"][0]
    assert "Suraj Lamp" in top_hit["title"] or top_hit["precedent_strength"] == "LANDMARK"
    assert top_hit["cited_by_count"] > 100
    assert "ratio_decidendi" in top_hit


def test_get_citation_graph():
    """Verify citation network DAG reconstruction for landmark judgment."""
    graph = IndianKanoonClient.get_citation_graph("ik-sc-2023-suraj-lamp")
    assert graph["root_judgment"]["id"] == "ik-sc-2023-suraj-lamp"
    assert graph["root_judgment"]["precedent_strength"] == "LANDMARK"
    assert len(graph["nodes"]) >= 3
    assert len(graph["edges"]) >= 2
    assert any(e["relation"] == "CITES" for e in graph["edges"])
    assert any(e["relation"] in ("FOLLOWED", "APPLIED", "CITED") for e in graph["edges"])
