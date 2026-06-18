"""Message repository port and local implementations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from pydantic import ValidationError

from app.core.config import Settings
from app.messages.constants import MESSAGES_COLLECTION
from app.messages.id_generation import parse_message_id
from app.messages.models import MessageDocument
from app.seed.mongo import SeedMongoError, seed_mongo_session


class MessageRepository(Protocol):
    """Message persistence contract."""

    async def insert(self, document: MessageDocument) -> MessageDocument: ...

    async def find_by_id(self, message_id: str) -> MessageDocument | None: ...

    async def find_by_ticket(
        self,
        ticket_id: str,
        *,
        limit: int = 200,
    ) -> list[MessageDocument]: ...

    async def find_by_session(
        self,
        session_id: str,
        *,
        limit: int = 200,
    ) -> list[MessageDocument]: ...

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[MessageDocument]: ...

    async def max_sequence_for_year(self, year: int) -> int: ...


class InMemoryMessageRepository:
    """In-memory message store for tests."""

    def __init__(self, messages: Iterable[MessageDocument] | None = None) -> None:
        self._messages: dict[str, MessageDocument] = {}
        if messages:
            for message in messages:
                self._messages[message.message_id] = message

    async def insert(self, document: MessageDocument) -> MessageDocument:
        if document.message_id in self._messages:
            raise ValueError(f"message already exists: {document.message_id}")
        self._messages[document.message_id] = document
        return document

    async def find_by_id(self, message_id: str) -> MessageDocument | None:
        return self._messages.get(message_id)

    async def find_by_ticket(
        self,
        ticket_id: str,
        *,
        limit: int = 200,
    ) -> list[MessageDocument]:
        matches = [
            message for message in self._messages.values() if message.ticket_id == ticket_id
        ]
        matches.sort(key=lambda message: message.created_at)
        return matches[:limit]

    async def find_by_session(
        self,
        session_id: str,
        *,
        limit: int = 200,
    ) -> list[MessageDocument]:
        matches = [
            message for message in self._messages.values() if message.session_id == session_id
        ]
        matches.sort(key=lambda message: message.created_at)
        return matches[:limit]

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[MessageDocument]:
        matches = [
            message
            for message in self._messages.values()
            if message.customer_id == customer_id
        ]
        matches.sort(key=lambda message: message.created_at, reverse=True)
        return matches[:limit]

    async def max_sequence_for_year(self, year: int) -> int:
        max_seq = 0
        for message_id in self._messages:
            try:
                message_year, sequence = parse_message_id(message_id)
            except ValueError:
                continue
            if message_year == year:
                max_seq = max(max_seq, sequence)
        return max_seq


class MongoMessageRepository:
    """MongoDB-backed message persistence (T-022)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def insert(self, document: MessageDocument) -> MessageDocument:
        with seed_mongo_session(self._settings) as (_client, database):
            database[MESSAGES_COLLECTION].insert_one(document.to_mongo_dict())
        return document

    async def find_by_id(self, message_id: str) -> MessageDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                record = database[MESSAGES_COLLECTION].find_one({"message_id": message_id})
                if record is None:
                    return None
                return _document_from_mongo(record)
        except (SeedMongoError, ValidationError):
            return None

    async def find_by_ticket(
        self,
        ticket_id: str,
        *,
        limit: int = 200,
    ) -> list[MessageDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[MESSAGES_COLLECTION]
                    .find({"ticket_id": ticket_id})
                    .sort("created_at", 1)
                    .limit(limit)
                )
                return [_document_from_mongo(record) for record in cursor]
        except (SeedMongoError, ValidationError):
            return []

    async def find_by_session(
        self,
        session_id: str,
        *,
        limit: int = 200,
    ) -> list[MessageDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[MESSAGES_COLLECTION]
                    .find({"session_id": session_id})
                    .sort("created_at", 1)
                    .limit(limit)
                )
                return [_document_from_mongo(record) for record in cursor]
        except (SeedMongoError, ValidationError):
            return []

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[MessageDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[MESSAGES_COLLECTION]
                    .find({"customer_id": customer_id})
                    .sort("created_at", -1)
                    .limit(limit)
                )
                return [_document_from_mongo(record) for record in cursor]
        except (SeedMongoError, ValidationError):
            return []

    async def max_sequence_for_year(self, year: int) -> int:
        prefix = f"MSG-{year}-"
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[MESSAGES_COLLECTION]
                    .find({"message_id": {"$regex": f"^{prefix}"}})
                    .sort("message_id", -1)
                    .limit(1)
                )
                records = list(cursor)
                if not records:
                    return 0
                _year, sequence = parse_message_id(records[0]["message_id"])
                return sequence
        except (SeedMongoError, ValidationError, ValueError):
            return 0


def _document_from_mongo(document: dict[str, Any]) -> MessageDocument:
    """Build MessageDocument from a MongoDB record."""
    payload = dict(document)
    payload.pop("_id", None)
    return MessageDocument.model_validate(payload)
