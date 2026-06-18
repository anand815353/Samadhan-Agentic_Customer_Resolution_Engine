"""Knowledge document repository ports and local implementations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from pydantic import ValidationError

from app.core.config import Settings
from app.knowledge.constants import KNOWLEDGE_DOCUMENTS_COLLECTION
from app.knowledge.models import KnowledgeDocumentDocument, knowledge_document_from_mongo
from app.seed.mongo import SeedMongoError, seed_mongo_session


class KnowledgeDocumentRepository(Protocol):
    """Knowledge document persistence contract."""

    async def find_by_id(self, document_id: str) -> KnowledgeDocumentDocument | None: ...

    async def list(
        self,
        *,
        domain: str | None = None,
        approval_status: str | None = None,
        indexed_status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[KnowledgeDocumentDocument]: ...

    async def insert(self, document: KnowledgeDocumentDocument) -> KnowledgeDocumentDocument: ...

    async def update(self, document: KnowledgeDocumentDocument) -> KnowledgeDocumentDocument: ...


def _sort_key_uploaded_at(document: KnowledgeDocumentDocument) -> str:
    return str(document.uploaded_at)


class InMemoryKnowledgeDocumentRepository:
    """In-memory knowledge document store for tests."""

    def __init__(
        self,
        documents: Iterable[KnowledgeDocumentDocument] | None = None,
    ) -> None:
        self._documents: dict[str, KnowledgeDocumentDocument] = {}
        if documents:
            for document in documents:
                self._documents[document.document_id] = document

    async def find_by_id(self, document_id: str) -> KnowledgeDocumentDocument | None:
        return self._documents.get(document_id)

    async def list(
        self,
        *,
        domain: str | None = None,
        approval_status: str | None = None,
        indexed_status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[KnowledgeDocumentDocument]:
        matches = list(self._documents.values())
        if domain is not None:
            matches = [document for document in matches if document.domain == domain]
        if approval_status is not None:
            matches = [
                document
                for document in matches
                if document.approval_status == approval_status
            ]
        if indexed_status is not None:
            matches = [
                document
                for document in matches
                if document.indexed_status == indexed_status
            ]
        matches.sort(key=_sort_key_uploaded_at, reverse=True)
        return matches[skip : skip + limit]

    async def insert(self, document: KnowledgeDocumentDocument) -> KnowledgeDocumentDocument:
        if document.document_id in self._documents:
            raise ValueError(f"knowledge document already exists: {document.document_id}")
        self._documents[document.document_id] = document
        return document

    async def update(self, document: KnowledgeDocumentDocument) -> KnowledgeDocumentDocument:
        if document.document_id not in self._documents:
            raise ValueError(f"knowledge document not found: {document.document_id}")
        self._documents[document.document_id] = document
        return document


class MongoKnowledgeDocumentRepository:
    """MongoDB-backed knowledge document persistence (T-039)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def find_by_id(self, document_id: str) -> KnowledgeDocumentDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                document = database[KNOWLEDGE_DOCUMENTS_COLLECTION].find_one(
                    {"document_id": document_id}
                )
                if document is None:
                    return None
                return knowledge_document_from_mongo(document)
        except (SeedMongoError, ValidationError):
            return None

    async def list(
        self,
        *,
        domain: str | None = None,
        approval_status: str | None = None,
        indexed_status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[KnowledgeDocumentDocument]:
        query: dict[str, Any] = {}
        if domain is not None:
            query["domain"] = domain
        if approval_status is not None:
            query["approval_status"] = approval_status
        if indexed_status is not None:
            query["indexed_status"] = indexed_status
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[KNOWLEDGE_DOCUMENTS_COLLECTION]
                    .find(query)
                    .sort("uploaded_at", -1)
                    .skip(skip)
                    .limit(limit)
                )
                return [knowledge_document_from_mongo(doc) for doc in cursor]
        except (SeedMongoError, ValidationError):
            return []

    async def insert(self, document: KnowledgeDocumentDocument) -> KnowledgeDocumentDocument:
        with seed_mongo_session(self._settings) as (_client, database):
            database[KNOWLEDGE_DOCUMENTS_COLLECTION].insert_one(document.to_mongo_dict())
        return document

    async def update(self, document: KnowledgeDocumentDocument) -> KnowledgeDocumentDocument:
        with seed_mongo_session(self._settings) as (_client, database):
            result = database[KNOWLEDGE_DOCUMENTS_COLLECTION].replace_one(
                {"document_id": document.document_id},
                document.to_mongo_dict(),
            )
            if result.matched_count == 0:
                raise ValueError(f"knowledge document not found: {document.document_id}")
        return document
