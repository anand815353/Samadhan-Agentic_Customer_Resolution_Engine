"""Policy retrieval service protocol and safe fallback implementations."""

from __future__ import annotations

from typing import Protocol

from app.core.config import Settings, get_settings
from app.rag.schemas import RetrievalRequest, RetrievalResult


class RetrievalServiceError(Exception):
    """Controlled retrieval failure without exposing stack traces to customers."""


class PolicyRetrievalService(Protocol):
    """Contract for policy/SOP chunk retrieval."""

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResult: ...


class UnavailablePolicyRetrievalService:
    """Fallback when retrieval is not configured."""

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        _ = request
        return RetrievalResult(unavailable=True)


class RaisingPolicyRetrievalService:
    """Test-only service that raises controlled retrieval errors."""

    def __init__(self, message: str = "retrieval backend error") -> None:
        self._message = message

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        _ = request
        raise RetrievalServiceError(self._message)


def get_policy_retrieval_service(
    settings: Settings | None = None,
    *,
    service: PolicyRetrievalService | None = None,
) -> PolicyRetrievalService:
    """Return the configured policy retrieval service without querying Qdrant at import."""
    if service is not None:
        return service
    resolved = settings or get_settings()
    if not resolved.qdrant_url.strip():
        return UnavailablePolicyRetrievalService()
    from app.rag.qdrant_retrieval import QdrantPolicyRetrievalService

    return QdrantPolicyRetrievalService(settings=resolved)
