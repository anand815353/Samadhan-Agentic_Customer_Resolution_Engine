"""Knowledge document input and API-safe schemas."""

from __future__ import annotations

from datetime import UTC, date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.knowledge.constants import (
    ApprovalStatus,
    DOCUMENT_ID_PATTERN,
    DocumentType,
    IndexedStatus,
    PolicyDomain,
)
from app.knowledge.models import KnowledgeDocumentDocument


class KnowledgeDocumentCreate(BaseModel):
    """Input for creating policy/SOP metadata."""

    model_config = ConfigDict(str_strip_whitespace=True)

    document_id: str = Field(..., pattern=DOCUMENT_ID_PATTERN)
    title: str = Field(..., min_length=1)
    document_type: DocumentType
    domain: PolicyDomain
    version: str = Field(..., min_length=1)
    effective_date: date | str
    approval_status: ApprovalStatus
    source_filename: str = Field(..., min_length=1)
    storage_path: str = Field(..., min_length=1)
    uploaded_by: str = Field(..., min_length=1)
    indexed_status: IndexedStatus = "not_indexed"
    chunk_count: int = Field(default=0, ge=0)
    uploaded_at: datetime | str | None = None
    indexed_at: datetime | str | None = None


class KnowledgeDocumentUpdate(BaseModel):
    """Partial update for policy/SOP metadata."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1)
    version: str | None = Field(default=None, min_length=1)
    effective_date: date | str | None = None
    approval_status: ApprovalStatus | None = None
    source_filename: str | None = Field(default=None, min_length=1)
    storage_path: str | None = Field(default=None, min_length=1)


class KnowledgeDocumentRead(BaseModel):
    """API-safe knowledge document representation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    document_id: str
    title: str
    document_type: DocumentType
    domain: PolicyDomain
    version: str
    effective_date: date | str
    approval_status: ApprovalStatus
    source_filename: str
    storage_path: str
    indexed_status: IndexedStatus
    chunk_count: int
    uploaded_by: str
    uploaded_at: datetime | str
    indexed_at: datetime | str | None = None

    @classmethod
    def from_document(cls, document: KnowledgeDocumentDocument) -> KnowledgeDocumentRead:
        return cls(
            document_id=document.document_id,
            title=document.title,
            document_type=document.document_type,
            domain=document.domain,
            version=document.version,
            effective_date=document.effective_date,
            approval_status=document.approval_status,
            source_filename=document.source_filename,
            storage_path=document.storage_path,
            indexed_status=document.indexed_status,
            chunk_count=document.chunk_count,
            uploaded_by=document.uploaded_by,
            uploaded_at=document.uploaded_at,
            indexed_at=document.indexed_at,
        )


def knowledge_document_from_create(
    data: KnowledgeDocumentCreate,
    *,
    now: datetime | None = None,
) -> KnowledgeDocumentDocument:
    """Build a KnowledgeDocumentDocument from create input."""
    timestamp = now or datetime.now(UTC)
    uploaded_at = data.uploaded_at if data.uploaded_at is not None else timestamp
    return KnowledgeDocumentDocument(
        document_id=data.document_id,
        title=data.title,
        document_type=data.document_type,
        domain=data.domain,
        version=data.version,
        effective_date=data.effective_date,
        approval_status=data.approval_status,
        source_filename=data.source_filename,
        storage_path=data.storage_path,
        indexed_status=data.indexed_status,
        chunk_count=data.chunk_count,
        uploaded_by=data.uploaded_by,
        uploaded_at=uploaded_at,
        indexed_at=data.indexed_at,
    )
