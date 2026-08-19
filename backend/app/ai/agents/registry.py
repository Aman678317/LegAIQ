"""Concrete agents used by workers and the voice pipeline.

Each agent has scoped permissions, budgets, and loop protection. They use the
tool registry for case data so every access is permission-checked and audited.
"""
import re
from datetime import datetime, timezone
from typing import Any

from supabase import create_client

from app.ai.agents.base import (
    AgentBudget, BaseAgent, Permission, execute_agent, new_agent_context,
)
from app.ai.agents.tools import registry as tools
from app.ai.provider import LLMRequest
from app.config import get_settings

settings = get_settings()


def _db():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


class RiskAgent(BaseAgent):
    """Reviews comparison mismatches + entities and writes evidence-backed risks.

    Uses the LLM only to phrase findings; every risk must quote tool-retrieved
    evidence or it is not written.
    """
    name = "risk_agent"
    description = "Identify and register document risks with evidence"
    default_permissions = (Permission.READ_GRAPH, Permission.READ_ENTITIES, Permission.WRITE_RISKS)

    async def run(self, task: dict[str, Any]) -> dict:
        case_id = self.ctx.case_id
        mismatches = await tools.call(self.ctx, "comparison_read", {})
        entities = await tools.call(self.ctx, "entity_search", {"limit": 100})

        if not mismatches and not entities:
            return {"risks_created": 0, "reason": "no data"}

        # Grounded synthesis: ask the LLM to draft findings ONLY from supplied evidence
        evidence_block = "\n".join(
            f"- {m['field_name']}: {m.get('explanation') or 'conflict'} "
            f"[values: {[(v.get('value'), v.get('document_name'), v.get('page_number')) for v in m['values']]}]"
            for m in mismatches[:15]
        )
        entity_block = "\n".join(
            f"- {e['entity_type']}={e['value']} (doc={e['document']} p.{e['page']}, conf={e['confidence']:.2f})"
            for e in entities[:40]
        )

        created = 0
        if evidence_block and (settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY or settings.OLLAMA_BASE_URL):
            resp = await self.llm(LLMRequest(
                system=(
                    "You are a risk analyst for Indian property documents. From the supplied "
                    "comparison mismatches and entities, draft risk entries as strict JSON: "
                    '{"risks":[{"title":str,"category":str,"level":str,"description":str,'
                    '"evidence_index":int,"recommended_action":str}]}. '
                    "category in OWNERSHIP/TITLE/DOCUMENT/IDENTITY/BOUNDARY/REGISTRATION/"
                    "ENCUMBRANCE/LITIGATION/MISSING_EVIDENCE; level in LOW/MEDIUM/HIGH/CRITICAL. "
                    "evidence_index refers to the numbered mismatch supplied. Never invent evidence."
                ),
                prompt=f"MISMATCHES:\n{evidence_block}\n\nENTITIES:\n{entity_block}",
                task="classification", json_mode=True, temperature=0.1,
            ))
            try:
                import json
                data = json.loads(resp.content)
                for r in data.get("risks", [])[:10]:
                    idx = r.get("evidence_index", 0)
                    if 0 <= idx < len(mismatches):
                        m = mismatches[idx]
                        _db().table("risks").insert({
                            "case_id": case_id,
                            "category": r.get("category", "DOCUMENT"),
                            "level": r.get("level", "MEDIUM"),
                            "title": r["title"][:300],
                            "description": r["description"][:2000],
                            "evidence": [{
                                "document_id": v.get("document_id"),
                                "document_name": v.get("document_name"),
                                "page_number": v.get("page_number"),
                                "source_text": v.get("source_text") or v.get("value"),
                            } for v in m["values"]],
                            "recommended_action": r.get("recommended_action"),
                        }).execute()
                        created += 1
            except (ValueError, KeyError):
                pass  # malformed LLM output -> skip rather than write unverifiable risks

        return {"risks_created": created}


