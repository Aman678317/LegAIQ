"""Agent framework: budgets, loop prevention, and audit.

Every agent run gets token/time/cost budgets, a permission set, and an
iteration cap. Runs are recorded in ai_runs. No chain-of-thought is stored.
"""
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from supabase import create_client

from app.ai.provider import LLMRequest, LLMResponse, router as llm_router
from app.config import get_settings

settings = get_settings()


class BudgetExceededError(Exception):
    """Raised when an agent exceeds its token, cost, or time budget."""


class LoopLimitError(Exception):
    """Raised when an agent exceeds its max iterations (infinite-loop guard)."""


class Permission(str, Enum):
    READ_CASE = "read:case"
    READ_DOCUMENTS = "read:documents"
    READ_ENTITIES = "read:entities"
    READ_GRAPH = "read:graph"
    WRITE_FINDINGS = "write:findings"
    WRITE_RISKS = "write:risks"
    WRITE_DRAFTS = "write:drafts"
    WRITE_REPORTS = "write:reports"
    WEB_SEARCH = "web:search"
    WEB_FETCH = "web:fetch"
    VOICE = "voice"
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


@dataclass
class AgentBudget:
    max_llm_calls: int = 6
    max_prompt_tokens: int = 60_000
    max_completion_tokens: int = 12_000
    max_cost_usd: float = 0.50
    max_seconds: float = 240.0
    max_iterations: int = 8  # loop prevention on agentic loops
    max_tokens: Optional[int] = None
    max_tool_calls: Optional[int] = None
    max_cost: Optional[float] = None
    time_limit_seconds: Optional[int] = None


@dataclass
class AgentContext:
    """Everything an agent is allowed to know and touch for one run."""
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = "generic_agent"
    agent_type: Optional[str] = None
    case_id: Optional[str] = None
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    permissions: set[Permission] = field(default_factory=set)
    budget: AgentBudget = field(default_factory=AgentBudget)
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)
    context_data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.agent_type and (not self.agent_name or self.agent_name == "generic_agent"):
            self.agent_name = self.agent_type
        elif self.agent_name and not self.agent_type:
            self.agent_type = self.agent_name

    def has_permission(self, perm: Permission) -> bool:
        return perm in self.permissions


@dataclass
class UsageTracker:
    llm_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    started_at: float = field(default_factory=time.monotonic)
    iterations: int = 0

    # rough per-1k-token USD prices for estimates only
    PRICES = {
        ("openai", "in"): 0.00015, ("openai", "out"): 0.0006,
        ("anthropic", "in"): 0.003, ("anthropic", "out"): 0.015,
    }

    def record(self, response: LLMResponse):
        self.llm_calls += 1
        self.prompt_tokens += response.prompt_tokens
        self.completion_tokens += response.completion_tokens
        in_price = self.PRICES.get((response.provider, "in"), 0.0)
        out_price = self.PRICES.get((response.provider, "out"), 0.0)
        est = (response.prompt_tokens / 1000 * in_price
               + response.completion_tokens / 1000 * out_price)
        self.cost_usd += est

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_at


