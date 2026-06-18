"""Conservative escalation aggregation for resolution planning (T-060)."""

from __future__ import annotations

from app.agent.resolution.resolution_types import (
    MAX_ESCALATION_REASON_LENGTH,
    MANDATORY_ESCALATE_INTENTS,
)
from app.agent.resolution.tool_outcome_collector import ToolOutcomeSummary
from app.agent.state import AgentState, GuardrailState
from app.tickets.constants import TICKET_CLASS_HUMAN_REVIEW, TicketIntent


def _truncate_reason(reason: str) -> str:
    if len(reason) <= MAX_ESCALATION_REASON_LENGTH:
        return reason
    return f"{reason[: MAX_ESCALATION_REASON_LENGTH - 3]}..."


def _intent_escalation_reason(intent: TicketIntent) -> str | None:
    if intent == "fraud_security_issue":
        return "Fraud or unauthorized-transaction report requires critical Human Review."
    if intent == "emi_payment_issue":
        return "Financial dispute requires Human Review."
    if intent == "charges_refund_reversal":
        return "Refund or reversal dispute requires Human Review."
    if intent == "bureau_reporting_issue":
        return "Credit-bureau complaint requires manual verification."
    if intent == "unknown":
        return "Intent could not be determined safely."
    return None


def compute_escalation(
    state: AgentState,
    *,
    guardrail: GuardrailState,
    outcomes: ToolOutcomeSummary,
) -> tuple[bool, str | None]:
    """Return monotonic escalation_required and a bounded reason when true."""
    intent = state.intent_classification.intent  # type: ignore[union-attr]
    risk = state.risk_routing  # type: ignore[union-attr]
    reasons: list[str] = []

    if risk.ticket_class == TICKET_CLASS_HUMAN_REVIEW:
        reasons.append("Human Review routing requires escalation.")
    if guardrail.decision in {"escalate", "block"}:
        if guardrail.reason:
            reasons.append(guardrail.reason)
        elif guardrail.decision == "block":
            reasons.append(
                "Guardrail blocked a prohibited action and manual handling is required.",
            )
        else:
            reasons.append("High-risk scenario requires mandatory Human Review.")
    if guardrail.escalation_required:
        reasons.append("Guardrail policy requires escalation.")
    if risk.risk_level == "critical":
        reasons.append("Critical risk requires Human Review.")
    if intent in MANDATORY_ESCALATE_INTENTS:
        intent_reason = _intent_escalation_reason(intent)
        if intent_reason:
            reasons.append(intent_reason)
    if outcomes.any_tool_escalation:
        reasons.append("Tool output flagged escalation as required.")
    if outcomes.any_high_risk_tool_failure:
        reasons.append("Required tool failed in a high-risk workflow.")

    if not reasons:
        return False, None

    deduped: list[str] = []
    seen: set[str] = set()
    for reason in reasons:
        normalized = reason.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)

    return True, _truncate_reason(deduped[0])
