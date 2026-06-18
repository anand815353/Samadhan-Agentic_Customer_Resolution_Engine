"""Repayment repository ports and local implementations."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any, Protocol

from pydantic import ValidationError

from app.core.config import Settings
from app.repayments.constants import (
    PAYMENT_TRANSACTIONS_COLLECTION,
    REPAYMENT_SCHEDULE_COLLECTION,
)
from app.repayments.models import PaymentTransactionDocument, RepaymentScheduleDocument
from app.seed.mongo import SeedMongoError, seed_mongo_session


class RepaymentScheduleRepository(Protocol):
    """Repayment schedule read persistence contract."""

    async def find_by_id(self, schedule_id: str) -> RepaymentScheduleDocument | None: ...

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[RepaymentScheduleDocument]: ...

    async def find_by_loan(
        self,
        loan_id: str,
        *,
        limit: int = 50,
    ) -> list[RepaymentScheduleDocument]: ...


class PaymentTransactionRepository(Protocol):
    """Payment transaction read persistence contract."""

    async def find_by_id(self, transaction_id: str) -> PaymentTransactionDocument | None: ...

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[PaymentTransactionDocument]: ...

    async def find_by_loan(
        self,
        loan_id: str,
        *,
        limit: int = 50,
    ) -> list[PaymentTransactionDocument]: ...


def _sort_key_datetime(value: datetime | str | None) -> str:
    if value is None:
        return ""
    return str(value)


def _schedule_due_date_key(document: RepaymentScheduleDocument) -> str:
    return _sort_key_datetime(document.due_date)


def _transaction_date_key(document: PaymentTransactionDocument) -> str:
    return _sort_key_datetime(document.transaction_date)


class InMemoryRepaymentScheduleRepository:
    """In-memory repayment schedule store for tests."""

    def __init__(self, documents: Iterable[RepaymentScheduleDocument] | None = None) -> None:
        self._documents: dict[str, RepaymentScheduleDocument] = {}
        if documents:
            for document in documents:
                self._documents[document.schedule_id] = document

    async def find_by_id(self, schedule_id: str) -> RepaymentScheduleDocument | None:
        return self._documents.get(schedule_id)

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[RepaymentScheduleDocument]:
        matches = [
            document
            for document in self._documents.values()
            if document.customer_id == customer_id
        ]
        matches.sort(key=_schedule_due_date_key, reverse=True)
        return matches[:limit]

    async def find_by_loan(
        self,
        loan_id: str,
        *,
        limit: int = 50,
    ) -> list[RepaymentScheduleDocument]:
        matches = [
            document for document in self._documents.values() if document.loan_id == loan_id
        ]
        matches.sort(key=_schedule_due_date_key, reverse=True)
        return matches[:limit]


class InMemoryPaymentTransactionRepository:
    """In-memory payment transaction store for tests."""

    def __init__(self, documents: Iterable[PaymentTransactionDocument] | None = None) -> None:
        self._documents: dict[str, PaymentTransactionDocument] = {}
        if documents:
            for document in documents:
                self._documents[document.transaction_id] = document

    async def find_by_id(self, transaction_id: str) -> PaymentTransactionDocument | None:
        return self._documents.get(transaction_id)

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[PaymentTransactionDocument]:
        matches = [
            document
            for document in self._documents.values()
            if document.customer_id == customer_id
        ]
        matches.sort(key=_transaction_date_key, reverse=True)
        return matches[:limit]

    async def find_by_loan(
        self,
        loan_id: str,
        *,
        limit: int = 50,
    ) -> list[PaymentTransactionDocument]:
        matches = [
            document for document in self._documents.values() if document.loan_id == loan_id
        ]
        matches.sort(key=_transaction_date_key, reverse=True)
        return matches[:limit]


class MongoRepaymentScheduleRepository:
    """MongoDB-backed repayment schedule reads."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def find_by_id(self, schedule_id: str) -> RepaymentScheduleDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                document = database[REPAYMENT_SCHEDULE_COLLECTION].find_one(
                    {"schedule_id": schedule_id}
                )
                if document is None:
                    return None
                return _schedule_from_mongo(document)
        except (SeedMongoError, ValidationError):
            return None

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[RepaymentScheduleDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[REPAYMENT_SCHEDULE_COLLECTION]
                    .find({"customer_id": customer_id})
                    .sort("due_date", -1)
                    .limit(limit)
                )
                return [_schedule_from_mongo(doc) for doc in cursor]
        except (SeedMongoError, ValidationError):
            return []

    async def find_by_loan(
        self,
        loan_id: str,
        *,
        limit: int = 50,
    ) -> list[RepaymentScheduleDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[REPAYMENT_SCHEDULE_COLLECTION]
                    .find({"loan_id": loan_id})
                    .sort("due_date", -1)
                    .limit(limit)
                )
                return [_schedule_from_mongo(doc) for doc in cursor]
        except (SeedMongoError, ValidationError):
            return []


class MongoPaymentTransactionRepository:
    """MongoDB-backed payment transaction reads."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def find_by_id(self, transaction_id: str) -> PaymentTransactionDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                document = database[PAYMENT_TRANSACTIONS_COLLECTION].find_one(
                    {"transaction_id": transaction_id}
                )
                if document is None:
                    return None
                return _transaction_from_mongo(document)
        except (SeedMongoError, ValidationError):
            return None

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[PaymentTransactionDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[PAYMENT_TRANSACTIONS_COLLECTION]
                    .find({"customer_id": customer_id})
                    .sort("transaction_date", -1)
                    .limit(limit)
                )
                return [_transaction_from_mongo(doc) for doc in cursor]
        except (SeedMongoError, ValidationError):
            return []

    async def find_by_loan(
        self,
        loan_id: str,
        *,
        limit: int = 50,
    ) -> list[PaymentTransactionDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[PAYMENT_TRANSACTIONS_COLLECTION]
                    .find({"loan_id": loan_id})
                    .sort("transaction_date", -1)
                    .limit(limit)
                )
                return [_transaction_from_mongo(doc) for doc in cursor]
        except (SeedMongoError, ValidationError):
            return []


def _schedule_from_mongo(document: dict[str, Any]) -> RepaymentScheduleDocument:
    payload = dict(document)
    payload.pop("_id", None)
    return RepaymentScheduleDocument.model_validate(payload)


def _transaction_from_mongo(document: dict[str, Any]) -> PaymentTransactionDocument:
    payload = dict(document)
    payload.pop("_id", None)
    return PaymentTransactionDocument.model_validate(payload)
