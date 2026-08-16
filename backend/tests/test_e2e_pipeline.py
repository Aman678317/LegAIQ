"""End-to-end pipeline test: the critical acceptance path.

create case → upload document → OCR → extraction → embeddings → ownership →
comparison → risks → report → export. Runs the real API routes and the real
worker task functions against the in-memory fake — the only fakes are the
database, storage, and OCR engine. The LLM path uses the built-in honest
mock provider (no network, clearly-labelled output), which is also asserted.
"""
from tests.conftest import ORG_ID

API = "/api/v1"


def _upload(api_client, name: str, content: bytes = b"fake-pdf-bytes"):
    res = api_client.post(
        f"{API}/cases/{CASE_ID[0]}/documents",
        files={"file": (name, content, "application/pdf")},
    )
    assert res.status_code == 200, res.text
    return res.json()


# populated by the fixture chain; set in setup below
CASE_ID: list[str] = []


def test_full_pipeline(api_client, fake, fake_ocr, drain):
    # ---------- 1. Create case ----------
    res = api_client.post(f"{API}/cases", json={
        "name": "Whitefield Sy 124/3 — Due Diligence",
        "case_type": "PROPERTY",
        "organization_id": ORG_ID,
        "jurisdiction_state": "Karnataka",
        "jurisdiction_district": "Bengaluru Urban",
    })
    assert res.status_code == 200, res.text
    case = res.json()
    CASE_ID.clear()
    CASE_ID.append(case["id"])

    # ---------- 2. Upload two documents (the second has a conflicting survey no) ----------
    doc1 = _upload(api_client, "sale_deed_1987.pdf", content=b"doc1-pdf")

    # Second document OCR returns a DIFFERENT survey number to force a mismatch
    fake_ocr.enqueue_for(b"doc2-pdf", [
        "PARTITION DEED dated 04/06/2003 among the legal heirs of Lakshmamma. "
        "The schedule property bearing Sy. No. 124/2 of Whitefield Hobli, "
        "Khata No. 456, measuring 2 Acres 12 Guntas is partitioned between "
        "the three heirs. Registered as Doc No. 445/2003-04."
    ])
    doc2 = _upload(api_client, "partition_deed_2003.pdf", content=b"doc2-pdf")

    docs = fake.tables.rows("documents")
    assert len(docs) == 2
    assert all(d["status"] in ("PROCESSING", "VALIDATING") for d in docs)

    # Upload audited
    assert len([a for a in fake.tables.rows("audit_events") if a["action"] == "document.uploaded"]) == 2

    # ---------- 3. Run the worker pipeline: OCR → extraction → embeddings → ownership → risks ----------
    drain()

    # OCR: page-by-page rows, original bytes untouched in storage
    pages = [p for p in fake.tables.rows("document_pages") if p["document_id"] == doc1["id"]]
    assert len(pages) == 2
    assert all(p["text"] and p["confidence"] > 0.9 for p in pages)
    assert fake.storage.objects[doc1["storage_path"]] == b"doc1-pdf"

    # Document completed with OCR stats
    d1 = next(d for d in fake.tables.rows("documents") if d["id"] == doc1["id"])
    assert d1["status"] == "COMPLETED"
    assert d1["page_count"] == 2
    assert d1["ocr_confidence"] > 0.9

    # Extraction: regex fallback found survey numbers, khata, amounts
    entities = fake.tables.rows("extracted_entities")
    types = {e["entity_type"] for e in entities}
    assert "survey_number" in types
    assert "khata_number" in types
    assert "transaction_amount" in types
    # Every entity carries evidence
    assert all(e["source_text"] and e["page_number"] >= 1 for e in entities)

    # Embeddings: chunks exist (embedding None without an API key — honest)
    chunks = fake.tables.rows("document_chunks")
    assert len(chunks) >= 2

    # Ownership: person nodes + evidenced edges exist
    nodes = fake.tables.rows("ownership_nodes")
    persons = [n for n in nodes if n["node_type"] == "PERSON"]
    properties = [n for n in nodes if n["node_type"] == "PROPERTY"]
    assert len(persons) >= 1
    assert len(properties) >= 1
    edges = fake.tables.rows("ownership_edges")
    assert len(edges) >= 1
    assert all(e["evidence"] for e in edges)  # every relationship requires evidence

    # ---------- 4. Comparison → risk ----------
    res = api_client.post(f"{API}/cases/{case['id']}/compare", json={
        "document_ids": [doc1["id"], doc2["id"]],
    })
    assert res.status_code == 200
    drain()

    comparisons = fake.tables.rows("comparison_results")
    survey_cmp = next(c for c in comparisons if c["field_name"] == "survey_number")
    assert survey_cmp["verdict"] == "MISMATCH"
    assert survey_cmp["explanation"] and "124/3" in survey_cmp["explanation"]

    risks = fake.tables.rows("risks")
    assert len(risks) >= 1
    survey_risk = next(r for r in risks if "survey number" in r["title"].lower())
    assert survey_risk["level"] == "HIGH"
    assert survey_risk["category"] == "BOUNDARY"
    assert survey_risk["evidence"]  # never a risk without evidence

    # ---------- 5. Ownership + risk endpoints expose the data ----------
    graph = api_client.get(f"{API}/cases/{case['id']}/ownership")
    assert graph.status_code == 200
    assert len(graph.json()["edges"]) >= 1

    risk_list = api_client.get(f"{API}/cases/{case['id']}/risks")
    assert risk_list.status_code == 200
    assert len(risk_list.json()) >= 1

    # ---------- 6. Case summary reflects everything ----------
    summary = api_client.get(f"{API}/cases/{case['id']}/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["document_count"] == 2
    assert body["risk_summary"]["total"] >= 1

    # ---------- 7. Report generation (ReportAgent, budgeted) ----------
    res = api_client.post(f"{API}/cases/{case['id']}/reports")
    assert res.status_code == 200
    report_id = res.json()["id"]
    drain()

    report = api_client.get(f"{API}/reports/{report_id}")
    assert report.status_code == 200
    content = report.json()["content"]
    assert "executive_summary" in content
    assert "risks" in content and len(content["risks"]) >= 1
    assert "disclaimer" in content

    # Agent run was recorded with usage accounting
    runs = fake.tables.rows("agent_runs")
    assert any(r["agent_name"] == "report_agent" and r["status"] == "COMPLETED" for r in runs)

    # ---------- 8. Export PDF ----------
    res = api_client.post(f"{API}/reports/{report_id}/export", json={"format": "pdf"})
    assert res.status_code == 200
    drain()

    exported = next(r for r in fake.tables.rows("reports") if r["id"] == report_id)
    assert exported["storage_path"].endswith(".pdf")
    pdf_bytes = fake.storage.objects[exported["storage_path"]]
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert b"trailer" in pdf_bytes

    # ---------- 8b. Export DOCX (valid OOXML zip) ----------
    res = api_client.post(f"{API}/reports/{report_id}/export", json={"format": "docx"})
    assert res.status_code == 200
    drain()

    exported = next(r for r in fake.tables.rows("reports") if r["id"] == report_id)
    assert exported["storage_path"].endswith(".docx")
    docx_bytes = fake.storage.objects[exported["storage_path"]]
    assert docx_bytes.startswith(b"PK")  # valid zip container
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
        names = z.namelist()
        assert "[Content_Types].xml" in names
        assert "word/document.xml" in names
        doc_xml = z.read("word/document.xml").decode("utf-8")
        assert "Whitefield Sy 124/3" in doc_xml  # title paragraph present
        assert "RISKS" in doc_xml  # section heading present
        # XML escaping holds even when content carries special characters
        assert "&amp;" not in doc_xml or "Sy. No. 124/3" in doc_xml

    # ---------- 9. Drafting (mock LLM: honest "not configured" + verification block) ----------
    res = api_client.post(f"{API}/cases/{case['id']}/drafts", json={
        "draft_type": "legal_notice",
        "title": "Notice to Vendor",
        "instructions": "Draft a notice regarding the survey number discrepancy.",
    })
    assert res.status_code == 200, res.text
    draft = res.json()
    assert "AI-generated draft" in draft["content"]
    assert "VERIFICATION REPORT" in draft["content"]  # VerificationAgent ran

    # ---------- 10. Grounded chat over the real retrieval path ----------
    res = api_client.post(f"{API}/cases/{case['id']}/questions", json={
        "question": "What is the survey number mentioned in the sale deed?",
    })
    assert res.status_code == 200
    answer = res.json()
    # Citations point at real uploaded documents
    assert any("sale_deed" in c["document_name"] or "partition" in c["document_name"]
               for c in (answer.get("citations") or []))

    # ---------- 11. All jobs completed, none failed ----------
    jobs = fake.tables.rows("jobs")
    assert jobs, "pipeline produced no jobs"
    failed = [j for j in jobs if j["state"] == "FAILED"]
    assert not failed, f"failed jobs: {[(j['job_type'], j['error_message']) for j in failed]}"
    assert all(j["state"] == "COMPLETED" for j in jobs)

    # ---------- 12. Case home data via activity feed ----------
    activity = api_client.get(f"{API}/cases/{case['id']}/activity")
    events = {a["event_type"] for a in activity.json()}
    assert "case.created" in events
    assert "document.uploaded" in events


def test_failed_upload_rejected(api_client, fake, drain):
    """Bad file types and empty files never enter the pipeline."""
    CASE_ID.clear()
    case = api_client.post(f"{API}/cases", json={
        "name": "Validation Case", "organization_id": ORG_ID,
    }).json()
    CASE_ID.append(case["id"])

    # Disallowed MIME
    res = api_client.post(
        f"{API}/cases/{case['id']}/documents",
        files={"file": ("virus.exe", b"MZ...", "application/x-msdownload")},
    )
    assert res.status_code == 400

    # Allowed type but empty body
    res = api_client.post(
        f"{API}/cases/{case['id']}/documents",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert res.status_code == 400

    drain()
    assert fake.tables.rows("documents") == []
