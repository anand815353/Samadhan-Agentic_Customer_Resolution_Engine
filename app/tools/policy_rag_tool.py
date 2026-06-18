"""PolicyRAGTool — safe wrapper around policy retrieval for FAQ and supporting intents."""

from __future__ import annotations

from typing import Any

from app.customers.repositories import CustomerRepository
from app.rag.constants import (
    DEFAULT_MAX_TOP_K,
    DEFAULT_MIN_TOP_K,
    DEFAULT_TOP_K,
    HIGH_RISK_RETRIEVAL_FAILURE_INTENTS,
    INTENT_TO_POLICY_DOMAIN,
)
from app.rag.domain_resolution import resolve_policy_domain
from app.rag.retrieval import PolicyRetrievalService, RetrievalServiceError
from app.rag.schemas import RetrievedPolicyChunk, RetrievalRequest
from app.tickets.constants import TicketIntent
from app.tools.audit_hook import ToolAuditHook
from app.tools.base import BaseMockTool
from app.tools.constants import ToolName
from app.tools.exceptions import ToolExecutionError, ToolValidationError
from app.tools.schemas import ToolInput, ToolRunResult

SUPPORTED_INTENTS: frozenset[TicketIntent] = frozenset(INTENT_TO_POLICY_DOMAIN.keys())

_CHUNKS_RETRIEVED_SUMMARY = "I found relevant approved policy context for this query."
_NO_CHUNKS_SUMMARY = (
    "I could not find approved policy context for this query in the demo knowledge base."
)
_UNAVAILABLE_SUMMARY = "Policy retrieval is not available in the current demo configuration."
_FAILED_SUMMARY = "Policy retrieval could not be completed safely for this query."

_QUERY_KEY_ALIASES = ("query", "customer_message", "message_text")


class PolicyRAGTool(BaseMockTool):
    """Mock tool wrapper that retrieves approved policy chunks via injected retrieval service."""

    def __init__(
        self,
        customer_repository: CustomerRepository,
        policy_retrieval_service: PolicyRetrievalService | None = None,
        audit_hook: ToolAuditHook | None = None,
    ) -> None:
        super().__init__(audit_hook=audit_hook)
        self._customer_repository = customer_repository
        self._policy_retrieval_service = policy_retrieval_service

    @property
    def tool_name(self) -> ToolName:
        return "PolicyRAGTool"

    def validate_input(self, tool_input: ToolInput) -> None:
        if tool_input.intent not in SUPPORTED_INTENTS:
            raise ToolValidationError(
                f"PolicyRAGTool does not support intent: {tool_input.intent}"
            )

    async def _run(self, tool_input: ToolInput) -> ToolRunResult:
        customer = await self._customer_repository.find_by_id(tool_input.customer_id)
        if customer is None:
            raise ToolExecutionError(
                "Customer record was not found for this demo profile.",
                code="not_found",
                retryable=False,
            )

        if self._policy_retrieval_service is None:
            return ToolRunResult(
                data={},
                customer_safe_summary=_UNAVAILABLE_SUMMARY,
                action_taken="policy_retrieval_unavailable",
                escalation_required=False,
            )

        query = _resolve_query(tool_input)
        domain = resolve_policy_domain(
            tool_input.intent,
            query,
            parameters=tool_input.parameters,
        )
        customer_visible_only = _parse_customer_visible(tool_input.parameters)
        top_k = _parse_top_k(tool_input.parameters)
        min_score = _parse_min_score(tool_input.parameters)

        request = RetrievalRequest(
            query=query,
            intent=tool_input.intent,
            domain=domain,
            top_k=top_k,
            approved_only=True,
            customer_visible_only=customer_visible_only,
            min_score=min_score,
        )

        try:
            result = await self._policy_retrieval_service.retrieve(request)
        except RetrievalServiceError:
            return _retrieval_failed_result(tool_input.intent)
        except Exception:
            return _retrieval_failed_result(tool_input.intent)

        if result.unavailable:
            return ToolRunResult(
                data={"domain_used": domain},
                customer_safe_summary=_UNAVAILABLE_SUMMARY,
                action_taken="policy_retrieval_unavailable",
                escalation_required=False,
            )

        if result.error_message:
            return _retrieval_failed_result(tool_input.intent)

        visible_chunks = _filter_visible_chunks(
            result.chunks,
            customer_visible_only=customer_visible_only,
        )
        if not visible_chunks:
            return ToolRunResult(
                data={"domain_used": domain, "source_policy_ids": []},
                customer_safe_summary=_NO_CHUNKS_SUMMARY,
                action_taken="policy_chunks_not_found",
                escalation_required=False,
            )

        return ToolRunResult(
            data=_build_safe_data(
                chunks=visible_chunks,
                domain_used=domain,
                confidence=result.confidence,
            ),
            customer_safe_summary=_CHUNKS_RETRIEVED_SUMMARY,
            action_taken="policy_chunks_retrieved",
            escalation_required=False,
        )


def _retrieval_failed_result(intent: TicketIntent) -> ToolRunResult:
    escalate = intent in HIGH_RISK_RETRIEVAL_FAILURE_INTENTS
    return ToolRunResult(
        data={},
        customer_safe_summary=_FAILED_SUMMARY,
        action_taken="policy_retrieval_failed",
        escalation_required=escalate,
    )


def _resolve_query(tool_input: ToolInput) -> str:
    parameters = tool_input.parameters
    for key in _QUERY_KEY_ALIASES:
        value = parameters.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    domain = resolve_policy_domain(
        tool_input.intent,
        "",
        parameters=parameters,
    )
    if domain:
        return f"{tool_input.intent} {domain}"
    return tool_input.intent


def _parse_customer_visible(parameters: dict[str, Any]) -> bool:
    value = parameters.get("customer_visible")
    if value is False:
        return False
    if isinstance(value, str) and value.strip().lower() in {"false", "0", "no"}:
        return False
    return True


def _parse_top_k(parameters: dict[str, Any]) -> int:
    value = parameters.get("top_k")
    if isinstance(value, bool):
        return DEFAULT_TOP_K
    if isinstance(value, int):
        return max(DEFAULT_MIN_TOP_K, min(DEFAULT_MAX_TOP_K, value))
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        return max(DEFAULT_MIN_TOP_K, min(DEFAULT_MAX_TOP_K, parsed))
    return DEFAULT_TOP_K


def _parse_min_score(parameters: dict[str, Any]) -> float | None:
    value = parameters.get("min_score")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _filter_visible_chunks(
    chunks: list[RetrievedPolicyChunk],
    *,
    customer_visible_only: bool,
) -> list[RetrievedPolicyChunk]:
    if not customer_visible_only:
        return list(chunks)
    return [
        chunk
        for chunk in chunks
        if chunk.customer_visible and not chunk.internal_only
    ]


def _build_safe_data(
    *,
    chunks: list[RetrievedPolicyChunk],
    domain_used: str | None,
    confidence: float | None,
) -> dict[str, Any]:
    source_policy_ids = list(dict.fromkeys(chunk.document_id for chunk in chunks))
    data: dict[str, Any] = {
        "retrieved_chunks": [chunk.model_dump() for chunk in chunks],
        "source_policy_ids": source_policy_ids,
        "domain_used": domain_used,
    }
    if confidence is not None:
        data["retrieval_confidence"] = confidence
    return data
