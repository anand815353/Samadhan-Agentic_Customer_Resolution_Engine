"""Schemas for policy document text extraction (T-040)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SupportedFileType = Literal["md", "txt", "pdf"]


class DocumentExtractionResult(BaseModel):
    """Structured result from local policy document text extraction."""

    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = ""
    source_filename: str
    file_type: SupportedFileType | None = None
    page_count: int | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None and bool(self.text.strip())
