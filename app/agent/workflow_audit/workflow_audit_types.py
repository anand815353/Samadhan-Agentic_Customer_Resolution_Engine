"""Typed contracts for workflow audit persistence (T-063)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.agent.state import AgentState


@dataclass(frozen=True)
class WorkflowAuditCommand:
    """Validated inputs for workflow audit persistence."""

    state: AgentState


@dataclass(frozen=True)
class WorkflowAuditResult:
    """Outcome of workflow audit persistence."""

    workflow_audit_id: str
    event_type: str
    linked_tool_audit_ids: list[str]
    langsmith_trace_id: str | None
    workflow_status: str
    idempotent_replay: bool
    persisted_at: datetime | None = None
