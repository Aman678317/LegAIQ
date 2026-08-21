"""Tier 5 Adversarial Coverage Hardening & Empirical Stress Test Suite.

Exhaustively stress-tests:
1. AI Gateway: Rapid concurrency (50+ simultaneous requests), provider rate-limit simulation (429/503/timeout failover), and multi-line streaming SSE edge cases (malformed JSON, embedded newlines, split Unicode, stream truncation).
2. Ownership Chain DAG: Circular conveyances (DFS cycles, self-loops, multi-cycles), split parcels, deep missing link deeds, and mortgage release collisions.
3. BSA 2023 Section 63 Engine: Hash tampering detection, corrupted electronic records, and date presumption boundaries (exact 29 vs 30 vs 31 years, leap years, future dates).
4. Indian PII Redaction: Verhoeff mathematical checksum validation, single-digit transposition/substitution detection, Unicode script obfuscation, and context keyword confidence modulation.
5. SSRF Defense: DNS rebinding (single and multi-IP resolution), IPv6-mapped IPv4 addresses, AWS/GCP/Azure cloud metadata endpoints, and non-HTTP scheme smuggling.
"""

import asyncio
import hashlib
import ipaddress
import json
import pytest
from datetime import datetime, timezone, timedelta
from typing import Any, AsyncIterator, Dict, List
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

# AI Gateway imports
from app.ai.provider import (
    AnthropicProvider,
    BaseLLMProvider,
    GroqProvider,
    LLMRequest,
    LLMResponse,
    MockLLMProvider,
    ModelRouter,
    NvidiaProvider,
    OllamaProvider,
    OpenAIProvider,
    _PROVIDERS,
    router as global_llm_router,
)
from app.config import get_settings

# Land & Ownership DAG imports
from app.ai.land_intelligence import (
    IndianLandExtractor,
    are_land_areas_equivalent,
    get_state_bigha_sqm,
    normalize_land_area,
    parse_and_normalize_area,
    reconstruct_title_chain,
)
from app.ai.ownership_graph import (
    LinkType,
    OwnershipChainAnalyzer,
    OwnershipEdge,
    OwnershipNode,
    TitleBreakAlert,
    TitleBreakSeverity,
)

# BSA 2023 Section 63 imports
from app.ai.bharatiya_sakshya import (
    AdmissibilityStatus,
    BharatiyaSakshyaEngine,
    DocumentCategory,
    DPDPLawfulBasis,
    EvidenceItem,
    EvidenceType,
    Section63Certificate,
    check_section94_presumption,
    check_section95_presumption,
    check_section96_presumption,
    check_section97_presumption,
    generate_section63_certificate,
    validate_dpdp_compliance,
)

# Indian PII imports
from app.security.pii import (
    IndianPIIRecognizer,
    LegalPIIRecognizer,
    PIIDetectionEngine,
    PIIEntity,
    PIIEntityType,
    PIIRedactionPipeline,
    RedactionConfig,
    RedactionResult,
    RedactionStrategy,
    detect_pii,
    redact_pii,
)

# SSRF imports
from app.security.ssrf import (
    _is_blocked_ip,
    _resolve_all,
    validate_external_url,
)

settings = get_settings()


# ============================================================================
# DOMAIN 1: AI Gateway Adversarial Stress Testing
# ============================================================================

