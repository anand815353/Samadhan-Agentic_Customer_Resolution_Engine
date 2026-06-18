"""KYC document repository ports and local implementations."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any, Protocol

from pydantic import ValidationError

from app.core.config import Settings
from app.kyc.constants import KYC_DOCUMENTS_COLLECTION
from app.kyc.models import KycDocumentDocument
from app.seed.mongo import SeedMongoError, seed_mongo_session


class KycDocumentRepository(Protocol):
    """KYC document read persistence contract."""

    async def find_by_id(self, kyc_id: str) -> KycDocumentDocument | None: ...

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 20,
    ) -> list[KycDocumentDocument]: ...


def _sort_key_datetime(value: datetime | str | None) -> str:
    if value is None:
        return ""
    return str(value)


def _kyc_recency_key(document: KycDocumentDocument) -> tuple[str, str, str]:
    return (
        _sort_key_datetime(document.reviewed_at),
        _sort_key_datetime(document.uploaded_at),
        _sort_key_datetime(document.created_at),
    )


class InMemoryKycDocumentRepository:
    """In-memory KYC document store for tests."""

    def __init__(self, documents: Iterable[KycDocumentDocument] | None = None) -> None:
        self._documents: dict[str, KycDocumentDocument] = {}
        if documents:
            for document in documents:
                self._documents[document.kyc_id] = document

    async def find_by_id(self, kyc_id: str) -> KycDocumentDocument | None:
        return self._documents.get(kyc_id)

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 20,
    ) -> list[KycDocumentDocument]:
        matches = [
            document
            for document in self._documents.values()
            if document.customer_id == customer_id
        ]
        matches.sort(key=_kyc_recency_key, reverse=True)
        return matches[:limit]


class MongoKycDocumentRepository:
    """MongoDB-backed KYC document reads."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def find_by_id(self, kyc_id: str) -> KycDocumentDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                document = database[KYC_DOCUMENTS_COLLECTION].find_one({"kyc_id": kyc_id})
                if document is None:
                    return None
                return _kyc_from_mongo(document)
        except (SeedMongoError, ValidationError):
            return None

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 20,
    ) -> list[KycDocumentDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[KYC_DOCUMENTS_COLLECTION]
                    .find({"customer_id": customer_id})
                    .sort("reviewed_at", -1)
                    .limit(limit)
                )
                return [_kyc_from_mongo(doc) for doc in cursor]
        except (SeedMongoError, ValidationError):
            return []


def _kyc_from_mongo(document: dict[str, Any]) -> KycDocumentDocument:
    payload = dict(document)
    payload.pop("_id", None)
    return KycDocumentDocument.model_validate(payload)
