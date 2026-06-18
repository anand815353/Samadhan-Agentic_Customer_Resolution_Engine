"""Dependency bundle for the agent resolution planner node (T-060)."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.resolution.resolution_types import RESOLUTION_PLANNER_POLICY_VERSION

_resolution_planner_deps_override: ResolutionPlannerDeps | None = None


@dataclass(frozen=True)
class ResolutionPlannerDeps:
    """Injected policy version for resolution planner execution."""

    policy_version: str = RESOLUTION_PLANNER_POLICY_VERSION


def set_resolution_planner_deps_override(deps: ResolutionPlannerDeps | None) -> None:
    """Override default resolution planner dependencies (primarily for tests)."""
    global _resolution_planner_deps_override
    _resolution_planner_deps_override = deps


def get_default_resolution_planner_deps() -> ResolutionPlannerDeps:
    """Return production resolution planner dependencies."""
    if _resolution_planner_deps_override is not None:
        return _resolution_planner_deps_override
    return ResolutionPlannerDeps()
