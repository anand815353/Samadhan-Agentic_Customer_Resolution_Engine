"""Dependency bundle for the agent retrieval node."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.rag.retrieval import PolicyRetrievalService, get_policy_retrieval_service

_retrieval_deps_override: RetrievalDeps | None = None


@dataclass(frozen=True)
class RetrievalDeps:
    """Injected retrieval service and settings for retrieval node execution."""

    policy_retrieval_service: PolicyRetrievalService
    settings: Settings


def set_retrieval_deps_override(deps: RetrievalDeps | None) -> None:
    """Override default retrieval dependencies (primarily for tests)."""
    global _retrieval_deps_override
    _retrieval_deps_override = deps


def get_default_retrieval_deps() -> RetrievalDeps:
    """Return production retrieval dependencies."""
    if _retrieval_deps_override is not None:
        return _retrieval_deps_override
    settings = get_settings()
    return RetrievalDeps(
        policy_retrieval_service=get_policy_retrieval_service(settings),
        settings=settings,
    )
