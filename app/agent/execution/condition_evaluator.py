"""Deterministic conditional-step evaluation for tool execution (T-059)."""

from __future__ import annotations

from app.agent.planning.tool_plan_types import PLANNER_CONDITION_AFTER_BUREAU_CLOSURE_LETTER
from app.agent.state import ToolStepState
from app.tools.schemas import ToolOutput

_BUREAU_CLOSURE_LETTER_ACTIONS = frozenset(
    {
        "bureau_reporting_mismatch_detected",
        "bureau_closure_letter_requested",
    }
)


def bureau_closure_letter_needed(output: ToolOutput) -> bool:
    """Return True when bureau output warrants a closure-letter document step."""
    return output.success and output.action_taken in _BUREAU_CLOSURE_LETTER_ACTIONS


def should_execute_conditional_step(
    condition: str,
    *,
    step_index: int,
    tool_steps: list[ToolStepState],
) -> bool:
    """Evaluate a planner condition using trusted prior tool outputs only."""
    if condition == PLANNER_CONDITION_AFTER_BUREAU_CLOSURE_LETTER:
        if step_index == 0:
            return False
        prior = tool_steps[step_index - 1]
        if prior.tool_name != "BureauReportingTool":
            return False
        output = prior.tool_output
        if output is None:
            return False
        return bureau_closure_letter_needed(output)

    return False
