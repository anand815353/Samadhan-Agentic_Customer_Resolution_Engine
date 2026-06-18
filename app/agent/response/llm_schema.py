"""Structured LLM output schema for customer response generation (T-061)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.agent.response.response_types import RESPONSE_MAX_CHARACTERS


class LlmCustomerResponseOutput(BaseModel):
    """Strict provider output for response generation."""

    response_text: str = Field(..., min_length=1, max_length=RESPONSE_MAX_CHARACTERS)

    @field_validator("response_text")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("response_text must not be blank")
        return text
