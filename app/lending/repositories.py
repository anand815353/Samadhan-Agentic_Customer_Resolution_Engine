"""Lending repository ports and local implementations."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any, Protocol

from pydantic import ValidationError

from app.core.config import Settings
from app.lending.constants import LOAN_APPLICATIONS_COLLECTION, LOANS_COLLECTION
from app.lending.models import LoanApplicationDocument, LoanDocument
from app.seed.mongo import SeedMongoError, seed_mongo_session


class LoanApplicationRepository(Protocol):
    """Loan application read persistence contract."""

    async def find_by_id(self, application_id: str) -> LoanApplicationDocument | None: ...

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 20,
    ) -> list[LoanApplicationDocument]: ...


class LoanRepository(Protocol):
    """Loan account read persistence contract."""

    async def find_by_id(self, loan_id: str) -> LoanDocument | None: ...

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 20,
    ) -> list[LoanDocument]: ...


def _sort_key_datetime(value: datetime | str) -> str:
    return str(value)


class InMemoryLoanApplicationRepository:
    """In-memory loan application store for tests."""

    def __init__(self, documents: Iterable[LoanApplicationDocument] | None = None) -> None:
        self._documents: dict[str, LoanApplicationDocument] = {}
        if documents:
            for document in documents:
                self._documents[document.application_id] = document

    async def find_by_id(self, application_id: str) -> LoanApplicationDocument | None:
        return self._documents.get(application_id)

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 20,
    ) -> list[LoanApplicationDocument]:
        matches = [
            document
            for document in self._documents.values()
            if document.customer_id == customer_id
        ]
        matches.sort(key=lambda item: _sort_key_datetime(item.last_updated_at), reverse=True)
        return matches[:limit]


class InMemoryLoanRepository:
    """In-memory loan store for tests."""

    def __init__(self, documents: Iterable[LoanDocument] | None = None) -> None:
        self._documents: dict[str, LoanDocument] = {}
        if documents:
            for document in documents:
                self._documents[document.loan_id] = document

    async def find_by_id(self, loan_id: str) -> LoanDocument | None:
        return self._documents.get(loan_id)

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 20,
    ) -> list[LoanDocument]:
        matches = [
            document for document in self._documents.values() if document.customer_id == customer_id
        ]
        matches.sort(key=lambda item: _sort_key_datetime(item.updated_at), reverse=True)
        return matches[:limit]


class MongoLoanApplicationRepository:
    """MongoDB-backed loan application reads."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def find_by_id(self, application_id: str) -> LoanApplicationDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                document = database[LOAN_APPLICATIONS_COLLECTION].find_one(
                    {"application_id": application_id}
                )
                if document is None:
                    return None
                return _application_from_mongo(document)
        except (SeedMongoError, ValidationError):
            return None

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 20,
    ) -> list[LoanApplicationDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[LOAN_APPLICATIONS_COLLECTION]
                    .find({"customer_id": customer_id})
                    .sort("last_updated_at", -1)
                    .limit(limit)
                )
                return [_application_from_mongo(doc) for doc in cursor]
        except (SeedMongoError, ValidationError):
            return []


class MongoLoanRepository:
    """MongoDB-backed loan reads."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def find_by_id(self, loan_id: str) -> LoanDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                document = database[LOANS_COLLECTION].find_one({"loan_id": loan_id})
                if document is None:
                    return None
                return _loan_from_mongo(document)
        except (SeedMongoError, ValidationError):
            return None

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 20,
    ) -> list[LoanDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[LOANS_COLLECTION]
                    .find({"customer_id": customer_id})
                    .sort("updated_at", -1)
                    .limit(limit)
                )
                return [_loan_from_mongo(doc) for doc in cursor]
        except (SeedMongoError, ValidationError):
            return []


def _application_from_mongo(document: dict[str, Any]) -> LoanApplicationDocument:
    payload = dict(document)
    payload.pop("_id", None)
    return LoanApplicationDocument.model_validate(payload)


def _loan_from_mongo(document: dict[str, Any]) -> LoanDocument:
    payload = dict(document)
    payload.pop("_id", None)
    return LoanDocument.model_validate(payload)
