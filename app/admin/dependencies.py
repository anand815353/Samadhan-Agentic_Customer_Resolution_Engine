"""FastAPI dependencies for admin policy indexing (T-045)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import Depends

from app.core.config import Settings, get_settings

if TYPE_CHECKING:
    from app.admin.services import AdminPolicyIndexingService
    from app.audit.services import AuditService
    from app.knowledge.repositories import KnowledgeDocumentRepository
    from app.knowledge.services import KnowledgeDocumentService
    from app.rag.indexing import PolicyDocumentIndexingService

APP_ROOT = Path(__file__).resolve().parents[2]


@lru_cache
def _local_demo_knowledge_repository():
    from app.knowledge.models import knowledge_document_from_demo_row
    from app.knowledge.repositories import InMemoryKnowledgeDocumentRepository
    from app.seed.demo_policies import demo_knowledge_document_rows

    documents = [
        knowledge_document_from_demo_row(row) for row in demo_knowledge_document_rows()
    ]
    return InMemoryKnowledgeDocumentRepository(documents)


def get_knowledge_document_repository(
    settings: Settings = Depends(get_settings),
) -> KnowledgeDocumentRepository:
    """Return Mongo knowledge repository when configured, else seeded in-memory demo data."""
    from app.knowledge.repositories import (
        InMemoryKnowledgeDocumentRepository,
        MongoKnowledgeDocumentRepository,
    )

    if settings.mongodb_uri.strip() and settings.mongodb_db_name.strip():
        return MongoKnowledgeDocumentRepository(settings)
    return _local_demo_knowledge_repository()


def get_knowledge_document_service(
    repository: KnowledgeDocumentRepository = Depends(get_knowledge_document_repository),
) -> KnowledgeDocumentService:
    from app.knowledge.services import KnowledgeDocumentService

    return KnowledgeDocumentService(repository)


def get_audit_service() -> AuditService:
    from app.audit.repositories import InMemoryAuditLogRepository
    from app.audit.services import AuditService

    return AuditService(InMemoryAuditLogRepository())


def get_policy_indexing_service(
    knowledge_service: KnowledgeDocumentService = Depends(get_knowledge_document_service),
    settings: Settings = Depends(get_settings),
) -> PolicyDocumentIndexingService:
    from app.providers.base_embedding import get_embedding_provider
    from app.rag.embeddings import DocumentEmbeddingService
    from app.rag.indexing import PolicyDocumentIndexingService
    from app.rag.qdrant_store import get_policy_vector_store

    return PolicyDocumentIndexingService(
        knowledge_service,
        embedding_service=DocumentEmbeddingService(provider=get_embedding_provider(settings)),
        vector_store=get_policy_vector_store(settings),
        app_root=APP_ROOT,
        settings=settings,
    )


def get_admin_policy_indexing_service(
    knowledge_service: KnowledgeDocumentService = Depends(get_knowledge_document_service),
    indexing_service: PolicyDocumentIndexingService = Depends(get_policy_indexing_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> AdminPolicyIndexingService:
    from app.admin.services import AdminPolicyIndexingService

    return AdminPolicyIndexingService(
        knowledge_service,
        indexing_service,
        audit_service,
        app_root=APP_ROOT,
    )