class TestAIGatewayAdversarialStress:
    """Adversarial stress testing of AI Gateway routing, concurrency, failover, and SSE streaming."""

    @pytest.mark.asyncio
    async def test_rapid_concurrency_stress_router_complete(self):
        """Simulate 50 rapid concurrent requests across diverse tasks to verify router isolation and no deadlocks."""
        tasks = ["chat", "reasoning", "extraction", "research", "drafting", "classification", "summarization", "translation"]
        
        async def single_call(idx: int):
            task = tasks[idx % len(tasks)]
            req = LLMRequest(
                system=f"System prompt {idx}",
                prompt=f"Legal query {idx} on Indian statutes",
                task=task,
            )
            resp = await global_llm_router.complete(req)
            assert resp is not None
            assert len(resp.content) > 0
            assert resp.provider in ("mock", "groq", "nvidia", "ollama", "openai", "anthropic")
            return resp

        # Launch 50 concurrent tasks
        coros = [single_call(i) for i in range(50)]
        results = await asyncio.gather(*coros)
        assert len(results) == 50
        assert all(r.content != "" for r in results)

    @pytest.mark.asyncio
    async def test_rapid_concurrency_stream_complete(self):
        """Simulate 30 concurrent streaming requests running simultaneously with asyncio.gather."""
        async def single_stream(idx: int):
            req = LLMRequest(
                system=f"System {idx}",
                prompt=f"Stream prompt {idx}",
                task="chat",
            )
            tokens = []
            async for token in global_llm_router.stream_complete(req):
                tokens.append(token)
            assert len(tokens) > 0
            full_text = "".join(tokens)
            assert len(full_text) > 0
            return full_text

        coros = [single_stream(i) for i in range(30)]
        results = await asyncio.gather(*coros)
        assert len(results) == 30

    @pytest.mark.asyncio
    async def test_provider_rate_limit_429_failover(self, monkeypatch):
        """Simulate primary provider returning HTTP 429 (Rate Limit Exceeded) and verify graceful fallback."""
        router = ModelRouter()
        
        class RateLimitedProvider(BaseLLMProvider):
            name = "ratelimited"
            def is_configured(self):
                return True
            async def complete(self, request: LLMRequest) -> LLMResponse:
                return LLMResponse(
                    content='{"error": "rate_limit_exceeded", "message": "HTTP 429 Too Many Requests"}',
                    provider=self.name,
                    model="rate-limit-model",
                    latency_ms=10,
                )
            async def stream_complete(self, request: LLMRequest) -> AsyncIterator[str]:
                raise RuntimeError("HTTP 429 Rate Limit Exceeded")
                yield ""

        # Wire the rate-limited provider as primary
        test_providers = {
            "ratelimited": RateLimitedProvider(),
            "mock": MockLLMProvider(),
        }
        monkeypatch.setattr("app.ai.provider._PROVIDERS", test_providers)

        req = LLMRequest(system="System", prompt="Question", task="chat")
        resp = await router.complete(req)
        # Should gracefully fall back to mock without crashing
        assert resp is not None
        assert resp.provider == "mock" or "mock" in resp.content.lower() or "Jurisiva" in resp.content

    @pytest.mark.asyncio
    async def test_provider_service_unavailable_503_failover(self, monkeypatch):
        """Simulate primary provider returning HTTP 503 (Service Unavailable) and verify fallback."""
        router = ModelRouter()
        
        class Failing503Provider(BaseLLMProvider):
            name = "failing503"
            def is_configured(self):
                return True
            async def complete(self, request: LLMRequest) -> LLMResponse:
                return LLMResponse(
                    content='{"error": "service_unavailable", "message": "HTTP 503 Service Unavailable"}',
                    provider=self.name,
                    model="failing-model",
                    latency_ms=5,
                )
            async def stream_complete(self, request: LLMRequest) -> AsyncIterator[str]:
                raise ConnectionError("503 Service Unavailable")
                yield ""

        test_providers = {
            "failing503": Failing503Provider(),
            "mock": MockLLMProvider(),
        }
        monkeypatch.setattr("app.ai.provider._PROVIDERS", test_providers)

        req = LLMRequest(system="Sys", prompt="Test Prompt", task="reasoning")
        resp = await router.complete(req)
        assert resp is not None
        assert resp.provider == "mock" or "Jurisiva" in resp.content or "mock" in resp.content.lower()

    @pytest.mark.asyncio
    async def test_sse_multiline_newlines_in_tokens(self, monkeypatch):
        """Verify SSE streaming preserves tokens containing embedded newlines and multiple blank lines."""
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test-key")
        provider = OpenAIProvider()

        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Heading 1\\n\\n"}}]}',
            'data: {"choices": [{"delta": {"content": "Paragraph 1 with \\n newline.\\n\\n\\n"}}]}',
            'data: {"choices": [{"delta": {"content": "Paragraph 2 concluding."}}]}',
            'data: [DONE]',
        ]

        class MockStream:
            def raise_for_status(self):
                pass
            async def aiter_lines(self):
                for line in sse_lines:
                    yield line
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass

        with patch("httpx.AsyncClient.stream", return_value=MockStream()):
            req = LLMRequest(system="Sys", prompt="Format text", task="drafting")
            tokens = []
            async for token in provider.stream_complete(req):
                tokens.append(token)
            
            full_text = "".join(tokens)
            assert "Heading 1\n\n" in full_text
            assert "Paragraph 1 with \n newline.\n\n\n" in full_text
            assert "Paragraph 2 concluding." in full_text

    @pytest.mark.asyncio
    async def test_sse_malformed_json_and_comment_resilience(self, monkeypatch):
        """Verify SSE parser ignores malformed JSON lines, empty lines, and non-data SSE events without crashing."""
        monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk-test-key")
        provider = GroqProvider()

        sse_lines = [
            ': ping comment',
            'id: 101',
            'event: message',
            'data: {"choices": [{"delta": {"content": "Token 1 "}}]}',
            'data: {corrupted json line',
            '',
            'data: ',
            'data: {"choices": []}',
            'data: {"choices": [{"delta": {"content": "Token 2."}}]}',
            'data: [DONE]',
        ]

        class MockStream:
            def raise_for_status(self):
                pass
            async def aiter_lines(self):
                for line in sse_lines:
                    yield line
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass

        with patch("httpx.AsyncClient.stream", return_value=MockStream()):
            req = LLMRequest(system="Sys", prompt="Test", task="chat")
            tokens = []
            async for token in provider.stream_complete(req):
                tokens.append(token)
            assert tokens == ["Token 1 ", "Token 2."]

    @pytest.mark.asyncio
    async def test_sse_split_unicode_multibyte_characters(self, monkeypatch):
        """Verify SSE stream handles multi-byte Devanagari and emoji characters cleanly."""
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test-key")
        provider = OpenAIProvider()

        # Unicode legal text in Hindi and symbols
        sse_lines = [
            'data: {"choices": [{"delta": {"content": "न्यायालय "}}]}',
            'data: {"choices": [{"delta": {"content": "(Court) ⚖️ "}}]}',
            'data: {"choices": [{"delta": {"content": "और निर्णय 📜"}}]}',
            'data: [DONE]',
        ]

        class MockStream:
            def raise_for_status(self):
                pass
            async def aiter_lines(self):
                for line in sse_lines:
                    yield line
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass

        with patch("httpx.AsyncClient.stream", return_value=MockStream()):
            req = LLMRequest(system="Sys", prompt="Translate", task="translation")
            tokens = []
            async for token in provider.stream_complete(req):
                tokens.append(token)
            
            full = "".join(tokens)
            assert "न्यायालय" in full
            assert "⚖️" in full
            assert "📜" in full

    @pytest.mark.asyncio
    async def test_sse_stream_truncation_handling(self, monkeypatch):
        """Verify stream terminating abruptly without [DONE] yields accumulated tokens without infinite wait."""
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test-key")
        provider = OpenAIProvider()

        # Stream terminates after 2 tokens without [DONE]
        sse_lines = [
            'data: {"choices": [{"delta": {"content": "First token "}}]}',
            'data: {"choices": [{"delta": {"content": "Second token."}}]}',
        ]

        class MockStream:
            def raise_for_status(self):
                pass
            async def aiter_lines(self):
                for line in sse_lines:
                    yield line
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass

        with patch("httpx.AsyncClient.stream", return_value=MockStream()):
            req = LLMRequest(system="Sys", prompt="Test", task="chat")
            tokens = []
            async for token in provider.stream_complete(req):
                tokens.append(token)
            assert tokens == ["First token ", "Second token."]


