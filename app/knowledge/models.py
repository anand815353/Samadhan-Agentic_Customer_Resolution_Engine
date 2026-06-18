"""Knowledge document persistence models aligned with DATA_MODEL §10.2."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.knowledge.constants import (
    ALL_POLICY_DOMAINS,
    ApprovalStatus,
    DOCUMENT_ID_PATTERN,
    DocumentType,
    IndexedStatus,
    PolicyDomain,
)


class KnowledgeDocumentDocument(BaseModel):
    """MongoDB knowledge_documents collection document."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    document_id: str = Field(..., pattern=DOCUMENT_ID_PATTERN)
    title: str = Field(..., min_length=1)
    document_type: DocumentType
    domain: PolicyDomain
    version: str = Field(..., min_length=1)
    effective_date: date | str
    approval_status: ApprovalStatus
    source_filename: str = Field(..., min_length=1)
    storage_path: str = Field(..., min_length=1)
    indexed_status: IndexedStatus = "not_indexed"
    chunk_count: int = Field(default=0, ge=0)
    uploaded_by: str = Field(..., min_length=1)
    uploaded_at: datetime | str
    indexed_at: datetime | str | None = None

    @field_validator("domain")
    @classmethod
    def _validate_domain(cls, value: str) -> str:
        if value not in ALL_POLICY_DOMAINS:
            raise ValueError(f"invalid policy domain: {value}")
        return value

    def to_mongo_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python")


def knowledge_document_from_demo_row(row: dict[str, Any]) -> KnowledgeDocumentDocument:
    """Build a KnowledgeDocumentDocument from a T-019 demo_policies row dict."""
    return KnowledgeDocumentDocument.model_validate(row)


def knowledge_document_from_mongo(document: dict[str, Any]) -> KnowledgeDocumentDocument:
    """Build KnowledgeDocumentDocument from a MongoDB record."""
    payload = dict(document)
    payload.pop("_id", None)
    return KnowledgeDocumentDocument.model_validate(payload)
