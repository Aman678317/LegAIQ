"""Base Agent Classes and Context Serialization.

Defines Pydantic models for serializing agent state across asynchronous worker processes.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


class AgentBudget(BaseModel):
    max_iterations: int = 50
    max_tokens: int = 65536
    max_cost_usd: float = 5.0
    time_limit_seconds: int = 1800


class AgentContext(BaseModel):
    """Context and state serialization model for multi-agent workflows."""
    version: str = "1.0"
    case_id: str
    workflow_id: Optional[str] = None
    workflow_type: str = "custom"

    agent_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_name: str = "unknown"
    agent_role: str = "general"

    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    context_data: Dict[str, Any] = Field(default_factory=dict)

    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    status: str = "INIT"
    error_message: Optional[str] = None

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BudgetExceededError(Exception):
    """Raised when an agent workflow exceeds allocated resource budget."""
    pass


class LoopLimitError(Exception):
    """Raised when an agent workflow exceeds iteration limits."""
    pass


class Agent(BaseModel):
    name: str
    role: str
    description: str = ""
    max_retries: int = 3

    async def run(self, context: AgentContext) -> AgentContext:
        raise NotImplementedError

    def serialize_context(self, context: AgentContext) -> str:
        return context.model_dump_json()

    @classmethod
    def deserialize_context(cls, json_str: str) -> AgentContext:
        return AgentContext.model_validate_json(json_str)
