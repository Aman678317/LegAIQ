"""Unit tests for pure pipeline logic: chunking and regex extraction."""
from app.workers.tasks import REGEX_PATTERNS, _chunk_text


class TestChunker:
    def test_empty_text_yields_nothing(self):
        assert _chunk_text("") == []
        assert _chunk_text("   \n  ") == []

    def test_short_text_single_chunk(self):
        text = "word " * 50
        chunks = _chunk_text(text)
        assert len(chunks) == 1

    def test_long_text_chunks_with_overlap(self):
        text = "lorem ipsum dolor " * 2000  # ~36k chars
        chunks = _chunk_text(text, chunk_size=200, overlap=30)
        assert len(chunks) > 1
        # every chunk respects content threshold
        assert all(len(c) > 40 for c in chunks)

    def test_chunks_reassemble_coverage(self):
        words = [f"w{i}" for i in range(500)]
        text = " ".join(words)
        chunks = _chunk_text(text, chunk_size=100, overlap=10)
        joined = " ".join(chunks)
        assert "w0 " in joined and " w499" in joined


class TestRegexExtraction:
    def extract(self, text):
        found = []
        import re
        for pattern, etype in REGEX_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                found.append((etype, m.group(1)))
        return dict(found)

    def test_survey_number(self):
        got = self.extract("land bearing Sy. No. 124/3 of Whitefield Hobli")
        assert got.get("survey_number") == "124/3"

    def test_hissa(self):
        got = self.extract("Survey Number 124 Hissa 2 situated at Varthur")
        assert got.get("hissa") == "2"

    def test_khata(self):
        got = self.extract("Khata No. 456 issued by Gram Panchayat")
        assert got.get("khata_number") == "456"

    def test_amount(self):
        got = self.extract("consideration of Rs. 45,000 paid in cash")
        assert got.get("transaction_amount") == "45,000"

    def test_registration_date_indian_format(self):
        got = self.extract("registered on 15/03/1987 before Sub-Registrar")
        assert got.get("registration_date") == "15/03/1987"

    def test_no_false_positive_on_plain_text(self):
        got = self.extract("The parties agree to the terms herein contained.")
        assert got == {}
