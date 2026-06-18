"""Bureau reporting log repository ports and local implementations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from pydantic import ValidationError

from app.bureau.constants import BUREAU_REPORTING_LOGS_COLLECTION
from app.bureau.models import BureauReportingLogDocument
from app.core.config import Settings
from app.seed.mongo import SeedMongoError, seed_mongo_session


class BureauReportingLogRepository(Protocol):
    """Bureau reporting log read persistence contract."""

    async def find_by_id(self, bureau_log_id: str) -> BureauReportingLogDocument | None: ...

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 20,
    ) -> list[BureauReportingLogDocument]: ...

    async def find_by_loan(
        self,
        loan_id: str,
        *,
        limit: int = 20,
    ) -> list[BureauReportingLogDocument]: ...


def _reporting_month_key(document: BureauReportingLogDocument) -> str:
    return document.reporting_month


class InMemoryBureauReportingLogRepository:
    """In-memory bureau reporting log store for tests."""

    def __init__(self, documents: Iterable[BureauReportingLogDocument] | None = None) -> None:
        self._documents: dict[str, BureauReportingLogDocument] = {}
        if documents:
            for document in documents:
                self._documents[document.bureau_log_id] = document

    async def find_by_id(self, bureau_log_id: str) -> BureauReportingLogDocument | None:
        return self._documents.get(bureau_log_id)

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 20,
    ) -> list[BureauReportingLogDocument]:
        matches = [
            document
            for document in self._documents.values()
            if document.customer_id == customer_id
        ]
        matches.sort(key=_reporting_month_key, reverse=True)
        return matches[:limit]

    async def find_by_loan(
        self,
        loan_id: str,
        *,
        limit: int = 20,
    ) -> list[BureauReportingLogDocument]:
        matches = [
            document
            for document in self._documents.values()
            if document.loan_id == loan_id
        ]
        matches.sort(key=_reporting_month_key, reverse=True)
        return matches[:limit]


class MongoBureauReportingLogRepository:
    """MongoDB-backed bureau reporting log reads."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def find_by_id(self, bureau_log_id: str) -> BureauReportingLogDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                document = database[BUREAU_REPORTING_LOGS_COLLECTION].find_one(
                    {"bureau_log_id": bureau_log_id}
                )
                if document is None:
                    return None
                return _bureau_log_from_mongo(document)
        except (SeedMongoError, ValidationError):
            return None

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 20,
    ) -> list[BureauReportingLogDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[BUREAU_REPORTING_LOGS_COLLECTION]
                    .find({"customer_id": customer_id})
                    .sort("reporting_month", -1)
                    .limit(limit)
                )
                return [_bureau_log_from_mongo(doc) for doc in cursor]
        except (SeedMongoError, ValidationError):
            return []

    async def find_by_loan(
        self,
        loan_id: str,
        *,
        limit: int = 20,
    ) -> list[BureauReportingLogDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[BUREAU_REPORTING_LOGS_COLLECTION]
                    .find({"loan_id": loan_id})
                    .sort("reporting_month", -1)
                    .limit(limit)
                )
                return [_bureau_log_from_mongo(doc) for doc in cursor]
        except (SeedMongoError, ValidationError):
            return []


def _bureau_log_from_mongo(document: dict[str, Any]) -> BureauReportingLogDocument:
    payload = dict(document)
    payload.pop("_id", None)
    return BureauReportingLogDocument.model_validate(payload)
