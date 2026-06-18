"""Schemas for policy document chunking (T-041)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PolicyDocumentChunk(BaseModel):
    """A single pre-index policy chunk with document metadata preserved."""

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
    section_heading: str | None = None
    customer_visible: bool = True
    internal_only: bool = False


class DocumentChunkingResult(BaseModel):
    """Structured result from deterministic document chunking."""

    model_config = ConfigDict(str_strip_whitespace=True)

    chunks: list[PolicyDocumentChunk] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    @property
    def success(self) -> bool:
        return self.error is None and self.chunk_count > 0
