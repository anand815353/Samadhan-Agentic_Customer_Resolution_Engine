"""Dependency bundle for the agent guardrail node."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.guardrails.guardrail_types import GUARDRAIL_POLICY_VERSION

_guardrail_deps_override: GuardrailDeps | None = None


@dataclass(frozen=True)
class GuardrailDeps:
    """Injected policy version for guardrail node execution."""

    policy_version: str = GUARDRAIL_POLICY_VERSION


def set_guardrail_deps_override(deps: GuardrailDeps | None) -> None:
    """Override default guardrail dependencies (primarily for tests)."""
    global _guardrail_deps_override
    _guardrail_deps_override = deps


def get_default_guardrail_deps() -> GuardrailDeps:
    """Return production guardrail dependencies."""
    if _guardrail_deps_override is not None:
        return _guardrail_deps_override
    return GuardrailDeps()