class BaseAgent:
    """Subclasses declare permissions + budget and implement `run`."""

    name: str = "base_agent"
    description: str = ""
    default_permissions: tuple[Permission, ...] = ()

    def __init__(self, ctx: AgentContext):
        self.ctx = ctx
        self.usage = UsageTracker()

    # ---- guarded LLM access ----
    async def llm(self, request: LLMRequest) -> LLMResponse:
        b = self.ctx.budget
        if self.usage.llm_calls >= b.max_llm_calls:
            raise BudgetExceededError(f"{self.name}: max LLM calls ({b.max_llm_calls}) reached")
        if self.usage.prompt_tokens >= b.max_prompt_tokens:
            raise BudgetExceededError(f"{self.name}: prompt token budget reached")
        if self.usage.completion_tokens >= b.max_completion_tokens:
            raise BudgetExceededError(f"{self.name}: completion token budget reached")
        if self.usage.cost_usd >= b.max_cost_usd:
            raise BudgetExceededError(f"{self.name}: cost budget (${b.max_cost_usd}) reached")
        if self.usage.elapsed_seconds >= b.max_seconds:
            raise BudgetExceededError(f"{self.name}: time budget ({b.max_seconds}s) reached")

        response = await llm_router.complete(request)
        self.usage.record(response)
        return response

    # ---- loop prevention for iterative tool loops ----
    def check_iteration(self, action: str = "iterate"):
        self.usage.iterations += 1
        if self.usage.iterations > self.ctx.budget.max_iterations:
            raise LoopLimitError(
                f"{self.name}: exceeded max iterations ({self.ctx.budget.max_iterations}) during '{action}'"
            )

    def has_permission(self, perm: Permission) -> bool:
        return self.ctx.has_permission(perm)

    # ---- persistence ----
    def _db(self):
        url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "placeholder-key"
        try:
            return create_client(url, key)
        except Exception:
            return None

    def persist_run_start(self):
        try:
            db = self._db()
            if db:
                db.table("agent_runs").insert({
                    "id": self.ctx.run_id,
                    "case_id": self.ctx.case_id,
                    "organization_id": self.ctx.organization_id,
                    "user_id": self.ctx.user_id,
                    "agent_name": self.name,
                    "status": "RUNNING",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                }).execute()
        except Exception:
            pass

    def persist_run_end(self, status: str = "COMPLETED", error: str | None = None):
        try:
            db = self._db()
            if db:
                db.table("agent_runs").update({
                    "status": status,
                    "error_message": error,
                    "llm_calls": self.usage.llm_calls,
                    "prompt_tokens": self.usage.prompt_tokens,
                    "completion_tokens": self.usage.completion_tokens,
                    "estimated_cost_usd": round(self.usage.cost_usd, 6),
                    "elapsed_seconds": round(self.usage.elapsed_seconds, 2),
                    "iterations": self.usage.iterations,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", self.ctx.run_id).execute()
        except Exception:
            pass

    # ---- subclass hook ----
    async def run(self, task: dict[str, Any]) -> Any:
        raise NotImplementedError


Agent = BaseAgent


def serialize_context(context: AgentContext) -> str:
    """Serialize context to JSON string."""
    return json.dumps({
        "run_id": context.run_id,
        "agent_name": context.agent_name,
        "agent_type": context.agent_type,
        "case_id": context.case_id,
        "organization_id": context.organization_id,
        "user_id": context.user_id,
        "permissions": [p.value for p in context.permissions],
        "input_data": context.input_data,
        "output_data": context.output_data,
        "context_data": context.context_data,
    })


def deserialize_context(context_json: str) -> AgentContext:
    """Deserialize context from JSON string."""
    data = json.loads(context_json)
    return AgentContext(
        run_id=data.get("run_id", str(uuid.uuid4())),
        agent_name=data.get("agent_name", "generic_agent"),
        agent_type=data.get("agent_type"),
        case_id=data.get("case_id"),
        organization_id=data.get("organization_id"),
        user_id=data.get("user_id"),
        permissions={Permission(p) for p in data.get("permissions", [])},
        input_data=data.get("input_data", {}),
        output_data=data.get("output_data", {}),
        context_data=data.get("context_data", {}),
    )


def new_agent_context(
    agent: Any = None,
    case_id: str | None = None,
    organization_id: str | None = None,
    user_id: str | None = None,
    budget: AgentBudget | None = None,
    extra_permissions: Any = (),
    permissions: Any = None,
    **kwargs,
) -> AgentContext:
    if isinstance(agent, str) and case_id is None:
        case_id = agent
        agent = None
    agent_name = "generic_agent"
    perms = set()
    if agent is not None:
        agent_name = getattr(agent, "name", getattr(agent, "AGENT_TYPE", "generic_agent"))
        if hasattr(agent, "default_permissions"):
            perms.update(agent.default_permissions)
        if hasattr(agent, "DEFAULT_PERMISSIONS"):
            perms.update(agent.DEFAULT_PERMISSIONS)
    elif "agent_type" in kwargs:
        agent_name = kwargs["agent_type"]
    
    if permissions is not None:
        perms.update(permissions)
    if extra_permissions:
        perms.update(extra_permissions)
        
    return AgentContext(
        run_id=str(uuid.uuid4()),
        agent_name=agent_name,
        agent_type=agent_name,
        case_id=case_id,
        organization_id=organization_id,
        user_id=user_id,
        permissions=perms,
        budget=budget or AgentBudget(),
    )


async def execute_agent(agent: BaseAgent, task: dict[str, Any]) -> Any:
    """Run an agent with full accounting; always records the run outcome."""
    agent.persist_run_start()
    try:
        result = await agent.run(task)
        agent.persist_run_end("COMPLETED")
        return result
    except (BudgetExceededError, LoopLimitError) as e:
        agent.persist_run_end("FAILED", error=str(e))
        raise
    except Exception as e:
        agent.persist_run_end("FAILED", error=str(e)[:500])
        raise
