"""Defensive authorization validation before mock-tool invocation (T-059)."""

from __future__ import annotations

from app.agent.exceptions import ToolExecutionValidationError
from app.agent.guardrails.tool_plan_integrity import _validate_step_identity, validate_plan_replay
from app.agent.state import AgentState, GuardrailState
from app.tools.constants import ALL_TOOL_NAMES
from app.tools.registry import MockToolRegistry


def validate_execution_prerequisites(state: AgentState) -> GuardrailState:
    """Raise when upstream state is insufficient for tool execution."""
    if state.customer_id is None:
        raise ToolExecutionValidationError("customer_id is required before tool execution")
    if state.ticket_id is None:
        raise ToolExecutionValidationError("ticket_id is required before tool execution")
    if not state.workflow_id:
        raise ToolExecutionValidationError("workflow_id is required before tool execution")
    if state.guardrail is None:
        raise ToolExecutionValidationError("guardrail authorization is required before tool execution")
    if state.intent_classification is None:
        raise ToolExecutionValidationError("intent classification is required before tool execution")
    return state.guardrail


def validate_step_authorization(
    state: AgentState,
    step_index: int,
    *,
    guardrail: GuardrailState,
    registry: MockToolRegistry,
) -> None:
    """Revalidate identity, registry, and authorization immediately before invoke."""
    if step_index < 0 or step_index >= len(state.tool_steps):
        raise ToolExecutionValidationError(f"invalid tool step index: {step_index}")

    if step_index in guardrail.blocked_step_indexes and step_index in guardrail.approved_step_indexes:
        return

    if step_index in guardrail.blocked_step_indexes and step_index in guardrail.conditional_step_indexes:
        return

    step = state.tool_steps[step_index]
    if step.tool_input is None:
        raise ToolExecutionValidationError(f"tool step {step_index} is missing structured tool input")

    try:
        validate_plan_replay(state)
        _validate_step_identity(state, step_index)
    except ValueError as exc:
        raise ToolExecutionValidationError(str(exc)) from exc

    if step.tool_name not in ALL_TOOL_NAMES:
        raise ToolExecutionValidationError(f"unregistered tool at step {step_index}")

    if not registry.contains(step.tool_name):
        raise ToolExecutionValidationError(f"tool not available in registry: {step.tool_name}")


def step_execution_category(
    step_index: int,
    *,
    guardrail: GuardrailState,
) -> str:
    """Classify how a step should be handled: blocked, conditional, approved, or unapproved."""
    if step_index in guardrail.blocked_step_indexes:
        return "blocked"
    if step_index in guardrail.conditional_step_indexes:
        return "conditional"
    if step_index in guardrail.approved_step_indexes:
        return "approved"
    return "unapproved"