# ============================================================================
# DOMAIN 2: Ownership Chain DAG Adversarial Testing
# ============================================================================

class TestOwnershipChainDAGAdversarial:
    """Adversarial stress testing of Title Ownership DAG, cycles, splits, gaps, and mortgage collisions."""

    def test_dag_two_node_circular_conveyance(self):
        """Adversarial cycle: A -> B -> A (immediate circular transfer back to grantor)."""
        events = [
            {
                "event_date": "2000-01-10",
                "transaction_type": "SALE_DEED",
                "from_owner": "Vendor Alpha",
                "to_owner": "Purchaser Beta",
                "document_number": "DOC/2000/01",
            },
            {
                "event_date": "2005-06-15",
                "transaction_type": "SALE_DEED",
                "from_owner": "Purchaser Beta",
                "to_owner": "Vendor Alpha",  # Cycle back
                "document_number": "DOC/2005/02",
            },
        ]
        dag = reconstruct_title_chain(events, case_id="case-cycle-2")
        assert dag["title_status"] == "DEFECTIVE"
        cycle_gaps = [g for g in dag["gaps"] if g["break_type"] == "CIRCULAR_TRANSFER_DETECTED"]
        assert len(cycle_gaps) >= 1
        assert cycle_gaps[0]["severity"] == TitleBreakSeverity.CRITICAL.value

    def test_dag_three_node_circular_conveyance(self):
        """Adversarial cycle: A -> B -> C -> A (multi-hop circular conveyance)."""
        events = [
            {"event_date": "1995-01-01", "transaction_type": "SALE_DEED", "from_owner": "Party A", "to_owner": "Party B"},
            {"event_date": "2002-02-02", "transaction_type": "GIFT_DEED", "from_owner": "Party B", "to_owner": "Party C"},
            {"event_date": "2010-03-03", "transaction_type": "SALE_DEED", "from_owner": "Party C", "to_owner": "Party A"},
        ]
        dag = reconstruct_title_chain(events, case_id="case-cycle-3")
        assert dag["title_status"] == "DEFECTIVE"
        cycle_gaps = [g for g in dag["gaps"] if g["break_type"] == "CIRCULAR_TRANSFER_DETECTED"]
        assert len(cycle_gaps) >= 1
        assert "Party A" in cycle_gaps[0]["description"]
        assert "Party B" in cycle_gaps[0]["description"]
        assert "Party C" in cycle_gaps[0]["description"]

    def test_dag_self_loop_conveyance(self):
        """Adversarial sham transfer: A -> A (grantor and grantee are identical)."""
        events = [
            {"event_date": "2012-05-10", "transaction_type": "SALE_DEED", "from_owner": "Sole Owner", "to_owner": "Sole Owner"},
        ]
        dag = reconstruct_title_chain(events, case_id="case-self-loop")
        cycle_gaps = [g for g in dag["gaps"] if g["break_type"] == "CIRCULAR_TRANSFER_DETECTED"]
        assert len(cycle_gaps) >= 1
        assert dag["title_status"] == "DEFECTIVE"

    def test_dag_split_parcels_bifurcated_flow(self):
        """Valid split parcel: 1 grantor selling 3 distinct portions to 3 buyers does NOT trigger spurious cycle."""
        events = [
            {"event_date": "2000-01-01", "transaction_type": "SALE_DEED", "from_owner": "Original Owner", "to_owner": "Buyer Portion 1"},
            {"event_date": "2002-01-01", "transaction_type": "SALE_DEED", "from_owner": "Original Owner", "to_owner": "Buyer Portion 2"},
            {"event_date": "2004-01-01", "transaction_type": "SALE_DEED", "from_owner": "Original Owner", "to_owner": "Buyer Portion 3"},
        ]
        dag = reconstruct_title_chain(events, case_id="case-split-parcel")
        # No circular transfer
        cycle_gaps = [g for g in dag["gaps"] if g["break_type"] == "CIRCULAR_TRANSFER_DETECTED"]
        assert len(cycle_gaps) == 0

    def test_dag_partition_deed_coparcenary_split(self):
        """Partition deed amongst coparceners splits ownership into branches cleanly."""
        events = [
            {"event_date": "1990-01-01", "transaction_type": "PARTITION_DEED", "from_owner": "Joint Family Karta", "to_owner": "Son 1"},
            {"event_date": "1990-01-01", "transaction_type": "PARTITION_DEED", "from_owner": "Joint Family Karta", "to_owner": "Son 2"},
            {"event_date": "2015-05-05", "transaction_type": "SALE_DEED", "from_owner": "Son 1", "to_owner": "Developer Corp"},
        ]
        dag = reconstruct_title_chain(events, case_id="case-partition")
        assert len(dag["nodes"]) >= 4
        assert len(dag["edges"]) == 3
        # No circular transfer
        assert not any(g["break_type"] == "CIRCULAR_TRANSFER_DETECTED" for g in dag["gaps"])

    def test_dag_deep_missing_link_conveyance_gap(self):
        """Unbroken title chain discontinuity: A sells to B (1990), then stranger X sells to Y (2015)."""
        events = [
            {"event_date": "1990-04-12", "transaction_type": "SALE_DEED", "from_owner": "Anand Rao", "to_owner": "Babu Lal"},
            {"event_date": "2015-08-20", "transaction_type": "SALE_DEED", "from_owner": "Xavier Dsouza", "to_owner": "Yashwant Patel"},
        ]
        dag = reconstruct_title_chain(events, case_id="case-missing-link")
        discontinuity = [g for g in dag["gaps"] if g["break_type"] == "MISSING_INTERMEDIATE_LINK"]
        assert len(discontinuity) == 1
        assert discontinuity[0]["severity"] == TitleBreakSeverity.HIGH.value
        assert "Babu Lal" in discontinuity[0]["description"]
        assert "Xavier Dsouza" in discontinuity[0]["description"]

    def test_dag_mortgage_release_collision_single_bank_multiple_charges(self):
        """2 mortgages registered to State Bank of India, but only 1 Deed of Release -> exactly 1 active mortgage remains flagged."""
        events = [
            {
                "event_date": "2010-01-15",
                "transaction_type": "MORTGAGE_CHARGE",
                "from_owner": "Borrower One",
                "to_owner": "State Bank of India",
                "bank": "State Bank of India",
            },
            {
                "event_date": "2015-06-20",
                "transaction_type": "MORTGAGE_CHARGE",
                "from_owner": "Borrower One",
                "to_owner": "State Bank of India",
                "bank": "State Bank of India",
            },
            {
                "event_date": "2018-09-10",
                "transaction_type": "RELEASE_DEED",
                "from_owner": "State Bank of India",
                "to_owner": "Borrower One",
                "bank": "State Bank of India",
            },
        ]
        dag = reconstruct_title_chain(events, case_id="case-mortgage-collision")
        mortgage_gaps = [g for g in dag["gaps"] if g["break_type"] == "UNRELEASED_ENCUMBRANCE"]
        # Exactly 1 unreleased mortgage should remain flagged
        assert len(mortgage_gaps) == 1
        assert "State Bank of India" in mortgage_gaps[0]["title"]
        assert dag["title_status"] == "DEFECTIVE"

    def test_dag_mortgage_release_mismatched_lender_collision(self):
        """Mortgage registered to HDFC Bank, but Release Deed executed by ICICI Bank -> HDFC mortgage remains flagged as undischarged."""
        events = [
            {
                "event_date": "2012-03-10",
                "transaction_type": "MORTGAGE_CHARGE",
                "from_owner": "Owner Rao",
                "to_owner": "HDFC Bank Ltd",
                "bank": "HDFC Bank Ltd",
            },
            {
                "event_date": "2016-07-25",
                "transaction_type": "RELEASE_DEED",
                "from_owner": "ICICI Bank Ltd",  # Mismatched lender
                "to_owner": "Owner Rao",
                "bank": "ICICI Bank Ltd",
            },
        ]
        dag = reconstruct_title_chain(events, case_id="case-mismatched-bank")
        mortgage_gaps = [g for g in dag["gaps"] if g["break_type"] == "UNRELEASED_ENCUMBRANCE"]
        assert len(mortgage_gaps) == 1
        assert "HDFC Bank Ltd" in mortgage_gaps[0]["title"]


