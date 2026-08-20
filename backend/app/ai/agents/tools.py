"""Agent tool registry.

Every tool declares: JSON schema, required permission, timeout, and a
per-agent-run rate limit. Calls are audit-logged to agent_tool_calls.
Tools are case-scoped: they only ever touch the case in the agent context.
"""
import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from pydantic import ValidationError
from supabase import create_client

from app.ai.agents.base import AgentContext, Permission
from app.config import get_settings

settings = get_settings()


class ToolError(Exception):
    pass


class Tool:
    name: str = "tool"
    description: str = ""
    schema: dict = {}
    permission: Permission
    timeout_s: float = 20.0
    max_calls_per_run: int = 10

    async def _execute(self, ctx: AgentContext, params: dict) -> Any:
        raise NotImplementedError


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._call_counts: dict[str, int] = {}  # "{run_id}:{tool}" -> count
        self._counter_touched: dict[str, float] = {}  # key -> last-use monotonic
        self._pruned_at = time.monotonic()

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise ToolError(f"Unknown tool '{name}'")
        return self._tools[name]

    def list_for_permissions(self, perms: set[Permission]) -> list[dict]:
        return [
            {"name": t.name, "description": t.description, "schema": t.schema}
            for t in self._tools.values()
            if t.permission in perms
        ]

    async def call(self, ctx: AgentContext, name: str, params: dict) -> Any:
        tool = self.get(name)

        # Permission check — agents cannot call tools they weren't granted
        if not ctx.has_permission(tool.permission):
            raise ToolError(
                f"Agent '{ctx.agent_name}' lacks permission '{tool.permission.value}' for tool '{name}'"
            )

        # Rate limit per run
        key = f"{ctx.run_id}:{name}"
        count = self._call_counts.get(key, 0)
        if count >= tool.max_calls_per_run:
            raise ToolError(f"Tool '{name}' rate limit reached ({tool.max_calls_per_run} calls/run)")
        self._call_counts[key] = count + 1
        self._counter_touched[key] = time.monotonic()
        self._prune_stale()

        # Schema validation when declared
        if tool.schema:
            type_map = {"string": str, "number": (int, float), "integer": int, "boolean": bool, "object": dict, "array": list}
            for req in tool.schema.get("required", []):
                if req not in params:
                    raise ToolError(f"Tool '{name}' missing required param '{req}'")
            for pname, pschema in tool.schema.get("properties", {}).items():
                if pname in params:
                    expected = type_map.get(pschema.get("type"))
                    if expected and not isinstance(params[pname], expected):
                        raise ToolError(
                            f"Tool '{name}' param '{pname}' expects {pschema.get('type')}"
                        )

        started = time.monotonic()
        status, result, error = "COMPLETED", None, None
        try:
            result = await asyncio.wait_for(tool._execute(ctx, params), timeout=tool.timeout_s)
            return result
        except asyncio.TimeoutError:
            status, error = "FAILED", f"Tool '{name}' timed out after {tool.timeout_s}s"
            raise ToolError(error)
        except Exception as e:
            status, error = "FAILED", str(e)[:300]
            raise
        finally:
            # Audit log — params kept small; never log document content
            try:
                url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
                key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "placeholder-key"
                db = create_client(url, key)
                if db:
                    db.table("agent_tool_calls").insert({
                        "agent_run_id": ctx.run_id,
                        "tool_name": name,
                        "status": status,
                        "duration_ms": int((time.monotonic() - started) * 1000),
                        "params": {k: (str(v)[:80]) for k, v in (params or {}).items()},
                        "error_message": error,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }).execute()
            except Exception:
                pass  # audit must never break the tool call

    def _prune_stale(self, max_age_seconds: float = 3600.0):
        """Drop counters for runs that finished long ago (bounded memory)."""
        now = time.monotonic()
        if now - self._pruned_at < 300:
            return  # prune at most every 5 minutes
        self._pruned_at = now
        stale = [k for k, t in self._counter_touched.items() if now - t > max_age_seconds]
        for k in stale:
            self._call_counts.pop(k, None)
            del self._counter_touched[k]


# ============ Tool implementations (case-scoped, read-only unless noted) ============

def _db():
    url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "placeholder-key"
    try:
        return create_client(url, key)
    except Exception:
        return None


class DocumentSearchTool(Tool):
    name = "document_search"
    description = "Full-text + vector search over the case's document chunks. Returns chunks with document, page, and text."
    permission = Permission.READ_DOCUMENTS
    timeout_s = 15.0
    max_calls_per_run = 8
    schema = {
        "type": "object",
        "required": ["query"],
        "properties": {"query": {"type": "string"}, "top_k": {"type": "integer"}},
    }

    async def _execute(self, ctx: AgentContext, params: dict) -> Any:
        from app.ai.provider import generate_embedding
        db = _db()
        if not db:
            return []
        top_k = min(params.get("top_k", 6), 12)
        results = []
        try:
            embedding = await generate_embedding(params["query"][:500])
            if embedding:
                rows = db.rpc("match_document_chunks", {
                    "p_case_id": ctx.case_id, "p_query_embedding": embedding, "p_top_k": top_k,
                }).execute().data or []
                results = rows
            kw = db.rpc("keyword_search_chunks", {
                "p_case_id": ctx.case_id, "p_query": params["query"][:500], "p_top_k": top_k,
            }).execute().data or []
        except Exception:
            kw = []
        seen, merged = set(), []
        for c in results + kw:
            if c.get("id") not in seen:
                seen.add(c.get("id"))
                merged.append({
                    "document_name": c.get("document_name"),
                    "page_number": c.get("page_number", 1),
                    "content": (c.get("content") or "")[:600],
                })
        return merged[:top_k]


