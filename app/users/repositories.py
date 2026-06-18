"""User repository port and local implementations for auth and tests."""

from collections.abc import Iterable
from typing import Any, Protocol

from pydantic import ValidationError

from app.core.config import Settings
from app.seed.mongo import SeedMongoError, seed_mongo_session
from app.users.constants import USERS_COLLECTION
from app.users.models import UserDocument


class UserRepository(Protocol):
    """Lookup users by email or user_id for authentication and workflow intake."""

    async def find_by_email(self, email: str) -> UserDocument | None: ...

    async def find_by_user_id(self, user_id: str) -> UserDocument | None: ...


class UnavailableUserRepository:
    """Fail-closed repository when MongoDB is not configured."""

    async def find_by_email(self, email: str) -> UserDocument | None:
        return None

    async def find_by_user_id(self, user_id: str) -> UserDocument | None:
        return None


class InMemoryUserRepository:
    """In-memory user store for tests and local development."""

    def __init__(self, users: Iterable[UserDocument]) -> None:
        self._users_by_email = {user.email: user for user in users}
        self._users_by_id = {user.user_id: user for user in users}

    async def find_by_email(self, email: str) -> UserDocument | None:
        return self._users_by_email.get(email.strip().lower())

    async def find_by_user_id(self, user_id: str) -> UserDocument | None:
        return self._users_by_id.get(user_id)


class MongoUserRepository:
    """MongoDB-backed user lookup for demo seed authentication (T-016)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def find_by_email(self, email: str) -> UserDocument | None:
        normalized_email = email.strip().lower()
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                document = database[USERS_COLLECTION].find_one({"email": normalized_email})
                if document is None:
                    return None
                return _document_from_mongo(document)
        except (SeedMongoError, ValidationError):
            return None

    async def find_by_user_id(self, user_id: str) -> UserDocument | None:
        try:
            with seed_mongo_session(self._settings) as (_client, database):
                document = database[USERS_COLLECTION].find_one({"user_id": user_id})
                if document is None:
                    return None
                return _document_from_mongo(document)
        except (SeedMongoError, ValidationError):
            return None


def _document_from_mongo(document: dict[str, Any]) -> UserDocument:
    """Build UserDocument from a MongoDB record (strip _id, never log secrets)."""
    payload = dict(document)
    payload.pop("_id", None)
    return UserDocument.model_validate(payload)
