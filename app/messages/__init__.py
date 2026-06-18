"""Message domain module — model, repository, and service (T-022)."""

from app.messages.constants import ALL_SENDER_TYPES, MESSAGES_COLLECTION
from app.messages.exceptions import MessageAccessDeniedError, MessageValidationError
from app.messages.models import MessageDocument
from app.messages.repositories import (
    InMemoryMessageRepository,
    MessageRepository,
    MongoMessageRepository,
)
from app.messages.schemas import MessageCreate, MessageRead, message_document_from_create
from app.messages.services import MessageService

__all__ = [
    "ALL_SENDER_TYPES",
    "MESSAGES_COLLECTION",
    "InMemoryMessageRepository",
    "MessageAccessDeniedError",
    "MessageCreate",
    "MessageDocument",
    "MessageRead",
    "MessageRepository",
    "MessageService",
    "MessageValidationError",
    "MongoMessageRepository",
    "message_document_from_create",
]
