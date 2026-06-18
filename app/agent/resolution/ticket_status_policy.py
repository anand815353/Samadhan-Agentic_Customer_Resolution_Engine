"""Deterministic ticket-status selection for resolution planning (T-060)."""

from __future__ import annotations

from app.agent.resolution.tool_outcome_collector import (
    ToolOutcomeSummary,
    has_document_completed,
    has_service_request_created,
)
from app.agent.state import GuardrailState
from app.tickets.constants import TicketClass, TicketIntent, TicketStatus


def select_ticket_status(
    *,
    intent: TicketIntent,
    ticket_class: TicketClass,
    guardrail: GuardrailState,
    escalation_required: bool,
    outcomes: ToolOutcomeSummary,
    primary_sr_id: str | None,
) -> TicketStatus:
    """Choose the intended immediate workflow ticket status (not persisted here)."""
    if guardrail.decision == "ask_follow_up" or intent == "unknown":
        return "need_more_info"

    if guardrail.decision == "block":
        return "escalated_to_human"

    if escalation_required or ticket_class == "human_review":
        return "escalated_to_human"

    if has_document_completed(outcomes):
        return "service_completed"

    if has_service_request_created(outcomes) or primary_sr_id is not None:
        if primary_sr_id is None and ticket_class == "tier_1_service_request":
            return "failed"
        return "service_requested"

    if outcomes.any_high_risk_tool_failure:
        return "escalated_to_human"

    if outcomes.any_tool_failure:
        if intent in {"policy_faq", "unknown"}:
            return "need_more_info"
        return "failed"

    if ticket_class == "tier_2_conversation" and outcomes.has_successful_output:
        return "auto_resolved"

    if guardrail.decision in {"allow", "allow_with_audit"} and outcomes.has_successful_output:
        return "auto_resolved"

    if guardrail.decision == "ask_follow_up":
        return "need_more_info"

    return "failed"
