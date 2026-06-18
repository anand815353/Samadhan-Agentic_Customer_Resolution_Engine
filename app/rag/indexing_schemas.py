"""Schemas for policy document Qdrant indexing (T-043)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PolicyVectorPayload(BaseModel):
    """Qdrant payload for an indexed policy chunk."""

    model_config = ConfigDict(str_strip_whitespace=True)

    document_id: str
    title: str
    document_type: str
    domain: str
    version: str
    effective_date: str
    approval_status: str
    chunk_index: int = Field(ge=0)
    chunk_text: str = Field(min_length=1)
    source_filename: str
    indexed_at: str
    customer_visible: bool = True
    internal_only: bool = False
    section_heading: str | None = None


class DocumentIndexingResult(BaseModel):
    """Structured result from indexing a knowledge document into Qdrant."""

    model_config = ConfigDict(str_strip_whitespace=True)

    document_id: str
    chunk_count: int = Field(default=0, ge=0)
    indexed_at: datetime | str | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None and self.chunk_count > 0
