"""Deterministic fake embedding provider for tests and local no-key mode (T-042)."""

from __future__ import annotations

import hashlib
import struct

from app.core.config import Settings
from app.providers.embedding_schemas import EmbeddingBatchResult, EmbeddingVectorResult

DEFAULT_FAKE_DIMENSION = 768


def deterministic_vector(text: str, *, dimension: int = DEFAULT_FAKE_DIMENSION) -> list[float]:
    """Build a stable pseudo-embedding vector from text using SHA-256 expansion."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    counter = 0
    while len(values) < dimension:
        block = hashlib.sha256(digest + counter.to_bytes(4, "big")).digest()
        for index in range(0, len(block), 4):
            if len(values) >= dimension:
                break
            raw = struct.unpack(">I", block[index : index + 4])[0]
            values.append((raw / 0xFFFFFFFF) * 2.0 - 1.0)
        counter += 1
    return values


class FakeEmbeddingProvider:
    """Hash-based embedding provider with no external dependencies."""

    provider_name = "fake"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.model_name = "fake-hash-v1"
        self.dimension = settings.fake_embedding_dimension

    async def embed_texts(self, texts: list[str]) -> EmbeddingBatchResult:
        if not texts:
            return EmbeddingBatchResult(
                provider=self.provider_name,
                model=self.model_name,
                dimension=self.dimension,
                error="no texts provided",
            )

        vectors = [
            EmbeddingVectorResult(
                text=text,
                vector=deterministic_vector(text, dimension=self.dimension),
                index=index,
            )
            for index, text in enumerate(texts)
        ]
        return EmbeddingBatchResult(
            provider=self.provider_name,
            model=self.model_name,
            dimension=self.dimension,
            vectors=vectors,
        )
