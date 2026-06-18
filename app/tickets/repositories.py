"""Ticket repository port and local implementations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from pydantic import ValidationError

from app.core.config import Settings
from app.seed.mongo import SeedMongoError, seed_mongo_session
from app.tickets.constants import HUMAN_REVIEW_QUEUE_STATUSES, TICKETS_COLLECTION
from app.tickets.id_generation import parse_ticket_id
from app.tickets.models import TicketDocument


class TicketRepository(Protocol):
    """Ticket persistence contract."""

    async def find_by_id(self, ticket_id: str) -> TicketDocument | None: ...

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[TicketDocument]: ...

    async def list_human_review_queue(
        self,
        *,
        priority: str | None = None,
    ) -> list[TicketDocument]: ...

    async def insert(self, document: TicketDocument) -> TicketDocument: ...

    async def update(self, document: TicketDocument) -> TicketDocument: ...

    async def max_sequence_for_year(self, year: int) -> int: ...


class InMemoryTicketRepository:
    """In-memory ticket store for tests."""

    def __init__(self, tickets: Iterable[TicketDocument] | None = None) -> None:
        self._tickets: dict[str, TicketDocument] = {}
        if tickets:
            for ticket in tickets:
                self._tickets[ticket.ticket_id] = ticket

    async def find_by_id(self, ticket_id: str) -> TicketDocument | None:
        return self._tickets.get(ticket_id)

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[TicketDocument]:
        matches = [
            ticket
            for ticket in self._tickets.values()
            if ticket.customer_id == customer_id
        ]
        matches.sort(key=lambda t: t.created_at, reverse=True)
        return matches[:limit]

    async def list_human_review_queue(
        self,
        *,
        priority: str | None = None,
    ) -> list[TicketDocument]:
        matches = [
            ticket
            for ticket in self._tickets.values()
            if ticket.ticket_class == "human_review"
            and ticket.status in HUMAN_REVIEW_QUEUE_STATUSES
        ]
        if priority is not None:
            matches = [ticket for ticket in matches if ticket.priority == priority]
        matches.sort(key=lambda t: (t.priority, t.created_at))
        return matches

    async def insert(self, document: TicketDocument) -> TicketDocument:
        if document.ticket_id in self._tickets:
            raise ValueError(f"ticket already exists: {document.ticket_id}")
        self._tickets[document.ticket_id] = document
        return document

    async def update(self, document: TicketDocument) -> TicketDocument:
        if document.ticket_id not in self._tickets:
            raise ValueError(f"ticket not found: {document.ticket_id}")
        self._tickets[document.ticket_id] = document
        return document

    async def max_sequence_for_year(self, year: int) -> int:
        max_seq = 0
        for ticket_id in self._tickets:
            try:
                ticket_year, sequence = parse_ticket_id(ticket_id)
            except ValueError:
                continue
            if ticket_year == year:
                max_seq = max(max_seq, sequence)
        return max_seq


class MongoTicketRepository:
    """MongoDB-backed ticket persistence (T-021)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def find_by_id(self, ticket_id: str) -> TicketDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                document = database[TICKETS_COLLECTION].find_one({"ticket_id": ticket_id})
                if document is None:
                    return None
                return _document_from_mongo(document)
        except (SeedMongoError, ValidationError):
            return None

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[TicketDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[TICKETS_COLLECTION]
                    .find({"customer_id": customer_id})
                    .sort("created_at", -1)
                    .limit(limit)
                )
                return [_document_from_mongo(doc) for doc in cursor]
        except (SeedMongoError, ValidationError):
            return []

    async def list_human_review_queue(
        self,
        *,
        priority: str | None = None,
    ) -> list[TicketDocument]:
        query: dict[str, Any] = {
            "ticket_class": "human_review",
            "status": {"$in": list(HUMAN_REVIEW_QUEUE_STATUSES)},
        }
        if priority is not None:
            query["priority"] = priority
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = database[TICKETS_COLLECTION].find(query).sort(
                    [("priority", 1), ("created_at", 1)]
                )
                return [_document_from_mongo(doc) for doc in cursor]
        except (SeedMongoError, ValidationError):
            return []

    async def insert(self, document: TicketDocument) -> TicketDocument:
        with seed_mongo_session(self._settings) as (_client, database):
            database[TICKETS_COLLECTION].insert_one(document.to_mongo_dict())
        return document

    async def update(self, document: TicketDocument) -> TicketDocument:
        with seed_mongo_session(self._settings) as (_client, database):
            result = database[TICKETS_COLLECTION].replace_one(
                {"ticket_id": document.ticket_id},
                document.to_mongo_dict(),
            )
            if result.matched_count == 0:
                raise ValueError(f"ticket not found: {document.ticket_id}")
        return document

    async def max_sequence_for_year(self, year: int) -> int:
        prefix = f"TKT-{year}-"
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[TICKETS_COLLECTION]
                    .find({"ticket_id": {"$regex": f"^{prefix}"}})
                    .sort("ticket_id", -1)
                    .limit(1)
                )
                documents = list(cursor)
                if not documents:
                    return 0
                _year, sequence = parse_ticket_id(documents[0]["ticket_id"])
                return sequence
        except (SeedMongoError, ValidationError, ValueError):
            return 0


def _document_from_mongo(document: dict[str, Any]) -> TicketDocument:
    """Build TicketDocument from a MongoDB record."""
    payload = dict(document)
    payload.pop("_id", None)
    return TicketDocument.model_validate(payload)
