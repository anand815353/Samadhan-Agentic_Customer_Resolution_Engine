"""Embedding provider protocol, errors, and factory (T-042)."""

from __future__ import annotations

from typing import Protocol

from app.core.config import Settings, get_settings
from app.providers.embedding_schemas import EmbeddingBatchResult


class EmbeddingProviderError(Exception):
    """Raised when embedding configuration or provider calls fail safely."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class EmbeddingProvider(Protocol):
    """Common embedding provider contract for RAG indexing."""

    provider_name: str
    model_name: str
    dimension: int

    async def embed_texts(self, texts: list[str]) -> EmbeddingBatchResult: ...


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    """Return the configured embedding provider without performing network I/O."""
    from app.providers.fake_embedding import FakeEmbeddingProvider
    from app.providers.gemini_embedding import GeminiEmbeddingProvider
    from app.providers.openai_embedding import OpenAIEmbeddingProvider
    from app.providers.vertex_embedding import VertexEmbeddingProvider

    resolved = settings or get_settings()
    match resolved.embedding_provider:
        case "fake":
            return FakeEmbeddingProvider(resolved)
        case "gemini_api":
            return GeminiEmbeddingProvider(resolved)
        case "openai":
            return OpenAIEmbeddingProvider(resolved)
        case "vertex_ai":
            return VertexEmbeddingProvider(resolved)
        case _:
            raise EmbeddingProviderError(
                f"unsupported embedding provider: {resolved.embedding_provider}"
            )
