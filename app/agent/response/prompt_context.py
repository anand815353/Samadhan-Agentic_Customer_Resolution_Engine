"""Customer-safe prompt context for response generation (T-061)."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.response.trusted_facts import PolicySnippetFact, TrustedResponseFacts


@dataclass(frozen=True)
class SafePromptContext:
    """Bounded allow-listed context passed to the LLM."""

    intent: str
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


def build_safe_prompt_context(facts: TrustedResponseFacts) -> SafePromptContext:
    """Map trusted facts into the LLM-safe prompt context."""
    return SafePromptContext(
        intent=facts.intent,
        customer_response_type=facts.customer_response_type,
        customer_action=facts.customer_action,
        system_action=facts.system_action,
        escalation_required=facts.escalation_required,
        escalation_reason=facts.escalation_reason,
        ticket_status=facts.ticket_status,
        ticket_id=facts.ticket_id,
        service_request_id=facts.service_request_id,
        completed_tool_actions=facts.completed_tool_actions,
        tool_summaries=facts.tool_summaries,
        document_labels=facts.document_labels,
        policy_snippets=facts.policy_snippets,
        mock_disclaimer_required=facts.mock_disclaimer_required,
        customer_question_excerpt=facts.customer_question_excerpt,
        turnaround_time_text=facts.turnaround_time_text,
    )
