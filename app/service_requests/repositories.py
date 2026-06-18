"""Service request repository port and local implementations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from pydantic import ValidationError

from app.core.config import Settings
from app.seed.mongo import SeedMongoError, seed_mongo_session
from app.service_requests.constants import SERVICE_REQUESTS_COLLECTION
from app.service_requests.id_generation import parse_service_request_id
from app.service_requests.models import ServiceRequestDocument


class ServiceRequestRepository(Protocol):
    """Service request persistence contract."""

    async def insert(self, document: ServiceRequestDocument) -> ServiceRequestDocument: ...

    async def update(self, document: ServiceRequestDocument) -> ServiceRequestDocument: ...

    async def delete(self, service_request_id: str) -> bool: ...

    async def find_by_id(self, service_request_id: str) -> ServiceRequestDocument | None: ...

    async def find_by_ticket(self, ticket_id: str) -> ServiceRequestDocument | None: ...

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[ServiceRequestDocument]: ...

    async def max_sequence_for_year(self, year: int) -> int: ...


class InMemoryServiceRequestRepository:
    """In-memory service request store for tests."""

    def __init__(self, documents: Iterable[ServiceRequestDocument] | None = None) -> None:
        self._documents: dict[str, ServiceRequestDocument] = {}
        if documents:
            for document in documents:
                self._documents[document.service_request_id] = document

    async def insert(self, document: ServiceRequestDocument) -> ServiceRequestDocument:
        if document.service_request_id in self._documents:
            raise ValueError(f"service request already exists: {document.service_request_id}")
        self._documents[document.service_request_id] = document
        return document

    async def update(self, document: ServiceRequestDocument) -> ServiceRequestDocument:
        if document.service_request_id not in self._documents:
            raise ValueError(f"service request not found: {document.service_request_id}")
        self._documents[document.service_request_id] = document
        return document

    async def delete(self, service_request_id: str) -> bool:
        if service_request_id not in self._documents:
            return False
        del self._documents[service_request_id]
        return True

    async def find_by_id(self, service_request_id: str) -> ServiceRequestDocument | None:
        return self._documents.get(service_request_id)

    async def find_by_ticket(self, ticket_id: str) -> ServiceRequestDocument | None:
        for document in self._documents.values():
            if document.ticket_id == ticket_id:
                return document
        return None

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[ServiceRequestDocument]:
        matches = [
            document
            for document in self._documents.values()
            if document.customer_id == customer_id
        ]
        matches.sort(key=lambda document: document.created_at, reverse=True)
        return matches[:limit]

    async def max_sequence_for_year(self, year: int) -> int:
        max_seq = 0
        for service_request_id in self._documents:
            try:
                sr_year, sequence = parse_service_request_id(service_request_id)
            except ValueError:
                continue
            if sr_year == year:
                max_seq = max(max_seq, sequence)
        return max_seq


class MongoServiceRequestRepository:
    """MongoDB-backed service request persistence (T-023)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def insert(self, document: ServiceRequestDocument) -> ServiceRequestDocument:
        with seed_mongo_session(self._settings) as (_client, database):
            database[SERVICE_REQUESTS_COLLECTION].insert_one(document.to_mongo_dict())
        return document

    async def update(self, document: ServiceRequestDocument) -> ServiceRequestDocument:
        with seed_mongo_session(self._settings) as (_client, database):
            result = database[SERVICE_REQUESTS_COLLECTION].replace_one(
                {"service_request_id": document.service_request_id},
                document.to_mongo_dict(),
            )
            if result.matched_count == 0:
                raise ValueError(f"service request not found: {document.service_request_id}")
        return document

    async def delete(self, service_request_id: str) -> bool:
        with seed_mongo_session(self._settings) as (_client, database):
            result = database[SERVICE_REQUESTS_COLLECTION].delete_one(
                {"service_request_id": service_request_id}
            )
            return result.deleted_count > 0

    async def find_by_id(self, service_request_id: str) -> ServiceRequestDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                record = database[SERVICE_REQUESTS_COLLECTION].find_one(
                    {"service_request_id": service_request_id}
                )
                if record is None:
                    return None
                return _document_from_mongo(record)
        except (SeedMongoError, ValidationError):
            return None

    async def find_by_ticket(self, ticket_id: str) -> ServiceRequestDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                record = database[SERVICE_REQUESTS_COLLECTION].find_one({"ticket_id": ticket_id})
                if record is None:
                    return None
                return _document_from_mongo(record)
        except (SeedMongoError, ValidationError):
            return None

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[ServiceRequestDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[SERVICE_REQUESTS_COLLECTION]
                    .find({"customer_id": customer_id})
                    .sort("created_at", -1)
                    .limit(limit)
                )
                return [_document_from_mongo(record) for record in cursor]
        except (SeedMongoError, ValidationError):
            return []

    async def max_sequence_for_year(self, year: int) -> int:
        prefix = f"SR-{year}-"
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[SERVICE_REQUESTS_COLLECTION]
                    .find({"service_request_id": {"$regex": f"^{prefix}"}})
                    .sort("service_request_id", -1)
                    .limit(1)
                )
                records = list(cursor)
                if not records:
                    return 0
                _year, sequence = parse_service_request_id(records[0]["service_request_id"])
                return sequence
        except (SeedMongoError, ValidationError, ValueError):
            return 0


def _document_from_mongo(document: dict[str, Any]) -> ServiceRequestDocument:
    """Build ServiceRequestDocument from a MongoDB record."""
    payload = dict(document)
    payload.pop("_id", None)
    return ServiceRequestDocument.model_validate(payload)
