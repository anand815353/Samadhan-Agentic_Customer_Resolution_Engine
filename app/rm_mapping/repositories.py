"""RM mapping repository ports and local implementations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from pydantic import ValidationError

from app.core.config import Settings
from app.rm_mapping.constants import RM_MAPPING_COLLECTION
from app.rm_mapping.models import RmMappingDocument
from app.seed.mongo import SeedMongoError, seed_mongo_session


class RmMappingRepository(Protocol):
    """RM mapping read persistence contract."""

    async def find_by_id(self, rm_mapping_id: str) -> RmMappingDocument | None: ...

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 5,
    ) -> list[RmMappingDocument]: ...


def _sort_key_datetime(value: object) -> str:
    return str(value)


class InMemoryRmMappingRepository:
    """In-memory RM mapping store for tests."""

    def __init__(self, documents: Iterable[RmMappingDocument] | None = None) -> None:
        self._documents: dict[str, RmMappingDocument] = {}
        if documents:
            for document in documents:
                self._documents[document.rm_mapping_id] = document

    async def find_by_id(self, rm_mapping_id: str) -> RmMappingDocument | None:
        return self._documents.get(rm_mapping_id)

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 5,
    ) -> list[RmMappingDocument]:
        matches = [
            document
            for document in self._documents.values()
            if document.customer_id == customer_id
        ]
        matches.sort(key=lambda document: _sort_key_datetime(document.created_at), reverse=True)
        return matches[:limit]


class MongoRmMappingRepository:
    """MongoDB-backed RM mapping reads."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def find_by_id(self, rm_mapping_id: str) -> RmMappingDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                document = database[RM_MAPPING_COLLECTION].find_one(
                    {"rm_mapping_id": rm_mapping_id}
                )
                if document is None:
                    return None
                return _rm_mapping_from_mongo(document)
        except (SeedMongoError, ValidationError):
            return None

    async def find_by_customer(
        self,
        customer_id: str,
        *,
        limit: int = 5,
    ) -> list[RmMappingDocument]:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                cursor = (
                    database[RM_MAPPING_COLLECTION]
                    .find({"customer_id": customer_id})
                    .sort("created_at", -1)
                    .limit(limit)
                )
                return [_rm_mapping_from_mongo(doc) for doc in cursor]
        except (SeedMongoError, ValidationError):
            return []


def _rm_mapping_from_mongo(document: dict[str, Any]) -> RmMappingDocument:
    payload = dict(document)
    payload.pop("_id", None)
    return RmMappingDocument.model_validate(payload)
