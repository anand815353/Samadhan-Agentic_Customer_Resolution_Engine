"""Offer repository ports and local implementations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from pydantic import ValidationError

from app.core.config import Settings
from app.offers.constants import OFFERS_COLLECTION
from app.offers.models import OfferDocument
from app.seed.mongo import SeedMongoError, seed_mongo_session


class OfferRepository(Protocol):
    """Offer persistence contract."""

    async def find_by_id(self, offer_id: str) -> OfferDocument | None: ...

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 20,
    ) -> list[OfferDocument]: ...

    async def update(self, document: OfferDocument) -> OfferDocument: ...


def _sort_key_datetime(value: object) -> str:
    return str(value)


class InMemoryOfferRepository:
    """In-memory offer store for tests."""

    def __init__(self, documents: Iterable[OfferDocument] | None = None) -> None:
        self._documents: dict[str, OfferDocument] = {}
        if documents:
            for document in documents:
                self._documents[document.offer_id] = document

    async def find_by_id(self, offer_id: str) -> OfferDocument | None:
        return self._documents.get(offer_id)

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 20,
    ) -> list[OfferDocument]:
        matches = [
            document
            for document in self._documents.values()
            if document.customer_id == customer_id
        ]
        matches.sort(key=lambda document: _sort_key_datetime(document.created_at), reverse=True)
        return matches[:limit]

    async def update(self, document: OfferDocument) -> OfferDocument:
        if document.offer_id not in self._documents:
            raise ValueError(f"offer not found: {document.offer_id}")
        self._documents[document.offer_id] = document
        return document


class MongoOfferRepository:
    """MongoDB-backed offer persistence."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def find_by_id(self, offer_id: str) -> OfferDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                document = database[OFFERS_COLLECTION].find_one({"offer_id": offer_id})
                if document is None:
                    return None
                return _offer_from_mongo(document)
        except (SeedMongoError, ValidationError):
            return None

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 20,
    ) -> list[OfferDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[OFFERS_COLLECTION]
                    .find({"customer_id": customer_id})
                    .sort("created_at", -1)
                    .limit(limit)
                )
                return [_offer_from_mongo(doc) for doc in cursor]
        except (SeedMongoError, ValidationError):
            return []

    async def update(self, document: OfferDocument) -> OfferDocument:
        with seed_mongo_session(self._settings) as (_client, database):
            database[OFFERS_COLLECTION].replace_one(
                {"offer_id": document.offer_id},
                document.to_mongo_dict(),
                upsert=False,
            )
        return document


def _offer_from_mongo(document: dict[str, Any]) -> OfferDocument:
    payload = dict(document)
    payload.pop("_id", None)
    return OfferDocument.model_validate(payload)
