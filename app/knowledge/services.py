"""Knowledge document business logic for policy/SOP metadata."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.common.service import BaseService
from app.core.exceptions import ConflictError, NotFoundError
from app.knowledge.models import KnowledgeDocumentDocument
from app.knowledge.repositories import KnowledgeDocumentRepository
from app.knowledge.schemas import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentUpdate,
    knowledge_document_from_create,
)


def is_customer_retrieval_eligible(document: KnowledgeDocumentDocument) -> bool:
    """Return True when metadata is eligible for future customer-facing retrieval."""
    return document.approval_status == "approved"


class KnowledgeDocumentService(BaseService):
    """Domain service for policy/SOP metadata persistence."""

    def __init__(
        self,
        repository: KnowledgeDocumentRepository,
        *,
        validate_storage_path: bool = False,
    ) -> None:
        self._repository = repository
        self._validate_storage_path = validate_storage_path

    async def create_metadata(
        self,
        data: KnowledgeDocumentCreate,
    ) -> KnowledgeDocumentDocument:
        existing = await self._repository.find_by_id(data.document_id)
        if existing is not None:
            raise ConflictError(f"knowledge document already exists: {data.document_id}")

        if self._validate_storage_path:
            self._assert_storage_path_exists(data.storage_path)

        document = knowledge_document_from_create(data)
        return await self._repository.insert(document)

    async def get_metadata(self, document_id: str) -> KnowledgeDocumentDocument:
        document = await self._repository.find_by_id(document_id)
        if document is None:
            raise NotFoundError(f"knowledge document not found: {document_id}")
        return document

    async def list_metadata(
        self,
        *,
        domain: str | None = None,
        approval_status: str | None = None,
        indexed_status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[KnowledgeDocumentDocument]:
        return await self._repository.list(
            domain=domain,
            approval_status=approval_status,
            indexed_status=indexed_status,
            skip=skip,
            limit=limit,
        )

    async def update_metadata(
        self,
        document_id: str,
        data: KnowledgeDocumentUpdate,
    ) -> KnowledgeDocumentDocument:
        document = await self.get_metadata(document_id)
        patch = data.model_dump(exclude_unset=True)
        if not patch:
            return document

        if "storage_path" in patch and self._validate_storage_path:
            self._assert_storage_path_exists(patch["storage_path"])

        updated = document.model_copy(update=patch)
        return await self._repository.update(updated)

    async def mark_not_indexed(self, document_id: str) -> KnowledgeDocumentDocument:
        document = await self.get_metadata(document_id)
        updated = document.model_copy(
            update={
                "indexed_status": "not_indexed",
                "chunk_count": 0,
                "indexed_at": None,
            }
        )
        return await self._repository.update(updated)

    async def mark_indexed(
        self,
        document_id: str,
        *,
        chunk_count: int,
    ) -> KnowledgeDocumentDocument:
        if chunk_count < 0:
            raise ValueError("chunk_count must be non-negative")
        document = await self.get_metadata(document_id)
        updated = document.model_copy(
            update={
                "indexed_status": "indexed",
                "chunk_count": chunk_count,
                "indexed_at": datetime.now(UTC),
            }
        )
        return await self._repository.update(updated)

    async def mark_index_failed(self, document_id: str) -> KnowledgeDocumentDocument:
        document = await self.get_metadata(document_id)
        updated = document.model_copy(
            update={
                "indexed_status": "failed",
                "chunk_count": 0,
                "indexed_at": None,
            }
        )
        return await self._repository.update(updated)

    @staticmethod
    def _assert_storage_path_exists(storage_path: str) -> None:
        if not Path(storage_path).is_file():
            raise ValueError(f"storage_path does not exist: {storage_path}")
