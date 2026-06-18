"""Shared types for deterministic tool plan execution (T-059)."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.state import ToolStepState, WorkflowError

TOOL_EXECUTION_POLICY_VERSION = "1.0.0"


@dataclass(frozen=True)
class ToolPlanExecutionResult:
    """Outcome of ordered mock-tool execution."""

    tool_steps: list[ToolStepState]
    audit_event_ids: list[str]
    workflow_errors: list[WorkflowError] | None = None
