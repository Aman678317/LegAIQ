"""Agent framework tests: budgets, loop prevention, tool governance."""
import asyncio
import uuid

import pytest

from app.ai.agents.base import (
    AgentBudget, AgentContext, BaseAgent, BudgetExceededError,
    LoopLimitError, Permission, new_agent_context,
)
from app.ai.agents.tools import ToolRegistry, Tool, ToolError
from app.ai.provider import LLMRequest, LLMResponse


def _resp(tokens=10):
    return LLMResponse(
        content="ok", provider="openai", model="test", latency_ms=1,
        prompt_tokens=tokens, completion_tokens=tokens,
    )


class TinyAgent(BaseAgent):
    name = "tiny_agent"
    default_permissions = (Permission.READ_ENTITIES,)

    async def run(self, task):
        for _ in range(task.get("llm_calls", 1)):
            await self.llm(LLMRequest(system="s", prompt="p"))
        for _ in range(task.get("iterations", 0)):
            self.check_iteration()
        return {"done": True}


class TestBudgets:
    def _wire_fake_llm(self, monkeypatch, tokens_per_call=20):
        """Stub the shared LLM router so each call reports real token usage."""
        from app.ai.provider import router as shared_router

        async def fake_complete(request):
            return _resp(tokens=tokens_per_call)

        monkeypatch.setattr(shared_router, "complete", fake_complete)

    def test_budget_blocks_after_max_llm_calls(self, monkeypatch):
        self._wire_fake_llm(monkeypatch)
        agent = TinyAgent(AgentContext(
            run_id="r1", agent_name="tiny",
            budget=AgentBudget(max_llm_calls=2),
        ))
        with pytest.raises(BudgetExceededError, match="max LLM calls"):
            asyncio.run(agent.run({"llm_calls": 3}))

    def test_budget_blocks_on_tokens(self, monkeypatch):
        self._wire_fake_llm(monkeypatch, tokens_per_call=30)
        agent = TinyAgent(AgentContext(
            run_id="r2", agent_name="tiny",
            budget=AgentBudget(max_llm_calls=99, max_prompt_tokens=50),
        ))
        with pytest.raises(BudgetExceededError, match="prompt token"):
            asyncio.run(agent.run({"llm_calls": 10}))

    def test_budget_blocks_on_cost(self, monkeypatch):
        self._wire_fake_llm(monkeypatch, tokens_per_call=2000)
        agent = TinyAgent(AgentContext(
            run_id="r3", agent_name="tiny",
            budget=AgentBudget(max_llm_calls=99, max_cost_usd=0.0001),
        ))
        with pytest.raises(BudgetExceededError, match="cost budget"):
            asyncio.run(agent.run({"llm_calls": 50}))

    def test_within_budget_succeeds(self, monkeypatch):
        self._wire_fake_llm(monkeypatch)
        agent = TinyAgent(AgentContext(
            run_id="r4", agent_name="tiny",
            budget=AgentBudget(max_llm_calls=3),
        ))
        result = asyncio.run(agent.run({"llm_calls": 2}))
        assert result == {"done": True}
        assert agent.usage.llm_calls == 2


class TestLoopPrevention:
    def test_iteration_cap_raises(self):
        agent = TinyAgent(AgentContext(
            run_id="r5", agent_name="tiny",
            budget=AgentBudget(max_iterations=3),
        ))
        with pytest.raises(LoopLimitError, match="max iterations"):
            asyncio.run(agent.run({"iterations": 5}))


class SleepyTool(Tool):
    name = "sleepy"
    description = "sleeps"
    permission = Permission.READ_ENTITIES
    timeout_s = 0.1

    async def _execute(self, ctx, params):
        await asyncio.sleep(5)
        return {}


class RecordTool(Tool):
    name = "recorder"
    description = "records"
    permission = Permission.READ_GRAPH
    max_calls_per_run = 2

    async def _execute(self, ctx, params):
        return {"ok": True}


class TestToolGovernance:
    def _ctx(self, perms):
        return AgentContext(
            run_id=f"run-{uuid.uuid4()}", agent_name="tester",
            permissions=set(perms), budget=AgentBudget(),
        )

    def test_unknown_tool_rejected(self):
        reg = ToolRegistry()
        with pytest.raises(ToolError, match="Unknown tool"):
            asyncio.run(reg.call(self._ctx([]), "nope", {}))

    def test_permission_denied(self):
        reg = ToolRegistry()
        reg.register(RecordTool())
        with pytest.raises(ToolError, match="lacks permission"):
            asyncio.run(reg.call(self._ctx([Permission.READ_ENTITIES]), "recorder", {}))

    def test_permission_granted_executes(self):
        reg = ToolRegistry()
        reg.register(RecordTool())
        result = asyncio.run(reg.call(self._ctx([Permission.READ_GRAPH]), "recorder", {}))
        assert result == {"ok": True}

    def test_rate_limit_per_run(self):
        reg = ToolRegistry()
        reg.register(RecordTool())
        ctx = self._ctx([Permission.READ_GRAPH])
        asyncio.run(reg.call(ctx, "recorder", {}))
        asyncio.run(reg.call(ctx, "recorder", {}))
        with pytest.raises(ToolError, match="rate limit"):
            asyncio.run(reg.call(ctx, "recorder", {}))

    def test_timeout_enforced(self):
        reg = ToolRegistry()
        reg.register(SleepyTool())
        with pytest.raises(ToolError, match="timed out"):
            asyncio.run(reg.call(self._ctx([Permission.READ_ENTITIES]), "sleepy", {}))

    def test_schema_validation(self):
        class SchemaTool(RecordTool):
            name = "schema_tool"
            permission = Permission.READ_GRAPH
            max_calls_per_run = 10
            schema = {
                "type": "object", "required": ["query"],
                "properties": {"query": {"type": "string"}},
            }

            async def _execute(self, ctx, params):
                return {"echo": params["query"]}

        reg = ToolRegistry()
        reg.register(SchemaTool())
        ctx = self._ctx([Permission.READ_GRAPH])
        with pytest.raises(ToolError, match="missing required param"):
            asyncio.run(reg.call(ctx, "schema_tool", {}))
        with pytest.raises(ToolError, match="expects string"):
            asyncio.run(reg.call(ctx, "schema_tool", {"query": 123}))
        assert asyncio.run(reg.call(ctx, "schema_tool", {"query": "hi"})) == {"echo": "hi"}