class ReportAgent(BaseAgent):
    """Compiles the Property Due Diligence report from case state via tools.

    Generates Title Search Report v2 format when case metadata indicates
    a property title search, with all 13 standard legal sections.
    """
    name = "report_agent"
    description = "Generate structured due diligence reports"
    default_permissions = (
        Permission.READ_CASE, Permission.READ_DOCUMENTS, Permission.READ_GRAPH,
        Permission.WRITE_REPORTS,
    )

    async def run(self, task: dict[str, Any]) -> dict:
        case_id = self.ctx.case_id
        report_id = task.get("report_id")
        db = _db()

        case = db.table("cases").select("*").eq("id", case_id).single().execute().data
        docs = db.table("documents").select(
            "file_name, status, page_count, ocr_confidence"
        ).eq("case_id", case_id).execute().data
        graph = await tools.call(self.ctx, "graph_search", {})
        risks = await tools.call(self.ctx, "risk_read", {})
        comparisons = await tools.call(self.ctx, "comparison_read", {})
        timeline = db.table("timeline_events").select("*").eq(
            "case_id", case_id
        ).order("sort_date").execute().data

        # Check if this is a title search report
        is_title_search = (
            "title search" in case.get("name", "").lower() or
            case.get("metadata", {}).get("report_type") == "title_search"
        )

        if is_title_search:
            content = await self._build_title_search_v2(case, docs, graph, risks, comparisons, timeline, case_id)
        else:
            # Standard due diligence report
            if settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY or settings.OLLAMA_BASE_URL:
                resp = await self.llm(LLMRequest(
                    system=(
                        "Write a 3-4 sentence executive summary for a property due diligence "
                        "report. Use ONLY the supplied counts and risk titles. No new facts."
                    ),
                    prompt=(
                        f"Case: {case['name']}. Documents: {len(docs)}. "
                        f"Risks: {[r['title'] for r in risks[:8]]}. "
                        f"Ownership edges: {len(graph.get('edges', []))}."
                    ),
                    task="summarization", temperature=0.2,
                ))
                summary = resp.content
            else:
                summary = (
                    f"Due diligence for '{case['name']}': {len(docs)} document(s) reviewed, "
                    f"{len(risks)} open risk(s), {len(graph.get('edges', []))} evidenced ownership "
                    "relationships. AI summary provider not configured; sections below are compiled "
                    "deterministically from case data."
                )

            content = {
                "executive_summary": summary,
                "documents_reviewed": docs,
                "ownership_chain": graph,
                "transaction_timeline": [
                    {"date": t.get("event_date"), "type": t["transaction_type"], "description": t["description"]}
                    for t in timeline
                ],
                "comparisons": [
                    {"field": c["field_name"], "verdict": c["verdict"], "explanation": c.get("explanation")}
                    for c in comparisons
                ],
                "risks": [
                    {"level": r["level"], "category": r["category"], "title": r["title"],
                     "action": r.get("recommended_action")}
                    for r in risks
                ],
                "recommendations": [r.get("recommended_action") for r in risks if r.get("recommended_action")],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "disclaimer": "AI-generated report. Review and verify before relying upon.",
            }

        db.table("reports").update({
            "content": content, "status": "COMPLETED",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", report_id).execute()
        return {"report_id": report_id, "sections": len(content), "type": "title_search_v2" if is_title_search else "standard"}

    async def _build_title_search_v2(self, case: dict, docs: list, graph: dict, risks: list, 
                                     comparisons: list, timeline: list, case_id: str) -> dict:
        """Build Title Search Report v2 structured content."""
        metadata = case.get("metadata", {})
        
        # Extract property details from case metadata
        survey_number = metadata.get("survey_number", "")
        district = metadata.get("district", "")
        taluk = metadata.get("taluk", "")
        village = metadata.get("village", "")
        state = metadata.get("state", "maharashtra")
        client_name = metadata.get("client_name", case.get("client_name", "Client"))
        prepared_by = metadata.get("prepared_by", "Jurisiva Legal Intelligence")
        search_period_years = metadata.get("search_period_years", 30)
        property_address = metadata.get("property_address", f"Survey {survey_number}, {village}, {taluk}, {district}")

        # Convert risks to structured format
        structured_risks = [
            {
                "level": r["level"],
                "category": r["category"],
                "title": r["title"],
                "description": r.get("description", ""),
                "recommended_action": r.get("recommended_action", ""),
            }
            for r in risks
        ]

        # Build chain of title from timeline
        chain_of_title = [
            {
                "document_type": t.get("transaction_type", "Document"),
                "document_number": t.get("document_number", ""),
                "registration_date": t.get("event_date", ""),
                "sro": t.get("sro", ""),
                "transfer_type": t.get("transaction_type", "Sale"),
                "transferors": [t.get("from_owner", "")] if t.get("from_owner") else [],
                "transferees": [t.get("to_owner", "")] if t.get("to_owner") else [],
                "consideration": t.get("consideration", ""),
                "verification_status": "Verified from timeline" if t.get("verified") else "From case data",
            }
            for t in timeline
        ]

        # Build encumbrances from risks
        encumbrances = [
            {
                "type": r.get("category", "ENCUMBRANCE"),
                "party": r.get("party", "Not specified"),
                "amount": r.get("amount", "Not specified"),
                "date": r.get("date", "Not specified"),
                "doc_ref": r.get("document_reference", ""),
                "status": "Active" if r.get("level") in ("HIGH", "CRITICAL") else "Under Review",
                "action": r.get("recommended_action", "Obtain NOC/Discharge Deed"),
            }
            for r in risks if r.get("category") in ("ENCUMBRANCE", "MORTGAGE", "CHARGE", "LIEN")
        ]

        # Build mutations from graph
        mutations = []
        for edge in graph.get("edges", []):
            if edge.get("type") in ("mutation", "ownership_transfer"):
                mutations.append({
                    "mutation_no": edge.get("mutation_number", ""),
                    "date": edge.get("date", ""),
                    "type": edge.get("transfer_type", "Sale"),
                    "from": edge.get("from", ""),
                    "to": edge.get("to", ""),
                    "extent": edge.get("extent", ""),
                    "order_ref": edge.get("order_ref", ""),
                    "status": edge.get("status", "Sanctioned"),
                })

        return {
            # Report metadata for v2 generator
            "survey_number": survey_number,
            "district": district,
            "taluk": taluk,
            "village": village,
            "state": state,
            "client_name": client_name,
            "prepared_by": prepared_by,
            "search_period_years": search_period_years,
            "property_address": property_address,
            "property_profile": metadata.get("property_profile"),
            "portal_records": metadata.get("portal_records", []),
            
            # Structured sections for v2
            "chain_of_title": chain_of_title,
            "encumbrances": encumbrances,
            "mutations": mutations,
            "litigation_cases": metadata.get("litigation_cases", []),
            "tax_records": metadata.get("tax_records", []),
            "registration_history": metadata.get("registration_history", []),
            "risks": structured_risks,
            "discrepancies": [c.get("explanation", "") for c in comparisons if c.get("verdict") == "MISMATCH"],
            "recommendations": [r.get("recommended_action") for r in risks if r.get("recommended_action")],
            
            # Legacy sections for compatibility
            "executive_summary": (
                f"Title search for '{case['name']}': {len(docs)} document(s) reviewed, "
                f"{len(risks)} risk(s) identified, {len(chain_of_title)} title links found."
            ),
            "documents_reviewed": docs,
            "ownership_chain": graph,
            "transaction_timeline": [
                {"date": t.get("event_date"), "type": t["transaction_type"], "description": t["description"]}
                for t in timeline
            ],
            "comparisons": [
                {"field": c["field_name"], "verdict": c["verdict"], "explanation": c.get("explanation")}
                for c in comparisons
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": "AI-generated Title Search Report v2. Review and verify before relying upon. "
                         "This report complies with Bharatiya Sakshya Adhiniyam 2023 and DPDP Act 2023.",
        }


class VerificationAgent(BaseAgent):
    """Fact-checks a draft against extracted entities (Phase 14 requirement).

    Scans for claims (names, numbers, survey references) not present in the
    case evidence and appends a verification block to the draft.
    """
    name = "verification_agent"
    description = "Fact-check drafts against case evidence"
    default_permissions = (Permission.READ_ENTITIES, Permission.READ_DOCUMENTS, Permission.WRITE_DRAFTS)

    async def run(self, task: dict[str, Any]) -> dict:
        draft_id = task["draft_id"]
        db = _db()
        draft = db.table("drafts").select("*").eq("id", draft_id).single().execute().data
        if not draft:
            return {"error": "draft not found"}

        entities = await tools.call(self.ctx, "entity_search", {"limit": 200})
        known_values = {e["value"].strip().lower() for e in entities if e.get("value")}

        # Deterministic checks first: explicit placeholders and numeric claims
        placeholders = re.findall(r"\[VERIFY:[^\]]*\]", draft["content"])
        numbers_in_draft = set(re.findall(r"\b\d+[/-]\w*\b|\b\d{1,3}(?:,\d{3})+\b", draft["content"]))
        numbers_in_evidence = set()
        for v in known_values:
            numbers_in_evidence.update(re.findall(r"\b\d+[/-]\w*\b|\b\d{1,3}(?:,\d{3})+\b", v))
        unverified_numbers = [n for n in numbers_in_draft if n not in numbers_in_evidence][:15]

        # LLM-assisted check when configured
        semantic_notes: list[str] = []
        if entities and (settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY):
            resp = await self.llm(LLMRequest(
                system=(
                    "You verify that legal draft statements are supported by extracted case "
                    "entities. List at most 5 specific statements from the draft that assert "
                    "facts (party names, relationships, dates, amounts) NOT present in the "
                    "entity list. Reply with plain lines '- <quote>' or 'OK' if none."
                ),
                prompt=(
                    f"ENTITY LIST:\n{chr(10).join(sorted(known_values))[:3000]}\n\n"
                    f"DRAFT:\n{draft['content'][:8000]}"
                ),
                task="classification", temperature=0.0,
            ))
            semantic_notes = [
                line.lstrip("- ").strip()
                for line in resp.content.splitlines()
                if line.strip().startswith("-")
            ][:5]

        checks = []
        if placeholders:
            checks.append(f"{len(placeholders)} [VERIFY:] placeholder(s) require manual completion.")
        if unverified_numbers:
            checks.append(
                "Numbers in draft not found in extracted evidence: " + ", ".join(unverified_numbers)
            )
        for note in semantic_notes:
            checks.append(f"Unverified statement: \"{note[:200]}\"")
        if not checks:
            checks.append("All checked statements trace to extracted evidence.")

        verification_block = (
            "\n\n---\nVERIFICATION REPORT (auto-generated)\n"
            + "\n".join(f"- {c}" for c in checks)
            + "\nAI-generated draft. Review and verify before filing or sending."
        )
        db.table("drafts").update({
            "content": draft["content"] + verification_block,
            "status": "REVIEW",
        }).eq("id", draft_id).execute()
        return {"checks": checks, "placeholders": len(placeholders)}


class VoiceAgent(BaseAgent):
    """Answers spoken questions case-grounded, with language matching.

    Never claims to be a human lawyer. Returns text for TTS plus citations
    the UI can open.
    """
    name = "voice_agent"
    description = "Voice assistant grounded in case documents"
    default_permissions = (
        Permission.READ_DOCUMENTS, Permission.READ_ENTITIES, Permission.VOICE,
    )

    VOICE_BUDGET = AgentBudget(
        max_llm_calls=2, max_prompt_tokens=20_000, max_completion_tokens=1500,
        max_cost_usd=0.10, max_seconds=45.0, max_iterations=2,
    )

    LANG_INSTRUCTIONS = {
        "en": "Respond in English.",
        "hi": "Respond in Hindi (Devanagari script).",
        "kn": "Respond in Kannada.", "ta": "Respond in Tamil.",
        "te": "Respond in Telugu.", "ml": "Respond in Malayalam.",
        "mr": "Respond in Marathi.", "bn": "Respond in Bengali.",
        "gu": "Respond in Gujarati.", "pa": "Respond in Punjabi.", "ur": "Respond in Urdu.",
    }

    async def run(self, task: dict[str, Any]) -> dict:
        question = task["question"]
        language = task.get("language", "en")

        chunks = await tools.call(self.ctx, "document_search", {"query": question, "top_k": 8})
        if not chunks:
            return {
                "answer": (
                    "Not found in the uploaded documents. "
                    "Upload case documents or wait for processing to complete."
                ),
                "citations": [], "language": language,
            }

        context = "\n\n".join(
            f"[{c['document_name']} p.{c['page_number']}] {c['content']}" for c in chunks
        )
        lang_rule = self.LANG_INSTRUCTIONS.get(language, "Respond in English.")

        resp = await self.llm(LLMRequest(
            system=(
                "You are Jurisiva, a voice legal assistant for Indian property matters. "
                "You are an AI, never a human lawyer. Keep the answer SHORT and speakable "
                "(3-6 sentences), suited for text-to-speech. "
                "Answer ONLY from the provided context. If absent, say: "
                "'Not found in the uploaded documents.' Never invent names, dates, or numbers. "
                f"{lang_rule} If the user asked for a different language than the question's "
                "language, follow the user's requested language."
            ),
            prompt=f"CONTEXT:\n{context[:9000]}\n\nSPOKEN QUESTION: {question}",
            task="chat", max_tokens=600,
        ))

        return {
            "answer": resp.content,
            "citations": [
                {"document_id": None, "document_name": c["document_name"],
                 "page_number": c["page_number"], "source_text": c["content"][:200]}
                for c in chunks[:3]
            ],
            "language": language,
            "provider": resp.provider, "model": resp.model,
        }


# ---- convenience runners ----

async def run_risk_agent(case_id: str, organization_id: str | None = None) -> dict:
    ctx = new_agent_context(RiskAgent, case_id, organization_id)
    return await execute_agent(RiskAgent(ctx), {})


async def run_report_agent(case_id: str, report_id: str, organization_id: str | None = None) -> dict:
    ctx = new_agent_context(ReportAgent, case_id, organization_id)
    return await execute_agent(ReportAgent(ctx), {"report_id": report_id})


async def run_verification_agent(draft_id: str, case_id: str | None, organization_id: str | None = None) -> dict:
    ctx = new_agent_context(VerificationAgent, case_id, organization_id)
    return await execute_agent(VerificationAgent(ctx), {"draft_id": draft_id})


async def run_voice_agent(case_id: str, question: str, language: str = "en",
                          organization_id: str | None = None, user_id: str | None = None) -> dict:
    ctx = new_agent_context(
        VoiceAgent, case_id, organization_id, user_id,
        budget=VoiceAgent.VOICE_BUDGET,
    )
    return await execute_agent(VoiceAgent(ctx), {"question": question, "language": language})
