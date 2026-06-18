"""Dependency bundle for the agent intent classifier node (T-053)."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.providers.llm_service import LlmGenerationService, get_llm_generation_service

_intent_classifier_deps_override: IntentClassifierDeps | None = None


@dataclass(frozen=True)
class IntentClassifierDeps:
    """Injected services for intent classifier node execution."""

    llm_service: LlmGenerationService
    settings: Settings


def set_intent_classifier_deps_override(deps: IntentClassifierDeps | None) -> None:
    """Override default intent classifier dependencies (primarily for tests)."""
    global _intent_classifier_deps_override
    _intent_classifier_deps_override = deps


def build_intent_classifier_deps(*, settings: Settings | None = None) -> IntentClassifierDeps:
    """Build intent classifier dependencies from application settings."""
    resolved = settings or get_settings()
    return IntentClassifierDeps(
        llm_service=get_llm_generation_service(resolved),
        settings=resolved,
    )


def get_default_intent_classifier_deps(settings: Settings | None = None) -> IntentClassifierDeps:
    """Return intent classifier dependencies for workflow execution."""
    if _intent_classifier_deps_override is not None:
        return _intent_classifier_deps_override
    return build_intent_classifier_deps(settings=settings)