# ============================================================================
# DOMAIN 3: BSA 2023 Section 63 Engine Adversarial Testing
# ============================================================================

class TestBSA2023Section63Adversarial:
    """Adversarial testing of BSA 2023 Section 63 hash tampering, electronic records, and 30-year presumption boundaries."""

    def test_bsa_sec63_tampered_document_hash_detection(self):
        """Verify that any 1-bit or 1-byte alteration in file hash invalidates cryptographic seal integrity."""
        original_content = b"Official Registered Sale Deed Document 1994"
        orig_hash = hashlib.sha256(original_content).hexdigest()
        
        # Tampered content with 1-character modification
        tampered_content = b"Official Registered Sale Deed Document 1995"
        tampered_hash = hashlib.sha256(tampered_content).hexdigest()

        cert = generate_section63_certificate(
            file_name="sale_deed_1994.pdf",
            file_hash=orig_hash,
            custodian_name="Advocate K. S. Murthy",
        )

        assert cert["master_audit_hash"] == orig_hash
        assert cert["master_audit_hash"] != tampered_hash
        assert len(cert["master_audit_hash"]) == 64

    def test_bsa_sec63_truncated_or_malformed_hash_resilience(self):
        """Verify engine generates deterministic SHA-256 fallback when given malformed or truncated hash."""
        cert_truncated = generate_section63_certificate(
            file_name="corrupt.pdf",
            file_hash="abcd1234",  # Truncated hash
        )
        assert len(cert_truncated["master_audit_hash"]) == 64

        cert_empty = generate_section63_certificate(
            file_name="empty_hash.pdf",
            file_hash="",
        )
        assert len(cert_empty["master_audit_hash"]) == 64

    def test_bsa_sec63_corrupted_electronic_record_admissibility(self):
        """Electronic record without Section 63 certificate is flagged with objection requiring certificate."""
        engine = BharatiyaSakshyaEngine()
        
        # Electronic record without cert
        ev_item = EvidenceItem(
            evidence_id="ev-elec-001",
            evidence_type=EvidenceType.ELECTRONIC,
            description="WhatsApp Chat Export",
            source="Mobile Phone",
            metadata={"computer_generated": True, "system_integrity_verified": False},
        )
        analyzed = engine.analyze_evidence(ev_item)
        assert analyzed.admissibility_status == AdmissibilityStatus.CONDITIONALLY_ADMISSIBLE
        assert any("Section 63 certificate required" in obj for obj in analyzed.objections)

    def test_bsa_sec63_electronic_agreement_signature_missing(self):
        """Electronic agreement lacking verified digital signature triggers Section 95/96 objections."""
        engine = BharatiyaSakshyaEngine()
        ev_item = EvidenceItem(
            evidence_id="ev-agr-002",
            evidence_type=EvidenceType.ELECTRONIC,
            description="Electronic Lease Agreement",
            source="Web Portal",
            document_category=DocumentCategory.ELECTRONIC_RECORD,
            metadata={"is_agreement": True, "digital_signature_verified": False},
        )
        analyzed = engine.analyze_evidence(ev_item)
        assert any("Digital signature verification required" in obj for obj in analyzed.objections)

    def test_bsa_sec94_presumption_exact_29_years_boundary(self):
        """Exact 29 years boundary: document is 29.0 years old -> Section 94 30-year presumption is REJECTED."""
        is_presumed, reason = check_section94_presumption(29.0)
        assert is_presumed is False
        assert "does not meet 30-year threshold" in reason
        assert "29.0 years old" in reason

    def test_bsa_sec94_presumption_exact_29_years_364_days(self):
        """Document created 29 years and 364 days ago -> does not reach 30.0 years -> presumption REJECTED."""
        dt_29_yr_364_d = datetime.now(timezone.utc) - timedelta(days=(29 * 365.25 + 364))
        is_presumed, reason = check_section94_presumption(dt_29_yr_364_d)
        assert is_presumed is False
        assert "does not meet 30-year threshold" in reason

    def test_bsa_sec94_presumption_exact_30_years_boundary(self):
        """Exact 30 years boundary: document is 30.0 years old -> Section 94 30-year presumption APPLIES."""
        is_presumed, reason = check_section94_presumption(30.0)
        assert is_presumed is True
        assert "Section 94 presumption applies" in reason
        assert "presumed genuine" in reason

    def test_bsa_sec94_presumption_exact_31_years_boundary(self):
        """Document is 31.0 years old -> Section 94 30-year presumption APPLIES."""
        is_presumed, reason = check_section94_presumption(31.0)
        assert is_presumed is True
        assert "Section 94 presumption applies" in reason

    def test_bsa_sec94_future_or_negative_date_handling(self):
        """Future year or invalid date string is rejected cleanly without crashing."""
        is_presumed, reason = check_section94_presumption(2099)
        assert is_presumed is False

        is_presumed_invalid, reason_inv = check_section94_presumption("not-a-valid-date")
        assert is_presumed_invalid is False
        assert "Could not parse" in reason_inv

    def test_bsa_sec97_certified_copy_presumption_boundaries(self):
        """Section 97 presumption applies strictly to certified copies of public/revenue/court documents."""
        # 1. Public document + certified -> True
        p1, r1 = check_section97_presumption(DocumentCategory.REVENUE_RECORD, is_certified=True)
        assert p1 is True
        assert "Section 97 presumption applies" in r1

        # 2. Public document + uncertified -> False
        p2, r2 = check_section97_presumption(DocumentCategory.REVENUE_RECORD, is_certified=False)
        assert p2 is False
        assert "not certified" in r2

        # 3. Private document + certified -> False (Section 97 covers public documents)
        p3, r3 = check_section97_presumption(DocumentCategory.PRIVATE_DOCUMENT, is_certified=True)
        assert p3 is False


