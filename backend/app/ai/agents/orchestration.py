"""Agent Orchestration State Machine and Workflow Execution Engine."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class NodeStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    RETRYING = "RETRYING"


class WorkflowNode(BaseModel):
    node_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_name: str
    agent_role: str
    status: NodeStatus = NodeStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)


class WorkflowState(BaseModel):
    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    case_id: str
    workflow_type: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    nodes: Dict[str, WorkflowNode] = Field(default_factory=dict)
    current_node: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_node(self, node: WorkflowNode) -> None:
        self.nodes[node.node_id] = node

    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        return self.nodes.get(node_id)

    def update_node(self, node_id: str, **updates) -> bool:
        if node_id not in self.nodes:
            return False
        node = self.nodes[node_id]
        for k, v in updates.items():
            if hasattr(node, k):
                setattr(node, k, v)
        return True

    def is_completed(self) -> bool:
        if self.status == WorkflowStatus.FAILED:
            return True
        if self.status == WorkflowStatus.PENDING:
            return False
        return all(n.status in [NodeStatus.COMPLETED, NodeStatus.SKIPPED] for n in self.nodes.values())