"""Dependency bundle for the agent response node (T-061)."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.response.response_types import RESPONSE_PROMPT_VERSION
from app.core.config import Settings, get_settings
from app.providers.llm_service import LlmGenerationService, get_llm_generation_service

_response_deps_override: ResponseDeps | None = None


@dataclass(frozen=True)
class ResponseDeps:
    """Injected services for response node execution."""

    llm_service: LlmGenerationService
    settings: Settings
    policy_version: str = RESPONSE_PROMPT_VERSION


def set_response_deps_override(deps: ResponseDeps | None) -> None:
    """Override default response dependencies (primarily for tests)."""
    global _response_deps_override
    _response_deps_override = deps


def build_response_deps(*, settings: Settings | None = None) -> ResponseDeps:
    """Build response dependencies from application settings."""
    resolved = settings or get_settings()
    return ResponseDeps(
        llm_service=get_llm_generation_service(resolved),
        settings=resolved,
    )


def get_default_response_deps(settings: Settings | None = None) -> ResponseDeps:
    """Return response dependencies for workflow execution."""
    if _response_deps_override is not None:
        return _response_deps_override
    return build_response_deps(settings=settings)