class EntitySearchTool(Tool):
    name = "entity_search"
    description = "Query extracted entities for this case (parties, survey numbers, amounts...). Each result carries source text and confidence."
    permission = Permission.READ_ENTITIES
    timeout_s = 10.0
    schema = {
        "type": "object",
        "properties": {
            "entity_type": {"type": "string"},
            "value_like": {"type": "string"},
            "limit": {"type": "integer"},
        },
    }

    async def _execute(self, ctx: AgentContext, params: dict) -> Any:
        db = _db()
        if not db:
            return []
        try:
            q = db.table("extracted_entities").select(
                "entity_type, value, source_text, page_number, confidence, documents(file_name)"
            ).eq("case_id", ctx.case_id)
            if params.get("entity_type"):
                q = q.eq("entity_type", params["entity_type"])
            if params.get("value_like"):
                q = q.ilike("value", f"%{params['value_like']}%")
            rows = q.order("confidence", desc=True).limit(min(params.get("limit", 50), 200)).execute().data or []
            return [
                {
                    "entity_type": r["entity_type"], "value": r["value"],
                    "source_text": (r.get("source_text") or "")[:200],
                    "document": (r.get("documents") or {}).get("file_name"),
                    "page": r.get("page_number", 1), "confidence": float(r.get("confidence") or 0),
                }
                for r in rows
            ]
        except Exception:
            return []


class GraphSearchTool(Tool):
    name = "graph_search"
    description = "Fetch the ownership graph (nodes + evidenced edges) for the case."
    permission = Permission.READ_GRAPH
    timeout_s = 10.0

    async def _execute(self, ctx: AgentContext, params: dict) -> Any:
        db = _db()
        if not db:
            return {"nodes": [], "edges": []}
        try:
            nodes = db.table("ownership_nodes").select("*").eq("case_id", ctx.case_id).execute().data or []
            edges = db.table("ownership_edges").select("*").eq("case_id", ctx.case_id).execute().data or []
            return {
                "nodes": [{"id": n["id"], "type": n["node_type"], "label": n["label"]} for n in nodes],
                "edges": [
                    {"source": e["source_id"], "target": e["target_id"],
                     "type": e["edge_type"], "date": e.get("event_date"),
                     "confidence": float(e.get("confidence") or 0), "evidence": e.get("evidence")}
                    for e in edges
                ],
            }
        except Exception:
            return {"nodes": [], "edges": []}


class ComparisonTool(Tool):
    name = "comparison_read"
    description = "Read cross-document comparison results (match/mismatch findings with evidence)."
    permission = Permission.READ_GRAPH
    timeout_s = 10.0

    async def _execute(self, ctx: AgentContext, params: dict) -> Any:
        db = _db()
        if not db:
            return []
        try:
            return db.table("comparison_results").select("*").eq(
                "case_id", ctx.case_id
            ).order("created_at", desc=True).limit(100).execute().data or []
        except Exception:
            return []


class RiskTool(Tool):
    name = "risk_read"
    description = "Read the case risk register (level, category, evidence)."
    permission = Permission.READ_GRAPH
    timeout_s = 10.0

    async def _execute(self, ctx: AgentContext, params: dict) -> Any:
        db = _db()
        if not db:
            return []
        try:
            return db.table("risks").select("*").eq(
                "case_id", ctx.case_id
            ).eq("resolved", False).limit(200).execute().data or []
        except Exception:
            return []


class WebSearchTool(Tool):
    name = "web_search"
    description = "Search the public web (Indian legal sources prioritised). SSRF-guarded."
    permission = Permission.WEB_SEARCH
    timeout_s = 30.0
    max_calls_per_run = 5
    schema = {"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}}}

    async def _execute(self, ctx: AgentContext, params: dict) -> Any:
        from app.api.research import web_search
        return await web_search(params["query"][:300], limit=6)


class CitationTool(Tool):
    name = "citation_check"
    description = "Validate that cited URLs were actually retrieved in this run. Pass the list of candidate citations."
    permission = Permission.WEB_SEARCH
    timeout_s = 10.0
    schema = {
        "type": "object",
        "required": ["citations"],
        "properties": {"citations": {"type": "array"}},
    }

    async def _execute(self, ctx: AgentContext, params: dict) -> Any:
        known_urls: set[str] = set()
        if ctx.case_id:
            db = _db()
            sessions = db.table("research_sessions").select("id").eq("case_id", ctx.case_id).execute().data
            if sessions:
                rows = db.table("research_sources").select("url").in_(
                    "session_id", [s["id"] for s in sessions]
                ).execute().data
                known_urls = {r["url"] for r in rows}
        results = []
        for c in params["citations"][:20]:
            url = c if isinstance(c, str) else c.get("url", "")
            results.append({"url": url, "verified": url in known_urls})
        return results


registry = ToolRegistry()
registry.register(DocumentSearchTool())
registry.register(EntitySearchTool())
registry.register(GraphSearchTool())
registry.register(ComparisonTool())
registry.register(RiskTool())
registry.register(WebSearchTool())
registry.register(CitationTool())
