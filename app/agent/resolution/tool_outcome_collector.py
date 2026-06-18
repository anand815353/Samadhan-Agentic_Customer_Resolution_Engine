"""Collect validated tool execution outcomes for resolution planning (T-060)."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.resolution.resolution_types import (
    DOCUMENT_COMPLETED_ACTIONS,
    SERVICE_REQUEST_CREATED_ACTIONS,
)
from app.agent.state import ToolStepState


@dataclass(frozen=True)
class ToolOutcomeSummary:
    """Aggregated successful tool execution results."""

    tool_actions: tuple[str, ...]
    service_request_ids: tuple[str, ...]
    any_tool_escalation: bool
    any_tool_failure: bool
    any_high_risk_tool_failure: bool
    has_successful_output: bool


def _dedupe_preserve_order(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def collect_tool_outcomes(
    tool_steps: list[ToolStepState],
    *,
    high_risk_intents: frozenset[str],
    intent: str,
) -> ToolOutcomeSummary:
    """Return ordered successful actions and SR IDs from completed tool steps."""
    actions: list[str] = []
    service_request_ids: list[str] = []
    any_tool_escalation = False
    any_tool_failure = False
    any_high_risk_tool_failure = False
    has_successful_output = False

    for step in tool_steps:
        if step.status == "completed" and step.tool_output is not None:
            output = step.tool_output
            if output.success:
                has_successful_output = True
                actions.append(output.action_taken)
                if output.escalation_required:
                    any_tool_escalation = True
                if output.service_request_id:
                    service_request_ids.append(output.service_request_id)
            elif output.escalation_required:
                any_tool_escalation = True
        elif step.status == "failed":
            any_tool_failure = True
            if step.tool_output is not None and step.tool_output.escalation_required:
                any_tool_escalation = True
            if intent in high_risk_intents:
                any_high_risk_tool_failure = True

    return ToolOutcomeSummary(
        tool_actions=_dedupe_preserve_order(actions),
        service_request_ids=_dedupe_preserve_order(service_request_ids),
        any_tool_escalation=any_tool_escalation,
        any_tool_failure=any_tool_failure,
        any_high_risk_tool_failure=any_high_risk_tool_failure,
        has_successful_output=has_successful_output,
    )


def primary_service_request_id(summary: ToolOutcomeSummary) -> str | None:
    """Return the last validated service-request ID from tool outputs."""
    if not summary.service_request_ids:
        return None
    return summary.service_request_ids[-1]


def has_document_completed(summary: ToolOutcomeSummary) -> bool:
    return any(action in DOCUMENT_COMPLETED_ACTIONS for action in summary.tool_actions)


def has_service_request_created(summary: ToolOutcomeSummary) -> bool:
    return any(action in SERVICE_REQUEST_CREATED_ACTIONS for action in summary.tool_actions)
