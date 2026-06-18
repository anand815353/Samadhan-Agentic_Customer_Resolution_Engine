"""Admin policy indexing view models (T-045)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AdminPolicyRow(BaseModel):
    """Policy metadata row for the admin indexing list."""

    model_config = ConfigDict(str_strip_whitespace=True)

    document_id: str
    title: str
    domain: str
    approval_status: str
    indexed_status: str
    chunk_count: int = Field(ge=0)
    indexed_at: str | None = None
    source_filename: str
    reindex_eligible: bool
    ineligible_reason: str | None = None


class AdminReindexResult(BaseModel):
    """Result of an admin policy re-index attempt."""

    model_config = ConfigDict(str_strip_whitespace=True)

    document_id: str
    success: bool
    chunk_count: int = Field(default=0, ge=0)
    indexed_at: str | None = None
    message: str
    error_category: str | None = None
