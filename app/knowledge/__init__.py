"""Policy/SOP knowledge document metadata domain (T-039)."""

from app.knowledge.constants import (
    ALL_APPROVAL_STATUSES,
    ALL_DOCUMENT_TYPES,
    ALL_INDEXED_STATUSES,
    KNOWLEDGE_DOCUMENTS_COLLECTION,
)
from app.knowledge.models import KnowledgeDocumentDocument, knowledge_document_from_demo_row
from app.knowledge.repositories import (
    InMemoryKnowledgeDocumentRepository,
    KnowledgeDocumentRepository,
    MongoKnowledgeDocumentRepository,
)
from app.knowledge.schemas import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentRead,
    KnowledgeDocumentUpdate,
)
from app.knowledge.services import KnowledgeDocumentService, is_customer_retrieval_eligible

__all__ = [
    "ALL_APPROVAL_STATUSES",
    "ALL_DOCUMENT_TYPES",
    "ALL_INDEXED_STATUSES",
    "InMemoryKnowledgeDocumentRepository",
    "KNOWLEDGE_DOCUMENTS_COLLECTION",
    "KnowledgeDocumentCreate",
    "KnowledgeDocumentDocument",
    "KnowledgeDocumentRead",
    "KnowledgeDocumentRepository",
    "KnowledgeDocumentService",
    "KnowledgeDocumentUpdate",
    "MongoKnowledgeDocumentRepository",
    "is_customer_retrieval_eligible",
    "knowledge_document_from_demo_row",
]
