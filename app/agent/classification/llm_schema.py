"""Structured LLM output schema for intent classification (T-053)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.tickets.constants import ALL_TICKET_INTENTS, TicketIntent


class LlmIntentClassificationOutput(BaseModel):
    """Strict provider output for intent classifier fallback."""

    intent: TicketIntent
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str | None = Field(default=None, max_length=200)

    @field_validator("intent")
    @classmethod
    def validate_supported_intent(cls, value: TicketIntent) -> TicketIntent:
        if value not in ALL_TICKET_INTENTS:
            raise ValueError(f"unsupported intent: {value}")
        return value
