"""Customer repository port and local implementations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from pydantic import ValidationError

from app.core.config import Settings
from app.customers.models import CustomerDocument
from app.seed.mongo import SeedMongoError, seed_mongo_session

CUSTOMERS_COLLECTION = "customers"


class CustomerRepository(Protocol):
    """Customer read persistence contract."""

    async def find_by_id(self, customer_id: str) -> CustomerDocument | None: ...


class InMemoryCustomerRepository:
    """In-memory customer store for tests."""

    def __init__(self, documents: Iterable[CustomerDocument] | None = None) -> None:
        self._documents: dict[str, CustomerDocument] = {}
        if documents:
            for document in documents:
                self._documents[document.customer_id] = document

    async def find_by_id(self, customer_id: str) -> CustomerDocument | None:
        return self._documents.get(customer_id)


class MongoCustomerRepository:
    """MongoDB-backed customer reads."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def find_by_id(self, customer_id: str) -> CustomerDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                document = database[CUSTOMERS_COLLECTION].find_one({"customer_id": customer_id})
                if document is None:
                    return None
                return _customer_from_mongo(document)
        except (SeedMongoError, ValidationError):
            return None


def _customer_from_mongo(document: dict[str, Any]) -> CustomerDocument:
    payload = dict(document)
    payload.pop("_id", None)
    return CustomerDocument.model_validate(payload)
