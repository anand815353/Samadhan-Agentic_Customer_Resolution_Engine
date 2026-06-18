"""LangGraph tool planner node implementation (T-057)."""

from __future__ import annotations

import logging
from typing import Any

from app.agent.exceptions import ToolPlannerValidationError
from app.agent.nodes.base import NodeCallable
from app.agent.planning.intent_tool_policy import plan_tools
from app.agent.planning.tool_input_builder import build_tool_input
from app.agent.state import AgentState, ToolStepState
from app.agent.tool_planner_deps import ToolPlannerDeps
from app.tickets.constants import ALL_TICKET_INTENTS

logger = logging.getLogger("samadhan.agent")


class ToolPlannerNode:
    """Plan ordered mock tools from classified intent without executing them."""

    def __init__(self, deps: ToolPlannerDeps) -> None:
        self._deps = deps

    async def __call__(self, state: AgentState) -> dict[str, Any]:
        if state.customer_id is None:
            raise ToolPlannerValidationError(
                "customer_id is required before tool planning",
            )
        if state.ticket_id is None:
            raise ToolPlannerValidationError(
                "ticket_id is required before tool planning",
            )
        if not state.workflow_id:
            raise ToolPlannerValidationError(
                "workflow_id is required before tool planning",
            )
        if state.intent_classification is None:
            raise ToolPlannerValidationError(
                "intent classification is required before tool planning",
            )

        intent = state.intent_classification.intent
        if intent not in ALL_TICKET_INTENTS:
            raise ToolPlannerValidationError("unsupported intent for tool planning")

        try:
            result = plan_tools(state)
        except ValueError as exc:
            raise ToolPlannerValidationError(str(exc)) from exc

        if result.policy_version != self._deps.policy_version:
            raise ToolPlannerValidationError("tool planner policy version mismatch")

        tool_steps: list[ToolStepState] = []
        for step in result.steps:
            try:
                tool_input = build_tool_input(step, intent=intent, state=state)
            except ValueError as exc:
                raise ToolPlannerValidationError(str(exc)) from exc
            tool_steps.append(
                ToolStepState(
                    tool_name=step.tool_name,
                    tool_input=tool_input,
                    status="pending",
                    planner_condition=step.planner_condition,
                )
            )

        logger.info(
            "tool plan created workflow_id=%s ticket_id=%s intent=%s tools=%s policy=%s",
            state.workflow_id,
            state.ticket_id,
            intent,
            [step.tool_name for step in tool_steps],
            self._deps.policy_version,
        )

        return {
            "tool_plan_reason": result.reason,
            "tool_steps": tool_steps,
        }


def build_tool_planner_node(deps: ToolPlannerDeps) -> NodeCallable:
    """Return a tool planner node callable."""
    node = ToolPlannerNode(deps)

    async def tool_planner_node(state: AgentState) -> dict[str, Any]:
        return await node(state)

    return tool_planner_node


# Registry stub; build_default_registry replaces with build_tool_planner_node().
from app.agent.nodes.base import passthrough_node as tool_planner_node  # noqa: E402

__all__ = ["ToolPlannerNode", "build_tool_planner_node", "tool_planner_node"]
