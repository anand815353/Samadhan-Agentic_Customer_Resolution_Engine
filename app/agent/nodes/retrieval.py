"""LangGraph retrieval node implementation (T-056)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.agent.constants import NODE_RETRIEVAL
from app.agent.exceptions import RetrievalValidationError
from app.agent.nodes.base import NodeCallable
from app.agent.retrieval.intent_retrieval_policy import (
    RETRIEVAL_POLICY_VERSION,
    is_retrieval_required,
    retrieval_customer_visible_only,
)
from app.agent.retrieval_deps import RetrievalDeps
from app.agent.state import AgentState, RetrievalState, WorkflowError
from app.rag.domain_resolution import resolve_policy_domain
from app.rag.retrieval import RetrievalServiceError
from app.rag.schemas import RetrievedPolicyChunk, RetrievalRequest, RetrievalResult
from app.tickets.constants import ALL_TICKET_INTENTS

logger = logging.getLogger("samadhan.agent")

_RETRIEVAL_UNAVAILABLE_MESSAGE = "Policy retrieval unavailable; continuing safely."


def _resolve_query(state: AgentState, *, max_chars: int) -> str:
    raw = state.normalized_message or state.customer_message
    query = raw.strip()
    if len(query) > max_chars:
        return query[:max_chars]
    return query


def _empty_retrieval_result() -> RetrievalResult:
    return RetrievalResult(chunks=[], confidence=None, total_results=0)


def _source_policy_ids(chunks: list[RetrievedPolicyChunk]) -> list[str]:
    return list(dict.fromkeys(chunk.document_id for chunk in chunks))


def _filter_accepted_chunks(
    chunks: list[RetrievedPolicyChunk],
    *,
    required_domain: str | None,
) -> list[RetrievedPolicyChunk]:
    accepted: list[RetrievedPolicyChunk] = []
    for chunk in chunks:
        if chunk.approval_status != "approved":
            continue
        if required_domain is not None and chunk.domain != required_domain:
            continue
        accepted.append(chunk)
    return accepted


def _build_retrieval_state(
    *,
    state: AgentState,
    retrieval_required: bool,
    result: RetrievalResult,
    source_policy_ids: list[str],
    workflow_errors: list[WorkflowError] | None = None,
) -> dict[str, Any]:
    errors = list(state.workflow_errors)
    if workflow_errors:
        errors.extend(workflow_errors)
    return {
        "retrieval": RetrievalState(
            retrieval_required=retrieval_required,
            result=result,
            source_policy_ids=source_policy_ids,
        ),
        "workflow_errors": errors,
    }


class RetrievalNode:
    """Retrieve approved policy chunks when required by classified intent."""

    def __init__(self, deps: RetrievalDeps) -> None:
        self._deps = deps

    async def __call__(self, state: AgentState) -> dict[str, Any]:
        if state.intent_classification is None:
            raise RetrievalValidationError(
                "intent classification is required before retrieval",
            )

        intent = state.intent_classification.intent
        if intent not in ALL_TICKET_INTENTS:
            raise RetrievalValidationError("unsupported intent for retrieval")

        query = _resolve_query(
            state,
            max_chars=self._deps.settings.rag_query_max_chars,
        )
        if not query:
            raise RetrievalValidationError(
                "normalized customer message is required before retrieval",
            )

        required = is_retrieval_required(intent)
        if not required:
            logger.info(
                "retrieval skipped workflow_id=%s intent=%s policy=%s",
                state.workflow_id,
                intent,
                RETRIEVAL_POLICY_VERSION,
            )
            return _build_retrieval_state(
                state=state,
                retrieval_required=False,
                result=_empty_retrieval_result(),
                source_policy_ids=[],
            )

        domain = resolve_policy_domain(intent, query)
        customer_visible_only = retrieval_customer_visible_only(intent)
        settings = self._deps.settings

        request = RetrievalRequest(
            query=query,
            intent=intent,
            domain=domain,
            top_k=settings.rag_default_top_k,
            min_score=settings.rag_default_min_score,
            approved_only=True,
            customer_visible_only=customer_visible_only,
        )

        try:
            result = await self._deps.policy_retrieval_service.retrieve(request)
        except asyncio.CancelledError:
            raise
        except RetrievalServiceError:
            logger.warning(
                "retrieval unavailable workflow_id=%s intent=%s domain=%s",
                state.workflow_id,
                intent,
                domain,
            )
            return _build_retrieval_state(
                state=state,
                retrieval_required=True,
                result=RetrievalResult(unavailable=True),
                source_policy_ids=[],
                workflow_errors=[
                    WorkflowError(
                        code="retrieval_unavailable",
                        message=_RETRIEVAL_UNAVAILABLE_MESSAGE,
                        node=NODE_RETRIEVAL,
                        recoverable=True,
                    )
                ],
            )

        if result.unavailable:
            logger.warning(
                "retrieval unavailable workflow_id=%s intent=%s domain=%s",
                state.workflow_id,
                intent,
                domain,
            )
            return _build_retrieval_state(
                state=state,
                retrieval_required=True,
                result=result,
                source_policy_ids=[],
                workflow_errors=[
                    WorkflowError(
                        code="retrieval_unavailable",
                        message=_RETRIEVAL_UNAVAILABLE_MESSAGE,
                        node=NODE_RETRIEVAL,
                        recoverable=True,
                    )
                ],
            )

        if result.error_message:
            logger.info(
                "retrieval soft failure workflow_id=%s intent=%s domain=%s",
                state.workflow_id,
                intent,
                domain,
            )
            return _build_retrieval_state(
                state=state,
                retrieval_required=True,
                result=RetrievalResult(
                    chunks=[],
                    confidence=None,
                    error_message=result.error_message,
                    requested_top_k=result.requested_top_k,
                    applied_domain_filter=domain,
                ),
                source_policy_ids=[],
            )

        filtered_chunks = _filter_accepted_chunks(result.chunks, required_domain=domain)
        confidence = filtered_chunks[0].relevance_score if filtered_chunks else None
        final_result = RetrievalResult(
            chunks=filtered_chunks,
            confidence=confidence,
            total_results=len(filtered_chunks),
            requested_top_k=result.requested_top_k,
            applied_domain_filter=domain,
            applied_score_threshold=result.applied_score_threshold,
            embedding_provider=result.embedding_provider,
            embedding_model=result.embedding_model,
            warnings=list(result.warnings),
        )
        source_ids = _source_policy_ids(filtered_chunks)

        logger.info(
            "retrieval completed workflow_id=%s intent=%s domain=%s required=%s count=%s policy=%s",
            state.workflow_id,
            intent,
            domain,
            required,
            len(filtered_chunks),
            RETRIEVAL_POLICY_VERSION,
        )

        return _build_retrieval_state(
            state=state,
            retrieval_required=True,
            result=final_result,
            source_policy_ids=source_ids,
        )


def build_retrieval_node(deps: RetrievalDeps) -> NodeCallable:
    """Return a retrieval node callable."""
    node = RetrievalNode(deps)

    async def retrieval_node(state: AgentState) -> dict[str, Any]:
        return await node(state)

    return retrieval_node


# Registry stub; build_default_registry replaces with build_retrieval_node().
from app.agent.nodes.base import passthrough_node as retrieval_node  # noqa: E402

__all__ = ["RetrievalNode", "build_retrieval_node", "retrieval_node"]
