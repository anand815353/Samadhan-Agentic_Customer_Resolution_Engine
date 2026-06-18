"""RAG retrieval request/response schemas for policy chunk results."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RetrievedPolicyChunk(BaseModel):
    """A single approved policy chunk returned by retrieval."""

    model_config = ConfigDict(str_strip_whitespace=True)

    document_id: str
    title: str
    document_type: str
    domain: str
    version: str
    effective_date: str
    approval_status: str = "approved"
    chunk_index: int = 0
    chunk_text: str
    relevance_score: float | None = None
    source_filename: str | None = None
    indexed_at: str | None = None
    customer_visible: bool = True
    internal_only: bool = False


class RetrievalRequest(BaseModel):
    """Input contract for policy retrieval services."""

    model_config = ConfigDict(str_strip_whitespace=True)

    query: str
    intent: str | None = None
    domain: str | None = None
    top_k: int = Field(default=5, ge=1, le=10)
    min_score: float | None = Field(default=None, ge=0.0, le=1.0)
    document_type: str | None = None
    document_id: str | None = None
    approved_only: bool = True
    customer_visible_only: bool = True
    allowed_approval_statuses: list[str] | None = None


class RetrievalResult(BaseModel):
    """Output contract from policy retrieval services."""

    chunks: list[RetrievedPolicyChunk] = Field(default_factory=list)
    confidence: float | None = None
    unavailable: bool = False
    error_message: str | None = None
    total_results: int = 0
    requested_top_k: int = 0
    applied_domain_filter: str | None = None
    applied_score_threshold: float | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None
    warnings: list[str] = Field(default_factory=list)