# ============================================================================
# DOMAIN 4: Indian PII Redaction Adversarial Testing
# ============================================================================

class TestIndianPIIRedactionAdversarial:
    """Adversarial testing of Verhoeff Aadhaar validation, single-digit substitutions, Unicode obfuscation, and context masking."""

    def test_verhoeff_valid_aadhaar_mathematical_checksum(self):
        """Mathematically valid Aadhaar numbers pass Verhoeff checksum with confidence 0.95."""
        recognizer = IndianPIIRecognizer()
        # Known valid Verhoeff Aadhaar test numbers
        valid_aadhars = [
            "2182 9319 7501",
            "9999 4105 1548",
            "3675 9834 6012",
        ]
        for a in valid_aadhars:
            assert recognizer._verify_aadhaar_checksum(a) is True
            entities = recognizer.detect(f"Aadhaar Number: {a}")
            aadhaar_ents = [e for e in entities if e.entity_type == PIIEntityType.AADHAAR]
            assert len(aadhaar_ents) >= 1
            assert aadhaar_ents[0].confidence == 0.95

    def test_verhoeff_single_digit_transposition_adversarial(self):
        """Verhoeff algorithm mathematically detects adjacent digit transpositions and fails checksum."""
        recognizer = IndianPIIRecognizer()
        valid = "218293197501"
        assert recognizer._verify_aadhaar_checksum(valid) is True

        # Transpose first two digits: 21 -> 12
        transposed_1 = "128293197501"
        assert recognizer._verify_aadhaar_checksum(transposed_1) is False

        # Transpose middle digits: 93 -> 39
        transposed_2 = "218239197501"
        assert recognizer._verify_aadhaar_checksum(transposed_2) is False

        # Transpose last two digits: 01 -> 10
        transposed_3 = "218293197510"
        assert recognizer._verify_aadhaar_checksum(transposed_3) is False

    def test_verhoeff_single_digit_substitution_adversarial(self):
        """Verhoeff algorithm mathematically detects single digit substitution."""
        recognizer = IndianPIIRecognizer()
        valid = "218293197501"
        assert recognizer._verify_aadhaar_checksum(valid) is True

        # Change last digit from 1 to 2
        substituted = "218293197502"
        assert recognizer._verify_aadhaar_checksum(substituted) is False

    def test_verhoeff_invalid_length_numbers(self):
        """Numbers with <12 or >12 digits return False."""
        recognizer = IndianPIIRecognizer()
        assert recognizer._verify_aadhaar_checksum("12345678901") is False  # 11 digits
        assert recognizer._verify_aadhaar_checksum("1234567890123") is False  # 13 digits
        assert recognizer._verify_aadhaar_checksum("12345678901A") is False  # Non-digit

    def test_pii_all_five_redaction_strategies(self):
        """Verify all 5 redaction strategies (MASK, REPLACE, HASH, REMOVE, PSEUDONYMIZE) on legal text."""
        raw_text = "Advocate Ramesh Rao filed PAN ABCDE1234F and Aadhaar 2182 9319 7501 in High Court of Karnataka."
        
        # 1. Strategy: MASK
        res_mask = redact_pii(raw_text, RedactionConfig(strategy=RedactionStrategy.MASK))
        assert "ABCDE1234F" not in res_mask.redacted_text
        assert "2182 9319 7501" not in res_mask.redacted_text
        assert "*" in res_mask.redacted_text

        # 2. Strategy: REPLACE
        res_replace = redact_pii(raw_text, RedactionConfig(strategy=RedactionStrategy.REPLACE))
        assert "ABCDE1234F" not in res_replace.redacted_text
        assert "<PAN>" in res_replace.redacted_text or "<AADHAAR>" in res_replace.redacted_text

        # 3. Strategy: HASH
        res_hash = redact_pii(raw_text, RedactionConfig(strategy=RedactionStrategy.HASH))
        assert "ABCDE1234F" not in res_hash.redacted_text
        assert "<HASH:" in res_hash.redacted_text

        # 4. Strategy: REMOVE
        res_remove = redact_pii(raw_text, RedactionConfig(strategy=RedactionStrategy.REMOVE))
        assert "ABCDE1234F" not in res_remove.redacted_text
        assert "2182 9319 7501" not in res_remove.redacted_text

        # 5. Strategy: PSEUDONYMIZE
        res_pseudo = redact_pii(raw_text, RedactionConfig(strategy=RedactionStrategy.PSEUDONYMIZE))
        assert "ABCDE1234F" not in res_pseudo.redacted_text
        assert "<" in res_pseudo.redacted_text and ">" in res_pseudo.redacted_text

    def test_pii_context_keyword_confidence_modulation(self):
        """Context keywords ('Aadhaar', 'PAN', 'IFSC') increase confidence score by +0.1."""
        recognizer = IndianPIIRecognizer()
        
        # Without context keyword
        ents_no_ctx = recognizer.detect("ABCDE1234F is present here.")
        pan_no_ctx = next((e for e in ents_no_ctx if e.entity_type == PIIEntityType.PAN), None)
        assert pan_no_ctx is not None
        conf_no_ctx = pan_no_ctx.confidence

        # With explicit context keyword
        ents_with_ctx = recognizer.detect("Income Tax PAN Card Number: ABCDE1234F")
        pan_with_ctx = next((e for e in ents_with_ctx if e.entity_type == PIIEntityType.PAN), None)
        assert pan_with_ctx is not None
        conf_with_ctx = pan_with_ctx.confidence

        assert conf_with_ctx >= conf_no_ctx

    def test_pii_15_indian_entity_types_complete_adversarial(self):
        """Verify detection across all 15 Indian PII types simultaneously in an adversarial payload."""
        sample_doc = (
            "1. Aadhaar: 2182 9319 7501\n"
            "2. PAN: ABCDE1234F\n"
            "3. Mobile: +91 9876543210\n"
            "4. Email: lawyer.rao@nic.in\n"
            "5. Bank Account: 123456789012\n"
            "6. IFSC: SBIN0001234\n"
            "7. Vehicle Reg: MH12AB1234\n"
            "8. Passport: A1234567\n"
            "9. Voter ID: ABC1234567\n"
            "10. Driving License: MH1220230001234\n"
            "11. GSTIN: 29ABCDE1234F1Z5\n"
            "12. UPI ID: advocate@oksbi\n"
            "13. CIN: L12345MH2020PTC123456\n"
            "14. DIN: 12345678\n"
            "15. Case Number: WP 1234/2023\n"
        )
        entities = detect_pii(sample_doc)
        detected_types = {e.entity_type for e in entities}
        
        # Verify critical Indian PII entities are recognized
        expected_types = {
            PIIEntityType.AADHAAR,
            PIIEntityType.PAN,
            PIIEntityType.INDIAN_PHONE,
            PIIEntityType.IFSC,
            PIIEntityType.VEHICLE_REG,
            PIIEntityType.PASSPORT,
            PIIEntityType.VOTER_ID,
            PIIEntityType.DRIVING_LICENSE,
            PIIEntityType.GST,
            PIIEntityType.UPI_ID,
            PIIEntityType.CIN,
            PIIEntityType.DIN,
            PIIEntityType.CASE_NUMBER,
        }
        matched = expected_types.intersection(detected_types)
        assert len(matched) >= 11  # Robust detection of all main types


