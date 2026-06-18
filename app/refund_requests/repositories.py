"""Refund request repository ports and local implementations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from pydantic import ValidationError

from app.core.config import Settings
from app.refund_requests.constants import REFUND_REQUESTS_COLLECTION
from app.refund_requests.id_generation import parse_refund_request_id
from app.refund_requests.models import RefundRequestDocument
from app.seed.mongo import SeedMongoError, seed_mongo_session


class RefundRequestRepository(Protocol):
    """Refund request persistence contract."""

    async def insert(self, document: RefundRequestDocument) -> RefundRequestDocument: ...

    async def find_by_id(self, refund_request_id: str) -> RefundRequestDocument | None: ...

    async def find_by_ticket(self, ticket_id: str) -> RefundRequestDocument | None: ...

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[RefundRequestDocument]: ...

    async def max_sequence_for_year(self, year: int) -> int: ...


def _sort_key_datetime(value: object) -> str:
    return str(value)


class InMemoryRefundRequestRepository:
    """In-memory refund request store for tests."""

    def __init__(self, documents: Iterable[RefundRequestDocument] | None = None) -> None:
        self._documents: dict[str, RefundRequestDocument] = {}
        if documents:
            for document in documents:
                self._documents[document.refund_request_id] = document

    async def insert(self, document: RefundRequestDocument) -> RefundRequestDocument:
        if document.refund_request_id in self._documents:
            raise ValueError(f"refund request already exists: {document.refund_request_id}")
        self._documents[document.refund_request_id] = document
        return document

    async def find_by_id(self, refund_request_id: str) -> RefundRequestDocument | None:
        return self._documents.get(refund_request_id)

    async def find_by_ticket(self, ticket_id: str) -> RefundRequestDocument | None:
        for document in self._documents.values():
            if document.ticket_id == ticket_id:
                return document
        return None

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[RefundRequestDocument]:
        matches = [
            document
            for document in self._documents.values()
            if document.customer_id == customer_id
        ]
        matches.sort(key=lambda document: _sort_key_datetime(document.created_at), reverse=True)
        return matches[:limit]

    async def max_sequence_for_year(self, year: int) -> int:
        max_seq = 0
        for refund_request_id in self._documents:
            try:
                ref_year, sequence = parse_refund_request_id(refund_request_id)
            except ValueError:
                continue
            if ref_year == year:
                max_seq = max(max_seq, sequence)
        return max_seq


class MongoRefundRequestRepository:
    """MongoDB-backed refund request persistence."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def insert(self, document: RefundRequestDocument) -> RefundRequestDocument:
        with seed_mongo_session(self._settings) as (_client, database):
            database[REFUND_REQUESTS_COLLECTION].insert_one(document.to_mongo_dict())
        return document

    async def find_by_id(self, refund_request_id: str) -> RefundRequestDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                document = database[REFUND_REQUESTS_COLLECTION].find_one(
                    {"refund_request_id": refund_request_id}
                )
                if document is None:
                    return None
                return _refund_request_from_mongo(document)
        except (SeedMongoError, ValidationError):
            return None

    async def find_by_ticket(self, ticket_id: str) -> RefundRequestDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                document = database[REFUND_REQUESTS_COLLECTION].find_one({"ticket_id": ticket_id})
                if document is None:
                    return None
                return _refund_request_from_mongo(document)
        except (SeedMongoError, ValidationError):
            return None

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[RefundRequestDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[REFUND_REQUESTS_COLLECTION]
                    .find({"customer_id": customer_id})
                    .sort("created_at", -1)
                    .limit(limit)
                )
                return [_refund_request_from_mongo(doc) for doc in cursor]
        except (SeedMongoError, ValidationError):
            return []

    async def max_sequence_for_year(self, year: int) -> int:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = database[REFUND_REQUESTS_COLLECTION].find(
                    {"refund_request_id": {"$regex": f"^REF-{year}-"}},
                    {"refund_request_id": 1},
                )
                max_seq = 0
                for document in cursor:
                    refund_request_id = document.get("refund_request_id")
                    if not isinstance(refund_request_id, str):
                        continue
                    try:
                        ref_year, sequence = parse_refund_request_id(refund_request_id)
                    except ValueError:
                        continue
                    if ref_year == year:
                        max_seq = max(max_seq, sequence)
                return max_seq
        except SeedMongoError:
            return 0


def _refund_request_from_mongo(document: dict[str, Any]) -> RefundRequestDocument:
    payload = dict(document)
    payload.pop("_id", None)
    return RefundRequestDocument.model_validate(payload)
