"""Qdrant-backed policy retrieval service (T-044)."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.providers.base_embedding import EmbeddingProvider, get_embedding_provider
from app.rag.constants import ALL_POLICY_DOMAINS, INTENT_TO_POLICY_DOMAIN
from app.rag.indexing_schemas import PolicyVectorPayload
from app.rag.qdrant_store import (
    PolicyVectorSearchStore,
    QdrantStoreError,
    get_policy_vector_search_store,
)
from app.rag.retrieval import RetrievalServiceError
from app.rag.schemas import RetrievedPolicyChunk, RetrievalRequest, RetrievalResult

_CUSTOMER_SAFE_APPROVAL_STATUSES: tuple[str, ...] = ("approved",)


class QdrantPolicyRetrievalService:
    """Retrieve approved policy chunks from Qdrant using query embeddings."""

    def __init__(
        self,
        *,
        search_store: PolicyVectorSearchStore | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._search_store = search_store or get_policy_vector_search_store(self._settings)
        self._embedding_provider = embedding_provider or get_embedding_provider(self._settings)

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        normalized_query = request.query.strip()
        if not normalized_query:
            return RetrievalResult(error_message="query is required")
        if len(normalized_query) > self._settings.rag_query_max_chars:
            return RetrievalResult(error_message="query exceeds maximum length")

        requested_top_k = min(request.top_k, self._settings.rag_max_top_k)
        score_threshold = request.min_score
        if score_threshold is None:
            score_threshold = self._settings.rag_default_min_score

        domain, domain_error = _resolve_domain(request)
        if domain_error is not None:
            return RetrievalResult(
                error_message=domain_error,
                requested_top_k=requested_top_k,
            )

        approval_statuses = _resolve_approval_statuses(request)

        batch = await self._embedding_provider.embed_texts([normalized_query])
        if not batch.success:
            raise RetrievalServiceError(batch.error or "embedding failed")

        try:
            raw_hits, search_warnings = await self._search_store.search_policy_chunks(
                query_vector=batch.vectors[0].vector,
                top_k=requested_top_k,
                domain=domain,
                document_id=request.document_id,
                document_type=request.document_type,
                approval_statuses=approval_statuses,
            )
        except QdrantStoreError as exc:
            raise RetrievalServiceError(exc.message) from exc

        warnings = list(search_warnings)
        filtered_hits = _post_filter_hits(
            raw_hits,
            request=request,
            approval_statuses=approval_statuses,
            score_threshold=score_threshold,
            warnings=warnings,
        )
        chunks = [_payload_to_chunk(payload, score) for payload, score in filtered_hits]
        chunks = _dedupe_chunks(chunks)
        chunks = chunks[:requested_top_k]

        confidence = chunks[0].relevance_score if chunks else None
        return RetrievalResult(
            chunks=chunks,
            confidence=confidence,
            total_results=len(chunks),
            requested_top_k=requested_top_k,
            applied_domain_filter=domain,
            applied_score_threshold=score_threshold,
            embedding_provider=batch.provider,
            embedding_model=batch.model,
            warnings=warnings,
        )


def _resolve_domain(request: RetrievalRequest) -> tuple[str | None, str | None]:
    if request.domain is not None:
        domain = request.domain.strip()
        if domain and domain not in ALL_POLICY_DOMAINS:
            return None, f"invalid policy domain: {domain}"
        return domain or None, None

    if request.intent and request.intent in INTENT_TO_POLICY_DOMAIN:
        return INTENT_TO_POLICY_DOMAIN[request.intent], None  # type: ignore[index]
    return None, None


def _resolve_approval_statuses(request: RetrievalRequest) -> tuple[str, ...]:
    if not request.approved_only:
        if request.allowed_approval_statuses:
            return tuple(request.allowed_approval_statuses)
        return _CUSTOMER_SAFE_APPROVAL_STATUSES
    # Customer-safe default: never weaken to draft/archived via caller filter.
    if request.allowed_approval_statuses:
        allowed = {status for status in request.allowed_approval_statuses}
        if allowed.issubset(set(_CUSTOMER_SAFE_APPROVAL_STATUSES)):
            return tuple(sorted(allowed))
    return _CUSTOMER_SAFE_APPROVAL_STATUSES


def _post_filter_hits(
    hits: list[tuple[PolicyVectorPayload, float]],
    *,
    request: RetrievalRequest,
    approval_statuses: tuple[str, ...],
    score_threshold: float | None,
    warnings: list[str],
) -> list[tuple[PolicyVectorPayload, float]]:
    filtered: list[tuple[PolicyVectorPayload, float]] = []
    for payload, score in hits:
        if payload.approval_status not in approval_statuses:
            warnings.append("dropped hit with non-approved status after retrieval")
            continue
        if request.approved_only and payload.approval_status != "approved":
            continue
        if request.customer_visible_only and (
            payload.internal_only or not payload.customer_visible
        ):
            continue
        if score_threshold is not None and score < score_threshold:
            continue
        filtered.append((payload, score))
    filtered.sort(
        key=lambda item: (-item[1], item[0].document_id, item[0].chunk_index),
    )
    return filtered


def _payload_to_chunk(payload: PolicyVectorPayload, score: float) -> RetrievedPolicyChunk:
    return RetrievedPolicyChunk(
        document_id=payload.document_id,
        title=payload.title,
        document_type=payload.document_type,
        domain=payload.domain,
        version=payload.version,
        effective_date=payload.effective_date,
        approval_status=payload.approval_status,
        chunk_index=payload.chunk_index,
        chunk_text=payload.chunk_text,
        relevance_score=score,
        source_filename=payload.source_filename,
        indexed_at=payload.indexed_at,
        customer_visible=payload.customer_visible,
        internal_only=payload.internal_only,
    )


def _dedupe_chunks(chunks: list[RetrievedPolicyChunk]) -> list[RetrievedPolicyChunk]:
    seen: set[tuple[str, int]] = set()
    unique: list[RetrievedPolicyChunk] = []
    for chunk in chunks:
        key = (chunk.document_id, chunk.chunk_index)
        if key in seen:
            continue
        seen.add(key)
        unique.append(chunk)
    return unique
