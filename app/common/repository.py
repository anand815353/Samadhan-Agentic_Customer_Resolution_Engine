"""Base repository protocol and abstract class for MongoDB-backed data access."""

from abc import ABC, abstractmethod
from typing import ClassVar, Generic, Protocol, TypeVar

from app.db.types import DatabaseHandle

T = TypeVar("T")


class Repository(Protocol[T]):
    """CRUD contract for domain repositories."""

    async def find_by_id(self, document_id: str) -> T | None: ...

    async def list(self, *, skip: int = 0, limit: int = 100) -> list[T]: ...

    async def insert(self, document: T) -> T: ...

    async def update(self, document_id: str, document: T) -> T: ...

    async def delete(self, document_id: str) -> bool: ...


class BaseRepository(ABC, Generic[T]):
    """Abstract base for MongoDB collection repositories."""

    collection_name: ClassVar[str]

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if "collection_name" not in cls.__dict__:
            raise TypeError(f"{cls.__name__} must define collection_name")

    def __init__(self, database: DatabaseHandle) -> None:
        self._database = database

    @abstractmethod
    async def find_by_id(self, document_id: str) -> T | None:
        raise NotImplementedError

    @abstractmethod
    async def list(self, *, skip: int = 0, limit: int = 100) -> list[T]:
        raise NotImplementedError

    @abstractmethod
    async def insert(self, document: T) -> T:
        raise NotImplementedError

    @abstractmethod
    async def update(self, document_id: str, document: T) -> T:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, document_id: str) -> bool:
        raise NotImplementedError
