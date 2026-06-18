"""LangGraph tool execution node implementation (T-059)."""

from __future__ import annotations

import logging
from typing import Any

from app.agent.exceptions import ToolExecutionValidationError
from app.agent.execution.execution_types import TOOL_EXECUTION_POLICY_VERSION
from app.agent.execution.tool_plan_executor import ToolPlanExecutor
from app.agent.nodes.base import NodeCallable
from app.agent.state import AgentState
from app.agent.tool_execution_deps import ToolExecutionDeps

logger = logging.getLogger("samadhan.agent")


class ToolExecutionNode:
    """Execute T-058-authorized mock tools and write results to canonical state."""

    def __init__(self, deps: ToolExecutionDeps) -> None:
        self._deps = deps

    async def __call__(self, state: AgentState) -> dict[str, Any]:
        if self._deps.policy_version != TOOL_EXECUTION_POLICY_VERSION:
            raise ToolExecutionValidationError("tool execution policy version mismatch")

        executor = ToolPlanExecutor(
            self._deps.registry,
            tool_timeout_seconds=self._deps.tool_timeout_seconds,
        )
        result = await executor.execute(state)

        update: dict[str, Any] = {
            "tool_steps": result.tool_steps,
            "audit_event_ids": result.audit_event_ids,
        }
        if result.workflow_errors:
            update["workflow_errors"] = [*state.workflow_errors, *result.workflow_errors]

        executed = sum(1 for step in result.tool_steps if step.status == "completed")
        skipped = sum(1 for step in result.tool_steps if step.status == "skipped")
        failed = sum(1 for step in result.tool_steps if step.status == "failed")
        logger.info(
            "tool execution finished workflow_id=%s ticket_id=%s executed=%s skipped=%s failed=%s",
            state.workflow_id,
            state.ticket_id,
            executed,
            skipped,
            failed,
        )
        return update


def build_tool_execution_node(deps: ToolExecutionDeps) -> NodeCallable:
    """Return a tool execution node callable."""
    node = ToolExecutionNode(deps)

    async def tool_execution_node(state: AgentState) -> dict[str, Any]:
        return await node(state)

    return tool_execution_node


# Registry stub; build_default_registry replaces with build_tool_execution_node().
from app.agent.nodes.base import passthrough_node as tool_execution_node  # noqa: E402

__all__ = ["ToolExecutionNode", "build_tool_execution_node", "tool_execution_node"]
