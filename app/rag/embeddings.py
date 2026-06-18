"""RAG document embedding orchestration (T-042)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.providers.base_embedding import EmbeddingProvider, get_embedding_provider
from app.providers.embedding_schemas import EmbeddingBatchResult
from app.rag.embedding_schemas import EmbeddedPolicyChunk
from app.rag.chunk_schemas import PolicyDocumentChunk

if TYPE_CHECKING:
    pass


class DocumentEmbeddingService:
    """Embed policy chunks via the configured embedding provider."""

    def __init__(self, provider: EmbeddingProvider | None = None) -> None:
        self._provider = provider or get_embedding_provider()

    async def embed_chunks(
        self,
        chunks: list[PolicyDocumentChunk],
    ) -> tuple[list[EmbeddedPolicyChunk], EmbeddingBatchResult]:
        if not chunks:
            return [], EmbeddingBatchResult(
                provider=self._provider.provider_name,
                model=self._provider.model_name,
                dimension=self._provider.dimension,
                error="no chunks provided",
            )

        texts = [chunk.chunk_text for chunk in chunks]
        batch = await self._provider.embed_texts(texts)
        if not batch.success:
            return [], batch

        embedded = [
            EmbeddedPolicyChunk(
                **chunk.model_dump(),
                vector=vector.vector,
                embedding_provider=batch.provider,
                embedding_model=batch.model,
            )
            for chunk, vector in zip(chunks, batch.vectors, strict=True)
        ]
        return embedded, batch
