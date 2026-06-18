"""Build trusted response facts from validated workflow state (T-061)."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.exceptions import ResponseValidationError
from app.agent.resolution.resolution_types import DOCUMENT_COMPLETED_ACTIONS
from app.agent.response.response_types import (
    MOCK_DISCLAIMER_INTENTS,
    MOCK_DISCLAIMER_SYSTEM_ACTIONS,
    RESPONSE_MAX_CUSTOMER_EXCERPT,
    RESPONSE_MAX_POLICY_SNIPPETS,
    RESPONSE_MAX_SNIPPET_CHARACTERS,
)
from app.agent.state import AgentState, ResolutionPlan
from app.common.masking import contains_unmasked_sensitive_text, mask_sensitive_data
from app.tickets.constants import TicketIntent


@dataclass(frozen=True)
class PolicySnippetFact:
    document_id: str
    title: str
    snippet_text: str


@dataclass(frozen=True)
class TrustedResponseFacts:
    """Customer-safe facts derived only from validated upstream state."""

    intent: TicketIntent
    customer_response_type: str
    customer_action: str
    system_action: str
    escalation_required: bool
    escalation_reason: str | None
    ticket_status: str | None
    ticket_id: str
    service_request_id: str | None
    completed_tool_actions: tuple[str, ...]
    tool_summaries: tuple[str, ...]
    document_labels: tuple[str, ...]
    policy_snippets: tuple[PolicySnippetFact, ...]
    mock_disclaimer_required: bool
    customer_question_excerpt: str | None
    turnaround_time_text: str | None


def _dedupe_preserve_order(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def _collect_tool_summaries(state: AgentState) -> tuple[str, ...]:
    summaries: list[str] = []
    for step in state.tool_steps:
        if step.status != "completed" or step.tool_output is None:
            continue
        output = step.tool_output
        if output.success and output.customer_safe_summary.strip():
            summaries.append(output.customer_safe_summary.strip())
    return _dedupe_preserve_order(summaries)


def _collect_document_labels(state: AgentState, completed_actions: tuple[str, ...]) -> tuple[str, ...]:
    if not any(action in DOCUMENT_COMPLETED_ACTIONS for action in completed_actions):
        return ()
    labels: list[str] = []
    for step in state.tool_steps:
        if step.status != "completed" or step.tool_output is None:
            continue
        output = step.tool_output
        if not output.success:
            continue
        document_type = output.data.get("document_type")
        if isinstance(document_type, str) and document_type.strip():
            labels.append(document_type.strip().replace("_", " "))
        status = output.data.get("status")
        if isinstance(status, str) and status.strip() and status not in labels:
            labels.append(status.strip().replace("_", " "))
    return _dedupe_preserve_order(labels)


def _collect_policy_snippets(state: AgentState) -> tuple[PolicySnippetFact, ...]:
    if state.retrieval is None or state.retrieval.result is None:
        return ()
    result = state.retrieval.result
    if result.unavailable or not result.chunks:
        return ()
    approved_ids = set(state.retrieval.source_policy_ids)
    if not approved_ids:
        return ()

    snippets: list[PolicySnippetFact] = []
    for chunk in result.chunks:
        if chunk.document_id not in approved_ids:
            continue
        if chunk.approval_status != "approved":
            continue
        if chunk.internal_only or not chunk.customer_visible:
            continue
        text = chunk.chunk_text.strip()
        if not text:
            continue
        if len(text) > RESPONSE_MAX_SNIPPET_CHARACTERS:
            text = text[: RESPONSE_MAX_SNIPPET_CHARACTERS - 3].rstrip() + "..."
        snippets.append(
            PolicySnippetFact(
                document_id=chunk.document_id,
                title=chunk.title.strip(),
                snippet_text=text,
            ),
        )
        if len(snippets) >= RESPONSE_MAX_POLICY_SNIPPETS:
            break
    return tuple(snippets)


def _customer_question_excerpt(state: AgentState) -> str | None:
    raw = state.normalized_message or state.customer_message
    text = raw.strip()
    if not text:
        return None
    if contains_unmasked_sensitive_text(text):
        text = mask_sensitive_data(text)
    if len(text) > RESPONSE_MAX_CUSTOMER_EXCERPT:
        text = text[: RESPONSE_MAX_CUSTOMER_EXCERPT - 3].rstrip() + "..."
    return text


def _mock_disclaimer_required(plan: ResolutionPlan) -> bool:
    if plan.system_action in MOCK_DISCLAIMER_SYSTEM_ACTIONS:
        return True
    return plan.intent in MOCK_DISCLAIMER_INTENTS


def build_trusted_response_facts(state: AgentState) -> TrustedResponseFacts:
    """Extract allow-listed facts for response generation."""
    if state.resolution_plan is None:
        raise ResponseValidationError("resolution plan is required before response generation")
    if state.ticket_id is None:
        raise ResponseValidationError("ticket_id is required before response generation")
    if state.intent_classification is None:
        raise ResponseValidationError("intent classification is required before response generation")
    if state.risk_routing is None or state.risk_routing.ticket_class is None:
        raise ResponseValidationError("ticket class is required before response generation")

    plan = state.resolution_plan
    completed_actions = tuple(plan.tool_actions)
    return TrustedResponseFacts(
        intent=plan.intent,
        customer_response_type=plan.customer_response_type,
        customer_action=plan.customer_action,
        system_action=plan.system_action,
        escalation_required=plan.escalation_required,
        escalation_reason=plan.escalation_reason,
        ticket_status=plan.ticket_status,
        ticket_id=state.ticket_id,
        service_request_id=plan.service_request_id,
        completed_tool_actions=completed_actions,
        tool_summaries=_collect_tool_summaries(state),
        document_labels=_collect_document_labels(state, completed_actions),
        policy_snippets=_collect_policy_snippets(state),
        mock_disclaimer_required=_mock_disclaimer_required(plan),
        customer_question_excerpt=_customer_question_excerpt(state),
        turnaround_time_text=None,
    )
