"""RAG embedding result schemas (T-042)."""

from __future__ import annotations

from app.rag.chunk_schemas import PolicyDocumentChunk


class EmbeddedPolicyChunk(PolicyDocumentChunk):
    """Policy chunk with an embedding vector attached."""

    vector: list[float]
    embedding_provider: str
    embedding_model: str
