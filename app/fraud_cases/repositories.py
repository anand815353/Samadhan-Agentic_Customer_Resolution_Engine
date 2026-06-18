"""Fraud case repository ports and local implementations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from pydantic import ValidationError

from app.core.config import Settings
from app.fraud_cases.constants import FRAUD_CASES_COLLECTION
from app.fraud_cases.id_generation import parse_fraud_case_id
from app.fraud_cases.models import FraudCaseDocument
from app.seed.mongo import SeedMongoError, seed_mongo_session


class FraudCaseRepository(Protocol):
    """Fraud case persistence contract."""

    async def insert(self, document: FraudCaseDocument) -> FraudCaseDocument: ...

    async def find_by_id(self, fraud_case_id: str) -> FraudCaseDocument | None: ...

    async def find_by_ticket(self, ticket_id: str) -> FraudCaseDocument | None: ...

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[FraudCaseDocument]: ...

    async def max_sequence_for_year(self, year: int) -> int: ...


def _sort_key_datetime(value: object) -> str:
    return str(value)


class InMemoryFraudCaseRepository:
    """In-memory fraud case store for tests."""

    def __init__(self, documents: Iterable[FraudCaseDocument] | None = None) -> None:
        self._documents: dict[str, FraudCaseDocument] = {}
        if documents:
            for document in documents:
                self._documents[document.fraud_case_id] = document

    async def insert(self, document: FraudCaseDocument) -> FraudCaseDocument:
        if document.fraud_case_id in self._documents:
            raise ValueError(f"fraud case already exists: {document.fraud_case_id}")
        self._documents[document.fraud_case_id] = document
        return document

    async def find_by_id(self, fraud_case_id: str) -> FraudCaseDocument | None:
        return self._documents.get(fraud_case_id)

    async def find_by_ticket(self, ticket_id: str) -> FraudCaseDocument | None:
        for document in self._documents.values():
            if document.ticket_id == ticket_id:
                return document
        return None

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[FraudCaseDocument]:
        matches = [
            document
            for document in self._documents.values()
            if document.customer_id == customer_id
        ]
        matches.sort(key=lambda document: _sort_key_datetime(document.created_at), reverse=True)
        return matches[:limit]

    async def max_sequence_for_year(self, year: int) -> int:
        max_seq = 0
        for fraud_case_id in self._documents:
            try:
                case_year, sequence = parse_fraud_case_id(fraud_case_id)
            except ValueError:
                continue
            if case_year == year:
                max_seq = max(max_seq, sequence)
        return max_seq


class MongoFraudCaseRepository:
    """MongoDB-backed fraud case persistence."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def insert(self, document: FraudCaseDocument) -> FraudCaseDocument:
        with seed_mongo_session(self._settings) as (_client, database):
            database[FRAUD_CASES_COLLECTION].insert_one(document.to_mongo_dict())
        return document

    async def find_by_id(self, fraud_case_id: str) -> FraudCaseDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                document = database[FRAUD_CASES_COLLECTION].find_one(
                    {"fraud_case_id": fraud_case_id}
                )
                if document is None:
                    return None
                return _fraud_case_from_mongo(document)
        except (SeedMongoError, ValidationError):
            return None

    async def find_by_ticket(self, ticket_id: str) -> FraudCaseDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                document = database[FRAUD_CASES_COLLECTION].find_one({"ticket_id": ticket_id})
                if document is None:
                    return None
                return _fraud_case_from_mongo(document)
        except (SeedMongoError, ValidationError):
            return None

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[FraudCaseDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[FRAUD_CASES_COLLECTION]
                    .find({"customer_id": customer_id})
                    .sort("created_at", -1)
                    .limit(limit)
                )
                return [_fraud_case_from_mongo(doc) for doc in cursor]
        except (SeedMongoError, ValidationError):
            return []

    async def max_sequence_for_year(self, year: int) -> int:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = database[FRAUD_CASES_COLLECTION].find(
                    {"fraud_case_id": {"$regex": f"^FRD-{year}-"}},
                    {"fraud_case_id": 1},
                )
                max_seq = 0
                for document in cursor:
                    fraud_case_id = document.get("fraud_case_id")
                    if not isinstance(fraud_case_id, str):
                        continue
                    try:
                        case_year, sequence = parse_fraud_case_id(fraud_case_id)
                    except ValueError:
                        continue
                    if case_year == year:
                        max_seq = max(max_seq, sequence)
                return max_seq
        except SeedMongoError:
            return 0


def _fraud_case_from_mongo(document: dict[str, Any]) -> FraudCaseDocument:
    payload = dict(document)
    payload.pop("_id", None)
    return FraudCaseDocument.model_validate(payload)
