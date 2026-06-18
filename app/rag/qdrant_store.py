"""Qdrant vector store for policy chunk indexing (T-043).

Uses cosine distance for semantic embeddings. Collection is created on demand with the
active embedding provider dimension; incompatible existing collections fail clearly.
"""

from __future__ import annotations

import asyncio
import math
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlparse

from app.core.config import Settings, get_settings
from app.rag.embedding_schemas import EmbeddedPolicyChunk
from app.rag.indexing_schemas import PolicyVectorPayload

POINT_ID_NAMESPACE = uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479")
ALLOWED_QDRANT_SCHEMES = frozenset({"http", "https"})


class QdrantStoreError(Exception):
    """Raised when Qdrant configuration or indexing operations fail safely."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def validate_qdrant_url(url: str) -> str:
    """Validate Qdrant URL scheme and host; return normalized URL without trailing slash."""
    normalized = url.strip()
    if not normalized:
        raise QdrantStoreError("QDRANT_URL not configured")
    parsed = urlparse(normalized)
    if parsed.scheme not in ALLOWED_QDRANT_SCHEMES:
        raise QdrantStoreError(
            f"unsupported qdrant url scheme: {parsed.scheme or 'missing'}"
        )
    if not parsed.netloc:
        raise QdrantStoreError("qdrant url missing host")
    return normalized.rstrip("/")


def deterministic_point_id(document_id: str, version: str, chunk_index: int) -> str:
    """Build a stable Qdrant point ID from document identity fields."""
    key = f"{document_id}|{version}|{chunk_index}"
    return str(uuid.uuid5(POINT_ID_NAMESPACE, key))


def build_policy_vector_payload(
    chunk: EmbeddedPolicyChunk,
    *,
    indexed_at: datetime,
) -> PolicyVectorPayload:
    """Map an embedded chunk to the Qdrant payload schema."""
    return PolicyVectorPayload(
        document_id=chunk.document_id,
        title=chunk.title,
        document_type=chunk.document_type,
        domain=chunk.domain,
        version=chunk.version,
        effective_date=str(chunk.effective_date),
        approval_status=chunk.approval_status,
        chunk_index=chunk.chunk_index,
        chunk_text=chunk.chunk_text,
        source_filename=chunk.source_filename,
        indexed_at=indexed_at.astimezone(UTC).isoformat(),
        customer_visible=chunk.customer_visible,
        internal_only=chunk.internal_only,
        section_heading=chunk.section_heading,
    )


class PolicyVectorStore(Protocol):
    """Contract for policy vector persistence."""

    async def ensure_collection(self, *, vector_size: int) -> None: ...

    async def delete_document_version(self, document_id: str, version: str) -> int: ...

    async def upsert_policy_chunks(
        self,
        chunks: list[EmbeddedPolicyChunk],
        *,
        indexed_at: datetime,
    ) -> int: ...


class InMemoryPolicyVectorStore:
    """Dict-backed vector store for unit tests."""

    def __init__(self) -> None:
        self._vector_size: int | None = None
        self._points: dict[str, dict[str, Any]] = {}

    async def ensure_collection(self, *, vector_size: int) -> None:
        if self._vector_size is None:
            self._vector_size = vector_size
            return
        if self._vector_size != vector_size:
            raise QdrantStoreError(
                f"collection dimension mismatch: expected {vector_size}, found {self._vector_size}"
            )

    async def delete_document_version(self, document_id: str, version: str) -> int:
        to_delete = [
            point_id
            for point_id, point in self._points.items()
            if point["payload"].get("document_id") == document_id
            and point["payload"].get("version") == version
        ]
        for point_id in to_delete:
            del self._points[point_id]
        return len(to_delete)

    async def upsert_policy_chunks(
        self,
        chunks: list[EmbeddedPolicyChunk],
        *,
        indexed_at: datetime,
    ) -> int:
        if self._vector_size is None:
            raise QdrantStoreError("collection not initialized")
        for chunk in chunks:
            point_id = deterministic_point_id(
                chunk.document_id,
                chunk.version,
                chunk.chunk_index,
            )
            payload = build_policy_vector_payload(chunk, indexed_at=indexed_at)
            self._points[point_id] = {
                "vector": list(chunk.vector),
                "payload": payload.model_dump(),
            }
        return len(chunks)

    def get_point(self, point_id: str) -> dict[str, Any] | None:
        return self._points.get(point_id)

    def list_points(self) -> list[dict[str, Any]]:
        return list(self._points.values())

    def point_count(self) -> int:
        return len(self._points)


class QdrantPolicyVectorStore:
    """Qdrant-backed policy vector store using qdrant-client."""

    def __init__(
        self,
        settings: Settings,
        *,
        client: Any | None = None,
    ) -> None:
        self._settings = settings
        self._client = client
        self._collection_name = settings.qdrant_collection_name

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        from qdrant_client import QdrantClient

        url = validate_qdrant_url(self._settings.qdrant_url)
        api_key = self._settings.qdrant_api_key.get_secret_value()
        kwargs: dict[str, Any] = {"url": url}
        if api_key:
            kwargs["api_key"] = api_key
        self._client = QdrantClient(**kwargs)
        return self._client

    async def ensure_collection(self, *, vector_size: int) -> None:
        await asyncio.to_thread(self._ensure_collection_sync, vector_size)

    async def delete_document_version(self, document_id: str, version: str) -> int:
        return await asyncio.to_thread(
            self._delete_document_version_sync,
            document_id,
            version,
        )

    async def upsert_policy_chunks(
        self,
        chunks: list[EmbeddedPolicyChunk],
        *,
        indexed_at: datetime,
    ) -> int:
        return await asyncio.to_thread(
            self._upsert_policy_chunks_sync,
            chunks,
            indexed_at,
        )

    def _ensure_collection_sync(self, vector_size: int) -> None:
        from qdrant_client import models

        client = self._get_client()
        collection_name = self._collection_name
        if client.collection_exists(collection_name):
            info = client.get_collection(collection_name)
            existing_size = info.config.params.vectors.size
            if existing_size != vector_size:
                raise QdrantStoreError(
                    "collection dimension mismatch: "
                    f"expected {vector_size}, found {existing_size}"
                )
            return

        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )

    def _delete_document_version_sync(self, document_id: str, version: str) -> int:
        from qdrant_client import models

        client = self._get_client()
        selector = models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id),
                    ),
                    models.FieldCondition(
                        key="version",
                        match=models.MatchValue(value=version),
                    ),
                ]
            )
        )
        before = client.count(
            collection_name=self._collection_name,
            count_filter=selector.filter,
            exact=True,
        ).count
        client.delete(
            collection_name=self._collection_name,
            points_selector=selector,
        )
        return before

    def _upsert_policy_chunks_sync(
        self,
        chunks: list[EmbeddedPolicyChunk],
        indexed_at: datetime,
    ) -> int:
        from qdrant_client import models

        if not chunks:
            return 0

        client = self._get_client()
        points = [
            models.PointStruct(
                id=deterministic_point_id(
                    chunk.document_id,
                    chunk.version,
                    chunk.chunk_index,
                ),
                vector=chunk.vector,
                payload=build_policy_vector_payload(chunk, indexed_at=indexed_at).model_dump(),
            )
            for chunk in chunks
        ]
        client.upsert(collection_name=self._collection_name, points=points)
        return len(points)


class PolicyVectorSearchStore(Protocol):
    """Contract for policy vector similarity search."""

    async def search_policy_chunks(
        self,
        *,
        query_vector: list[float],
        top_k: int,
        domain: str | None = None,
        document_id: str | None = None,
        document_type: str | None = None,
        approval_statuses: tuple[str, ...] = ("approved",),
    ) -> tuple[list[tuple[PolicyVectorPayload, float]], list[str]]: ...


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _payload_matches_filters(
    payload: dict[str, Any],
    *,
    domain: str | None,
    document_id: str | None,
    document_type: str | None,
    approval_statuses: tuple[str, ...],
) -> bool:
    if payload.get("approval_status") not in approval_statuses:
        return False
    if domain is not None and payload.get("domain") != domain:
        return False
    if document_id is not None and payload.get("document_id") != document_id:
        return False
    if document_type is not None and payload.get("document_type") != document_type:
        return False
    return True


class InMemoryPolicyVectorSearchStore:
    """In-memory vector search for unit tests."""

    def __init__(self, vector_store: InMemoryPolicyVectorStore | None = None) -> None:
        self._vector_store = vector_store or InMemoryPolicyVectorStore()

    @property
    def vector_store(self) -> InMemoryPolicyVectorStore:
        return self._vector_store

    async def search_policy_chunks(
        self,
        *,
        query_vector: list[float],
        top_k: int,
        domain: str | None = None,
        document_id: str | None = None,
        document_type: str | None = None,
        approval_statuses: tuple[str, ...] = ("approved",),
    ) -> tuple[list[tuple[PolicyVectorPayload, float]], list[str]]:
        warnings: list[str] = []
        scored: list[tuple[PolicyVectorPayload, float]] = []
        for point in self._vector_store.list_points():
            payload_raw = point.get("payload", {})
            if not _payload_matches_filters(
                payload_raw,
                domain=domain,
                document_id=document_id,
                document_type=document_type,
                approval_statuses=approval_statuses,
            ):
                continue
            try:
                payload = PolicyVectorPayload.model_validate(payload_raw)
            except Exception:  # noqa: BLE001 — skip malformed payloads safely
                warnings.append("skipped malformed vector payload")
                continue
            vector = point.get("vector", [])
            if not vector:
                warnings.append("skipped vector payload with empty vector")
                continue
            score = _cosine_similarity(query_vector, vector)
            scored.append((payload, score))
        scored.sort(
            key=lambda item: (-item[1], item[0].document_id, item[0].chunk_index),
        )
        return scored[:top_k], warnings


class QdrantPolicyVectorSearchStore:
    """Qdrant-backed policy vector search."""

    def __init__(
        self,
        settings: Settings,
        *,
        client: Any | None = None,
    ) -> None:
        self._settings = settings
        self._client = client
        self._collection_name = settings.qdrant_collection_name

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        from qdrant_client import QdrantClient

        url = validate_qdrant_url(self._settings.qdrant_url)
        api_key = self._settings.qdrant_api_key.get_secret_value()
        kwargs: dict[str, Any] = {
            "url": url,
            "timeout": self._settings.qdrant_request_timeout_seconds,
        }
        if api_key:
            kwargs["api_key"] = api_key
        self._client = QdrantClient(**kwargs)
        return self._client

    async def search_policy_chunks(
        self,
        *,
        query_vector: list[float],
        top_k: int,
        domain: str | None = None,
        document_id: str | None = None,
        document_type: str | None = None,
        approval_statuses: tuple[str, ...] = ("approved",),
    ) -> tuple[list[tuple[PolicyVectorPayload, float]], list[str]]:
        return await asyncio.to_thread(
            self._search_policy_chunks_sync,
            query_vector,
            top_k,
            domain,
            document_id,
            document_type,
            approval_statuses,
        )

    def _search_policy_chunks_sync(
        self,
        query_vector: list[float],
        top_k: int,
        domain: str | None,
        document_id: str | None,
        document_type: str | None,
        approval_statuses: tuple[str, ...],
    ) -> tuple[list[tuple[PolicyVectorPayload, float]], list[str]]:
        from qdrant_client import models

        client = self._get_client()
        must_conditions: list[models.FieldCondition] = []
        if len(approval_statuses) == 1:
            must_conditions.append(
                models.FieldCondition(
                    key="approval_status",
                    match=models.MatchValue(value=approval_statuses[0]),
                )
            )
        else:
            must_conditions.append(
                models.FieldCondition(
                    key="approval_status",
                    match=models.MatchAny(any=list(approval_statuses)),
                )
            )
        if domain is not None:
            must_conditions.append(
                models.FieldCondition(
                    key="domain",
                    match=models.MatchValue(value=domain),
                )
            )
        if document_id is not None:
            must_conditions.append(
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=document_id),
                )
            )
        if document_type is not None:
            must_conditions.append(
                models.FieldCondition(
                    key="document_type",
                    match=models.MatchValue(value=document_type),
                )
            )

        query_filter = models.Filter(must=must_conditions) if must_conditions else None
        try:
            hits = client.search(
                collection_name=self._collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
        except TimeoutError as exc:
            raise QdrantStoreError("qdrant search timed out") from exc
        except Exception as exc:  # noqa: BLE001 — controlled store boundary
            message = str(exc).lower()
            if "timeout" in message:
                raise QdrantStoreError("qdrant search timed out") from exc
            raise QdrantStoreError("qdrant search failed") from exc

        warnings: list[str] = []
        results: list[tuple[PolicyVectorPayload, float]] = []
        for hit in hits:
            payload_raw = hit.payload or {}
            try:
                payload = PolicyVectorPayload.model_validate(payload_raw)
            except Exception:  # noqa: BLE001
                warnings.append("skipped malformed vector payload")
                continue
            results.append((payload, float(hit.score)))
        return results, warnings


def get_policy_vector_store(
    settings: Settings | None = None,
    *,
    client: Any | None = None,
    store: PolicyVectorStore | None = None,
) -> PolicyVectorStore:
    """Return the configured policy vector store."""
    if store is not None:
        return store
    resolved = settings or get_settings()
    return QdrantPolicyVectorStore(resolved, client=client)


def get_policy_vector_search_store(
    settings: Settings | None = None,
    *,
    client: Any | None = None,
    store: PolicyVectorSearchStore | None = None,
    vector_store: InMemoryPolicyVectorStore | None = None,
) -> PolicyVectorSearchStore:
    """Return the configured policy vector search store."""
    if store is not None:
        return store
    if vector_store is not None:
        return InMemoryPolicyVectorSearchStore(vector_store)
    resolved = settings or get_settings()
    return QdrantPolicyVectorSearchStore(resolved, client=client)
