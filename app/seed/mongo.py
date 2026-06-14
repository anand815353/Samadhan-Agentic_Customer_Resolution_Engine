"""Sync MongoDB helpers for demo seed reset/upsert (T-015)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from pymongo import MongoClient, ReplaceOne
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.core.config import Settings
from app.seed.template_spec import demo_seed_collections


class SeedMongoError(Exception):
    """Seed-time MongoDB configuration or connectivity failure."""


def _require_mongo_settings(settings: Settings) -> None:
    if not settings.mongodb_uri.strip():
        raise SeedMongoError(
            "MongoDB is not configured; set MONGODB_URI in the environment or .env file."
        )
    if not settings.mongodb_db_name.strip():
        raise SeedMongoError(
            "MongoDB database name is not configured; set MONGODB_DB_NAME."
        )


@contextmanager
def seed_mongo_session(settings: Settings) -> Iterator[tuple[MongoClient, Database]]:
    """Open a short-lived Mongo client for seed operations."""
    _require_mongo_settings(settings)
    client = MongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=5000,
    )
    try:
        client.server_info()
    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        client.close()
        raise SeedMongoError(
            "Could not connect to MongoDB; ensure the server is running and "
            "MONGODB_URI is correct."
        ) from exc

    database = client[settings.mongodb_db_name]
    try:
        yield client, database
    finally:
        client.close()


def reset_demo_collections(database: Database) -> dict[str, int]:
    """Delete all documents from configured demo collections only."""
    deleted: dict[str, int] = {}
    for collection_name in demo_seed_collections():
        result = database[collection_name].delete_many({})
        deleted[collection_name] = result.deleted_count
    return deleted


def upsert_documents(
    collection: Collection,
    documents: list[dict[str, Any]],
    id_field: str,
) -> tuple[int, int]:
    """Upsert documents by stable ID field; return (inserted, updated) counts."""
    if not documents:
        return 0, 0

    operations = [
        ReplaceOne({id_field: document[id_field]}, document, upsert=True)
        for document in documents
        if id_field in document
    ]
    if not operations:
        return 0, 0

    result = collection.bulk_write(operations, ordered=True)
    inserted = result.upserted_count
    updated = result.modified_count
    return inserted, updated
