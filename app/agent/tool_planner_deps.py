"""Dependency bundle for the agent tool planner node."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.planning.tool_plan_types import TOOL_PLANNER_POLICY_VERSION

_tool_planner_deps_override: ToolPlannerDeps | None = None


@dataclass(frozen=True)
class ToolPlannerDeps:
    """Injected policy version for tool planner node execution."""

    policy_version: str = TOOL_PLANNER_POLICY_VERSION


def set_tool_planner_deps_override(deps: ToolPlannerDeps | None) -> None:
    """Override default tool planner dependencies (primarily for tests)."""
    global _tool_planner_deps_override
    _tool_planner_deps_override = deps


def get_default_tool_planner_deps() -> ToolPlannerDeps:
    """Return production tool planner dependencies."""
    if _tool_planner_deps_override is not None:
        return _tool_planner_deps_override
    return ToolPlannerDeps()
