"""LangGraph resolution planner node implementation (T-060)."""

from __future__ import annotations

import logging
from typing import Any

from app.agent.exceptions import ResolutionPlannerValidationError
from app.agent.nodes.base import NodeCallable
from app.agent.resolution.resolution_planner import plan_resolution
from app.agent.resolution.resolution_types import RESOLUTION_PLANNER_POLICY_VERSION
from app.agent.resolution_planner_deps import ResolutionPlannerDeps
from app.agent.state import AgentState

logger = logging.getLogger("samadhan.agent")


class ResolutionPlannerNode:
    """Produce a deterministic structured resolution plan from workflow state."""

    def __init__(self, deps: ResolutionPlannerDeps) -> None:
        self._deps = deps

    async def __call__(self, state: AgentState) -> dict[str, Any]:
        if self._deps.policy_version != RESOLUTION_PLANNER_POLICY_VERSION:
            raise ResolutionPlannerValidationError("resolution planner policy version mismatch")

        try:
            plan = plan_resolution(state)
        except ResolutionPlannerValidationError:
            raise
        except ValueError as exc:
            raise ResolutionPlannerValidationError(str(exc)) from exc

        logger.info(
            "resolution planned workflow_id=%s ticket_id=%s intent=%s "
            "ticket_status=%s escalation=%s response_type=%s tools=%s",
            state.workflow_id,
            state.ticket_id,
            plan.intent,
            plan.ticket_status,
            plan.escalation_required,
            plan.customer_response_type,
            plan.tool_actions,
        )
        return {"resolution_plan": plan}


def build_resolution_planner_node(deps: ResolutionPlannerDeps) -> NodeCallable:
    """Return a resolution planner node callable."""
    node = ResolutionPlannerNode(deps)

    async def resolution_planner_node(state: AgentState) -> dict[str, Any]:
        return await node(state)

    return resolution_planner_node


# Registry stub; build_default_registry replaces with build_resolution_planner_node().
from app.agent.nodes.base import passthrough_node as resolution_planner_node  # noqa: E402

__all__ = ["ResolutionPlannerNode", "build_resolution_planner_node", "resolution_planner_node"]
