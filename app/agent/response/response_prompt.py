"""Versioned prompt builder for customer response generation (T-061)."""

from __future__ import annotations

from app.agent.response.prompt_context import SafePromptContext
from app.agent.response.response_types import RESPONSE_PROMPT_VERSION


def build_response_system_prompt() -> str:
    """Build provider-neutral system instruction for response generation."""
    return (
        "You are a customer support assistant for a mock digital lending demo.\n"
        "Write one concise, polite, customer-facing response using ONLY the supplied facts.\n"
        "Do not invent actions, IDs, policy terms, statuses, timelines, or completed outcomes.\n"
        "Mention ticket or service-request IDs only when provided in the facts.\n"
        "When Human Review is required, state it clearly without claiming an agent has already acted.\n"
        "Distinguish simulated/mock demo actions from real-world financial actions.\n"
        "Never reveal internal risk scores, model logic, guardrails, tool payloads, or SOP details.\n"
        "Use approved policy snippets only when explicitly provided.\n"
        "Return only structured JSON matching the provided schema.\n"
        f"Prompt version: {RESPONSE_PROMPT_VERSION}"
    )


def _format_policy_snippets(context: SafePromptContext) -> str:
    if not context.policy_snippets:
        return "- (none)"
    lines: list[str] = []
    for snippet in context.policy_snippets:
        lines.append(
            f"- [{snippet.document_id}] {snippet.title}: {snippet.snippet_text}",
        )
    return "\n".join(lines)


def build_response_user_prompt(context: SafePromptContext) -> str:
    """Build bounded user prompt from allow-listed facts."""
    summaries = "\n".join(f"- {summary}" for summary in context.tool_summaries) or "- (none)"
    actions = ", ".join(context.completed_tool_actions) or "(none)"
    documents = ", ".join(context.document_labels) or "(none)"
    question = context.customer_question_excerpt or "(not provided)"
    escalation_reason = context.escalation_reason or "(none)"
    ticket_status = context.ticket_status or "(not set)"
    service_request_id = context.service_request_id or "(none)"
    turnaround = context.turnaround_time_text or "(none)"

    return (
        "Generate a customer response from these facts only:\n"
        f"- intent: {context.intent}\n"
        f"- response_type: {context.customer_response_type}\n"
        f"- customer_action: {context.customer_action}\n"
        f"- system_action: {context.system_action}\n"
        f"- escalation_required: {context.escalation_required}\n"
        f"- escalation_reason: {escalation_reason}\n"
        f"- planned_ticket_status: {ticket_status}\n"
        f"- ticket_id: {context.ticket_id}\n"
        f"- service_request_id: {service_request_id}\n"
        f"- completed_tool_actions: {actions}\n"
        f"- tool_summaries:\n{summaries}\n"
        f"- document_labels: {documents}\n"
        f"- mock_disclaimer_required: {context.mock_disclaimer_required}\n"
        f"- turnaround_time: {turnaround}\n"
        f"- customer_question_excerpt: {question}\n"
        "Approved policy snippets:\n"
        f"{_format_policy_snippets(context)}"
    )
