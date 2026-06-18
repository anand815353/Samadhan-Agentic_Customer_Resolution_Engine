"""LangGraph guardrail node implementation (T-058)."""

from __future__ import annotations

import logging
from typing import Any

from app.agent.exceptions import GuardrailValidationError
from app.agent.guardrail_deps import GuardrailDeps
from app.agent.guardrails.intent_guardrail_policy import evaluate_guardrails
from app.agent.guardrails.tool_plan_integrity import (
    scan_tool_plan_integrity,
    validate_tool_plan_prerequisites,
)
from app.agent.nodes.base import NodeCallable
from app.agent.state import AgentState, GuardrailState
from app.tickets.constants import ALL_TICKET_INTENTS

logger = logging.getLogger("samadhan.agent")


class GuardrailNode:
    """Validate planned tools and authorize safe mock execution."""

    def __init__(self, deps: GuardrailDeps) -> None:
        self._deps = deps

    async def __call__(self, state: AgentState) -> dict[str, Any]:
        try:
            validate_tool_plan_prerequisites(state)
        except ValueError as exc:
            raise GuardrailValidationError(str(exc)) from exc

        intent = state.intent_classification.intent  # type: ignore[union-attr]
        if intent not in ALL_TICKET_INTENTS:
            raise GuardrailValidationError("unsupported intent for guardrail evaluation")

        try:
            integrity = scan_tool_plan_integrity(state)
        except ValueError as exc:
            raise GuardrailValidationError(str(exc)) from exc

        result = evaluate_guardrails(state, integrity=integrity)

        if result.policy_version != self._deps.policy_version:
            raise GuardrailValidationError("guardrail policy version mismatch")

        logger.info(
            "guardrail evaluated workflow_id=%s ticket_id=%s intent=%s decision=%s "
            "escalation=%s approved=%s blocked=%s conditional=%s policy=%s",
            state.workflow_id,
            state.ticket_id,
            intent,
            result.decision,
            result.escalation_required,
            list(result.approved_step_indexes),
            list(result.blocked_step_indexes),
            list(result.conditional_step_indexes),
            self._deps.policy_version,
        )

        return {
            "guardrail": GuardrailState(
                decision=result.decision,
                reason=result.reason,
                allowed_actions=list(result.allowed_actions),
                escalation_required=result.escalation_required,
                approved_step_indexes=list(result.approved_step_indexes),
                blocked_step_indexes=list(result.blocked_step_indexes),
                conditional_step_indexes=list(result.conditional_step_indexes),
                policy_version=result.policy_version,
            ),
        }


def build_guardrail_node(deps: GuardrailDeps) -> NodeCallable:
    """Return a guardrail node callable."""
    node = GuardrailNode(deps)

    async def guardrail_node(state: AgentState) -> dict[str, Any]:
        return await node(state)

    return guardrail_node


# Registry stub; build_default_registry replaces with build_guardrail_node().
from app.agent.nodes.base import passthrough_node as guardrail_node  # noqa: E402

__all__ = ["GuardrailNode", "build_guardrail_node", "guardrail_node"]
