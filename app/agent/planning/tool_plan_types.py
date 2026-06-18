"""Shared types for deterministic tool planning (T-057)."""

from __future__ import annotations

from dataclasses import dataclass

from app.tools.constants import ToolName

TOOL_PLANNER_POLICY_VERSION = "1.0.0"
MAX_TOOL_PLAN_REASON_LENGTH = 200

PLANNER_CONDITION_AFTER_BUREAU_CLOSURE_LETTER = "after_bureau_tool_if_closure_letter_needed"


@dataclass(frozen=True)
class ToolPlanStep:
    """One ordered tool step before ToolInput materialization."""

    tool_name: ToolName
    document_type: str | None = None
    planner_condition: str | None = None