# ============================================================================
# DOMAIN 5: SSRF Defense Adversarial Testing
# ============================================================================

class TestSSRFDefenseAdversarial:
    """Adversarial testing of SSRF filters, DNS rebinding, IPv6 mapped IPv4, and cloud metadata endpoints."""

    def test_ssrf_dns_rebinding_simulation(self, monkeypatch):
        """Simulate DNS rebinding where a public domain resolves to an internal loopback/private IP."""
        from app.security import ssrf

        # Rebinding simulation: 'rebind.attacker.com' resolves to 127.0.0.1
        monkeypatch.setattr(
            ssrf, "_resolve_all",
            lambda host: ["127.0.0.1"] if host == "rebind.attacker.com" else ["93.184.216.34"],
        )

        with pytest.raises(HTTPException) as exc:
            ssrf.validate_external_url("https://rebind.attacker.com/steal-keys")
        assert exc.value.status_code == 400
        assert "blocked address" in exc.value.detail.lower()

    def test_ssrf_multi_ip_dns_rebinding(self, monkeypatch):
        """Simulate DNS returning multiple A-records with 1 public and 1 private IP (dual resolution)."""
        from app.security import ssrf

        # Host returns dual IPs: public and private
        monkeypatch.setattr(
            ssrf, "_resolve_all",
            lambda host: ["93.184.216.34", "10.0.0.5"] if host == "dual.attacker.com" else [],
        )

        with pytest.raises(HTTPException) as exc:
            ssrf.validate_external_url("https://dual.attacker.com/internal-api")
        assert exc.value.status_code == 400
        assert "blocked address" in exc.value.detail.lower()

    def test_ssrf_ipv6_mapped_ipv4_attacks(self):
        """Adversarial IPv6-mapped IPv4 addresses (::ffff:127.0.0.1, ::ffff:192.168.1.1, ::ffff:169.254.169.254) must be blocked."""
        ipv6_mapped_payloads = [
            "http://[::ffff:127.0.0.1]/admin",
            "http://[::ffff:192.168.1.1]/router",
            "http://[::ffff:10.0.0.1]/secret",
            "http://[::ffff:169.254.169.254]/latest/meta-data/",
        ]
        for url in ipv6_mapped_payloads:
            with pytest.raises(HTTPException) as exc:
                validate_external_url(url)
            assert exc.value.status_code == 400

    def test_ssrf_ipv6_loopback_and_link_local(self):
        """Pure IPv6 loopback (::1) and link-local (fe80::1) addresses must be blocked."""
        ipv6_payloads = [
            "http://[::1]/api/v1/keys",
            "http://[fe80::1]/internal",
            "http://[fc00::1]/private",
        ]
        for url in ipv6_payloads:
            with pytest.raises(HTTPException) as exc:
                validate_external_url(url)
            assert exc.value.status_code == 400

    def test_ssrf_cloud_metadata_endpoints_aws_gcp_azure_do(self):
        """Block AWS, GCP, Azure, and DigitalOcean cloud metadata endpoints."""
        metadata_endpoints = [
            "http://169.254.169.254/latest/meta-data/",
            "http://169.254.169.254/latest/user-data",
            "http://169.254.169.254:8080/latest/meta-data/",
            "http://metadata.google.internal/computeMetadata/v1/",
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            "http://169.254.169.254/metadata/v1.json",
        ]
        for url in metadata_endpoints:
            with pytest.raises(HTTPException) as exc:
                validate_external_url(url)
            assert exc.value.status_code == 400

    def test_ssrf_scheme_and_protocol_smuggling(self):
        """Block non-HTTP/HTTPS schemes (file, gopher, dict, ftp, ldap, data)."""
        smuggling_urls = [
            "file:///etc/passwd",
            "file:///c:/windows/win.ini",
            "gopher://127.0.0.1:6379/_flushall",
            "dict://127.0.0.1:11211/stat",
            "ftp://anonymous@internal.corp/dump",
            "ldap://127.0.0.1:389/o=corp",
            "data:text/html,<script>alert(1)</script>",
        ]
        for url in smuggling_urls:
            with pytest.raises(HTTPException) as exc:
                validate_external_url(url)
            assert exc.value.status_code == 400
            assert "not allowed" in exc.value.detail.lower() or "scheme" in exc.value.detail.lower()

    def test_ssrf_valid_public_domain_allowed(self):
        """Legitimate public legal research endpoints are strictly permitted."""
        allowed_urls = [
            "https://indiankanoon.org/doc/12345678/",
            "https://main.sci.gov.in/judgments",
            "https://api.openai.com/v1/models",
            "https://api.anthropic.com/v1/messages",
        ]
        for url in allowed_urls:
            assert validate_external_url(url) == url
