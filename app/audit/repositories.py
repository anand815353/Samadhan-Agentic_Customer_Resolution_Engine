"""Audit log repository port and local implementations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from pydantic import ValidationError

from app.audit.constants import AUDIT_LOGS_COLLECTION, AuditEventType
from app.audit.id_generation import parse_audit_id
from app.audit.models import AuditLogDocument
from app.core.config import Settings
from app.seed.mongo import SeedMongoError, seed_mongo_session


class AuditLogRepository(Protocol):
    """Audit log persistence contract."""

    async def insert(self, document: AuditLogDocument) -> AuditLogDocument: ...

    async def find_by_id(self, audit_id: str) -> AuditLogDocument | None: ...

    async def find_by_ticket(
        self,
        ticket_id: str,
        *,
        limit: int = 200,
    ) -> list[AuditLogDocument]: ...

    async def find_by_message(
        self,
        message_id: str,
        *,
        limit: int = 50,
    ) -> list[AuditLogDocument]: ...

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[AuditLogDocument]: ...

    async def find_by_event_type(
        self,
        event_type: AuditEventType,
        *,
        limit: int = 100,
    ) -> list[AuditLogDocument]: ...

    async def find_by_workflow_id(
        self,
        workflow_id: str,
        *,
        event_type: AuditEventType | None = None,
        limit: int = 10,
    ) -> list[AuditLogDocument]: ...

    async def max_sequence_for_year(self, year: int) -> int: ...


class InMemoryAuditLogRepository:
    """In-memory audit log store for tests."""

    def __init__(self, documents: Iterable[AuditLogDocument] | None = None) -> None:
        self._documents: dict[str, AuditLogDocument] = {}
        if documents:
            for document in documents:
                self._documents[document.audit_id] = document

    async def insert(self, document: AuditLogDocument) -> AuditLogDocument:
        if document.audit_id in self._documents:
            raise ValueError(f"audit event already exists: {document.audit_id}")
        self._documents[document.audit_id] = document
        return document

    async def find_by_id(self, audit_id: str) -> AuditLogDocument | None:
        return self._documents.get(audit_id)

    async def find_by_ticket(
        self,
        ticket_id: str,
        *,
        limit: int = 200,
    ) -> list[AuditLogDocument]:
        matches = [
            document
            for document in self._documents.values()
            if document.ticket_id == ticket_id
        ]
        matches.sort(key=lambda document: document.created_at, reverse=True)
        return matches[:limit]

    async def find_by_message(
        self,
        message_id: str,
        *,
        limit: int = 50,
    ) -> list[AuditLogDocument]:
        matches = [
            document
            for document in self._documents.values()
            if document.message_id == message_id
        ]
        matches.sort(key=lambda document: document.created_at, reverse=True)
        return matches[:limit]

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[AuditLogDocument]:
        matches = [
            document
            for document in self._documents.values()
            if document.customer_id == customer_id
        ]
        matches.sort(key=lambda document: document.created_at, reverse=True)
        return matches[:limit]

    async def find_by_event_type(
        self,
        event_type: AuditEventType,
        *,
        limit: int = 100,
    ) -> list[AuditLogDocument]:
        matches = [
            document
            for document in self._documents.values()
            if document.event_type == event_type
        ]
        matches.sort(key=lambda document: document.created_at, reverse=True)
        return matches[:limit]

    async def find_by_workflow_id(
        self,
        workflow_id: str,
        *,
        event_type: AuditEventType | None = None,
        limit: int = 10,
    ) -> list[AuditLogDocument]:
        matches = [
            document
            for document in self._documents.values()
            if document.workflow_id == workflow_id
            and (event_type is None or document.event_type == event_type)
        ]
        matches.sort(key=lambda document: document.created_at, reverse=True)
        return matches[:limit]

    async def max_sequence_for_year(self, year: int) -> int:
        max_seq = 0
        for audit_id in self._documents:
            try:
                audit_year, sequence = parse_audit_id(audit_id)
            except ValueError:
                continue
            if audit_year == year:
                max_seq = max(max_seq, sequence)
        return max_seq


class MongoAuditLogRepository:
    """MongoDB-backed audit log persistence (T-024)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def insert(self, document: AuditLogDocument) -> AuditLogDocument:
        with seed_mongo_session(self._settings) as (_client, database):
            database[AUDIT_LOGS_COLLECTION].insert_one(document.to_mongo_dict())
        return document

    async def find_by_id(self, audit_id: str) -> AuditLogDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                record = database[AUDIT_LOGS_COLLECTION].find_one({"audit_id": audit_id})
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
    ) -> list[AuditLogDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[AUDIT_LOGS_COLLECTION]
                    .find({"ticket_id": ticket_id})
                    .sort("created_at", -1)
                    .limit(limit)
                )
                return [_document_from_mongo(record) for record in cursor]
        except (SeedMongoError, ValidationError):
            return []

    async def find_by_message(
        self,
        message_id: str,
        *,
        limit: int = 50,
    ) -> list[AuditLogDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[AUDIT_LOGS_COLLECTION]
                    .find({"message_id": message_id})
                    .sort("created_at", -1)
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
    ) -> list[AuditLogDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[AUDIT_LOGS_COLLECTION]
                    .find({"customer_id": customer_id})
                    .sort("created_at", -1)
                    .limit(limit)
                )
                return [_document_from_mongo(record) for record in cursor]
        except (SeedMongoError, ValidationError):
            return []

    async def find_by_event_type(
        self,
        event_type: AuditEventType,
        *,
        limit: int = 100,
    ) -> list[AuditLogDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[AUDIT_LOGS_COLLECTION]
                    .find({"event_type": event_type})
                    .sort("created_at", -1)
                    .limit(limit)
                )
                return [_document_from_mongo(record) for record in cursor]
        except (SeedMongoError, ValidationError):
            return []

    async def find_by_workflow_id(
        self,
        workflow_id: str,
        *,
        event_type: AuditEventType | None = None,
        limit: int = 10,
    ) -> list[AuditLogDocument]:
        query: dict[str, Any] = {"workflow_id": workflow_id}
        if event_type is not None:
            query["event_type"] = event_type
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[AUDIT_LOGS_COLLECTION]
                    .find(query)
                    .sort("created_at", -1)
                    .limit(limit)
                )
                return [_document_from_mongo(record) for record in cursor]
        except (SeedMongoError, ValidationError):
            return []

    async def max_sequence_for_year(self, year: int) -> int:
        prefix = f"AUD-{year}-"
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[AUDIT_LOGS_COLLECTION]
                    .find({"audit_id": {"$regex": f"^{prefix}"}})
                    .sort("audit_id", -1)
                    .limit(1)
                )
                records = list(cursor)
                if not records:
                    return 0
                _year, sequence = parse_audit_id(records[0]["audit_id"])
                return sequence
        except (SeedMongoError, ValidationError, ValueError):
            return 0


def _document_from_mongo(document: dict[str, Any]) -> AuditLogDocument:
    """Build AuditLogDocument from a MongoDB record."""
    payload = dict(document)
    payload.pop("_id", None)
    return AuditLogDocument.model_validate(payload)
