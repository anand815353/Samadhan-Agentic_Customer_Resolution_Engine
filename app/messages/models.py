"""Message persistence models aligned with the MongoDB messages collection."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.messages.constants import SenderType
from app.messages.id_generation import MESSAGE_ID_PATTERN, validate_message_id
from app.tickets.id_generation import TICKET_ID_PATTERN
from app.tickets.models import CUSTOMER_ID_PATTERN, USER_ID_PATTERN


class MessageDocument(BaseModel):
    """MongoDB messages collection document."""

    model_config = ConfigDict(str_strip_whitespace=True)

    message_id: str = Field(..., pattern=MESSAGE_ID_PATTERN)
    ticket_id: str = Field(..., pattern=TICKET_ID_PATTERN)
    session_id: str = Field(..., min_length=1)
    customer_id: str = Field(..., pattern=CUSTOMER_ID_PATTERN)
    sender_type: SenderType
    sender_id: str | None = Field(default=None, pattern=USER_ID_PATTERN)
    message_text: str = Field(..., min_length=1)
    message_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    @model_validator(mode="after")
    def validate_sender_id_rules(self) -> "MessageDocument":
        if not validate_message_id(self.message_id):
            raise ValueError("invalid message_id format")

        if self.sender_type in ("customer", "support_agent"):
            if not self.sender_id:
                raise ValueError(f"{self.sender_type} messages require sender_id")
        elif self.sender_type in ("ai", "system"):
            if self.sender_id is not None:
                raise ValueError(f"{self.sender_type} messages must not have sender_id")

        return self

    def to_mongo_dict(self) -> dict[str, object]:
        """Serialize for MongoDB insert."""
        return self.model_dump(mode="json")
