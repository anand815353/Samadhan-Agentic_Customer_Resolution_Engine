"""Schemas for embedding provider requests and responses (T-042)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EmbeddingVectorResult(BaseModel):
    """A single embedded text input."""

    model_config = ConfigDict(str_strip_whitespace=True)

    text: str
    vector: list[float]
    index: int = Field(ge=0)


class EmbeddingBatchResult(BaseModel):
    """Batch embedding response from a provider."""

    model_config = ConfigDict(str_strip_whitespace=True)

    provider: str
    model: str
    dimension: int = Field(ge=1)
    vectors: list[EmbeddingVectorResult] = Field(default_factory=list)
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None and len(self.vectors) > 0
