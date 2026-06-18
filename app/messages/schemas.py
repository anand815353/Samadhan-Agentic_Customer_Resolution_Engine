"""Message input and API-safe schemas."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.messages.constants import SenderType
from app.messages.id_generation import MESSAGE_ID_PATTERN
from app.messages.models import MessageDocument


class MessageCreate(BaseModel):
    """Input for creating a chat message."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ticket_id: str = Field(..., pattern=r"^TKT-\d{4}-\d{4}$")
    session_id: str = Field(..., min_length=1)
    customer_id: str
    sender_type: SenderType
    message_text: str = Field(..., min_length=1)
    sender_id: str | None = None
    message_metadata: dict[str, Any] = Field(default_factory=dict)
    message_id: str | None = Field(default=None, pattern=MESSAGE_ID_PATTERN)


class MessageRead(BaseModel):
    """API-safe message representation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    message_id: str
    ticket_id: str
    session_id: str
    customer_id: str
    sender_type: SenderType
    sender_id: str | None = None
    message_text: str
    message_metadata: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_document(cls, document: MessageDocument) -> "MessageRead":
        return cls(
            message_id=document.message_id,
            ticket_id=document.ticket_id,
            session_id=document.session_id,
            customer_id=document.customer_id,
            sender_type=document.sender_type,
            sender_id=document.sender_id,
            message_text=document.message_text,
            message_metadata=document.message_metadata,
            created_at=document.created_at,
        )


def message_document_from_create(
    data: MessageCreate,
    *,
    message_id: str,
    now: datetime | None = None,
) -> MessageDocument:
    """Build a MessageDocument from create input."""
    timestamp = now or datetime.now(UTC)
    return MessageDocument(
        message_id=message_id,
        ticket_id=data.ticket_id,
        session_id=data.session_id,
        customer_id=data.customer_id,
        sender_type=data.sender_type,
        sender_id=data.sender_id,
        message_text=data.message_text,
        message_metadata=data.message_metadata,
        created_at=timestamp,
    )
