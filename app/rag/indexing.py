"""Policy document indexing orchestration for Qdrant (T-043)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.knowledge.services import KnowledgeDocumentService
from app.providers.fake_embedding import FakeEmbeddingProvider
from app.rag.chunking import DocumentChunker
from app.rag.embeddings import DocumentEmbeddingService
from app.rag.extraction import DocumentTextExtractor
from app.rag.indexing_schemas import DocumentIndexingResult
from app.rag.qdrant_store import PolicyVectorStore, QdrantStoreError, get_policy_vector_store


class PolicyDocumentIndexingService:
    """Index a knowledge document through extract → chunk → embed → Qdrant."""

    def __init__(
        self,
        knowledge_service: KnowledgeDocumentService,
        *,
        extractor: DocumentTextExtractor | None = None,
        chunker: DocumentChunker | None = None,
        embedding_service: DocumentEmbeddingService | None = None,
        vector_store: PolicyVectorStore | None = None,
        app_root: Path | None = None,
        settings: Settings | None = None,
    ) -> None:
        resolved_settings = settings or get_settings()
        root = (app_root or Path.cwd()).resolve()
        self._knowledge_service = knowledge_service
        self._extractor = extractor or DocumentTextExtractor(app_root=root)
        self._chunker = chunker or DocumentChunker(settings=resolved_settings)
        self._embedding_service = embedding_service or DocumentEmbeddingService(
            provider=FakeEmbeddingProvider(resolved_settings)
        )
        self._vector_store = vector_store or get_policy_vector_store(resolved_settings)

    async def index_document(self, document_id: str) -> DocumentIndexingResult:
        try:
            metadata = await self._knowledge_service.get_metadata(document_id)
        except NotFoundError:
            return DocumentIndexingResult(
                document_id=document_id,
                error=f"knowledge document not found: {document_id}",
            )

        warnings: list[str] = []

        extraction = self._extractor.extract_from_metadata(metadata)
        warnings.extend(extraction.warnings)
        if not extraction.success:
            await self._knowledge_service.mark_index_failed(document_id)
            return DocumentIndexingResult(
                document_id=document_id,
                warnings=warnings,
                error=extraction.error or "document extraction failed",
            )

        chunk_result = self._chunker.chunk(extraction, metadata)
        warnings.extend(chunk_result.warnings)
        if not chunk_result.success:
            await self._knowledge_service.mark_index_failed(document_id)
            return DocumentIndexingResult(
                document_id=document_id,
                warnings=warnings,
                error=chunk_result.error or "document chunking failed",
            )

        embedded, batch = await self._embedding_service.embed_chunks(chunk_result.chunks)
        if not batch.success:
            await self._knowledge_service.mark_index_failed(document_id)
            return DocumentIndexingResult(
                document_id=document_id,
                warnings=warnings,
                error=batch.error or "embedding failed",
            )

        indexed_at = datetime.now(UTC)
        try:
            await self._vector_store.ensure_collection(vector_size=batch.dimension)
            await self._vector_store.delete_document_version(
                metadata.document_id,
                metadata.version,
            )
            upserted = await self._vector_store.upsert_policy_chunks(
                embedded,
                indexed_at=indexed_at,
            )
        except QdrantStoreError as exc:
            await self._knowledge_service.mark_index_failed(document_id)
            return DocumentIndexingResult(
                document_id=document_id,
                warnings=warnings,
                error=exc.message,
            )

        if upserted != len(embedded):
            await self._knowledge_service.mark_index_failed(document_id)
            return DocumentIndexingResult(
                document_id=document_id,
                warnings=warnings,
                error="qdrant upsert count mismatch",
            )

        updated = await self._knowledge_service.mark_indexed(
            document_id,
            chunk_count=upserted,
        )
        return DocumentIndexingResult(
            document_id=document_id,
            chunk_count=upserted,
            indexed_at=updated.indexed_at,
            warnings=warnings,
        )
