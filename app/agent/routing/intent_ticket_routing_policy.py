"""Deterministic intent-to-ticket-class routing policy (T-055)."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.constants import ClassificationSource
from app.agent.risk.intent_risk_policy import LOW_INTENT_CONFIDENCE_THRESHOLD
from app.tickets.constants import (
    TICKET_CLASS_HUMAN_REVIEW,
    TICKET_CLASS_TIER_1,
    TICKET_CLASS_TIER_2,
    ALL_TICKET_INTENTS,
    Priority,
    RiskLevel,
    TicketClass,
    TicketIntent,
)
from app.tickets.risk_rules import INTENT_ROUTING_DEFAULTS

TICKET_ROUTING_POLICY_VERSION = "1.0.0"
MAX_ROUTING_REASON_LENGTH = 200

_TICKET_CLASS_RANK: dict[TicketClass, int] = {
    TICKET_CLASS_TIER_2: 1,
    TICKET_CLASS_TIER_1: 2,
    TICKET_CLASS_HUMAN_REVIEW: 3,
}

_MANDATORY_HR_INTENTS: frozenset[TicketIntent] = frozenset(
    {
        "fraud_security_issue",
        "emi_payment_issue",
        "charges_refund_reversal",
        "bureau_reporting_issue",
        "unknown",
    }
)

_BASE_REASON_BY_INTENT: dict[TicketIntent, str] = {
    "policy_faq": "Informational policy query is eligible for a Tier 2 conversation.",
    "loan_application_status": (
        "Customer-specific loan status can be handled as an informational Tier 2 conversation."
    ),
    "rejection_reason": (
        "Customer-safe rejection explanation can be handled as an informational Tier 2 conversation."
    ),
    "kyc_document_issue": "Document action requires an auditable Tier 1 service request.",
    "rm_redirection": "RM callback requires a Tier 1 service request.",
    "loan_statement_request": "Loan statement request requires a Tier 1 service request.",
    "noc_closure_certificate": "NOC or closure certificate requires a Tier 1 service request.",
    "topup_offer": "Top-up eligibility check is eligible for an informational Tier 2 conversation.",
    "emi_payment_issue": "Payment dispute requires Human Review due to potential financial impact.",
    "charges_refund_reversal": (
        "Refund or reversal dispute requires Human Review due to potential financial impact."
    ),
    "bureau_reporting_issue": (
        "Bureau complaint requires Human Review due to possible credit-record impact."
    ),
    "fraud_security_issue": "Fraud or security report requires mandatory Human Review.",
    "unknown": "Unknown intent requires conservative Human Review routing.",
}

_REASON_CRITICAL_RISK = "Critical risk requires mandatory Human Review routing."
_REASON_HIGH_RISK = "High risk requires Human Review routing."
_REASON_HIGH_PRIORITY = "High or critical priority requires Human Review routing."
_REASON_LOW_CONFIDENCE = (
    "Known intent confidence was below the approved floor; routing conservatively to Human Review."
)
_REASON_PRESERVED_HUMAN_REVIEW = (
    "Existing Human Review classification was preserved and not downgraded."
)
_REASON_PRESERVED_TIER_1 = (
    "Existing Tier 1 service classification was preserved and not downgraded."
)


@dataclass(frozen=True)
class TicketRoutingResult:
    """Outcome of deterministic ticket routing."""

    ticket_class: TicketClass
    routing_reason: str
    policy_version: str


def _truncate_reason(reason: str) -> str:
    if len(reason) <= MAX_ROUTING_REASON_LENGTH:
        return reason
    return f"{reason[: MAX_ROUTING_REASON_LENGTH - 3]}..."


def _max_ticket_class(current: TicketClass, candidate: TicketClass) -> TicketClass:
    if _TICKET_CLASS_RANK[candidate] > _TICKET_CLASS_RANK[current]:
        return candidate
    return current


def _base_ticket_class(intent: TicketIntent) -> TicketClass:
    return INTENT_ROUTING_DEFAULTS[intent].ticket_class


def _apply_risk_and_confidence_overrides(
    intent: TicketIntent,
    *,
    base_class: TicketClass,
    risk_level: RiskLevel,
    priority: Priority,
    confidence: float | None,
) -> tuple[TicketClass, str]:
    if intent in _MANDATORY_HR_INTENTS:
        return TICKET_CLASS_HUMAN_REVIEW, _BASE_REASON_BY_INTENT[intent]

    routed_class = base_class
    reason = _BASE_REASON_BY_INTENT[intent]

    if risk_level == "critical":
        return TICKET_CLASS_HUMAN_REVIEW, _REASON_CRITICAL_RISK

    if risk_level == "high":
        return TICKET_CLASS_HUMAN_REVIEW, _REASON_HIGH_RISK

    if priority in ("high", "critical") and routed_class == TICKET_CLASS_TIER_2:
        return TICKET_CLASS_HUMAN_REVIEW, _REASON_HIGH_PRIORITY

    if (
        confidence is not None
        and confidence < LOW_INTENT_CONFIDENCE_THRESHOLD
        and intent != "unknown"
    ):
        return TICKET_CLASS_HUMAN_REVIEW, _REASON_LOW_CONFIDENCE

    return routed_class, reason


def _merge_persisted_ticket_class(
    routed_class: TicketClass,
    routed_reason: str,
    persisted_ticket_class: TicketClass | None,
) -> tuple[TicketClass, str]:
    if persisted_ticket_class is None:
        return routed_class, routed_reason

    merged = _max_ticket_class(routed_class, persisted_ticket_class)
    if merged == routed_class:
        return routed_class, routed_reason

    if persisted_ticket_class == TICKET_CLASS_HUMAN_REVIEW:
        return merged, _REASON_PRESERVED_HUMAN_REVIEW
    if persisted_ticket_class == TICKET_CLASS_TIER_1:
        return merged, _REASON_PRESERVED_TIER_1
    return merged, routed_reason


def route_ticket(
    intent: TicketIntent,
    *,
    risk_level: RiskLevel,
    priority: Priority,
    confidence: float | None = None,
    source: ClassificationSource | None = None,
    persisted_ticket_class: TicketClass | None = None,
) -> TicketRoutingResult:
    """Map validated intent and risk inputs to a deterministic ticket class."""
    _ = source
    base_class = _base_ticket_class(intent)
    routed_class, reason = _apply_risk_and_confidence_overrides(
        intent,
        base_class=base_class,
        risk_level=risk_level,
        priority=priority,
        confidence=confidence,
    )
    final_class, final_reason = _merge_persisted_ticket_class(
        routed_class,
        reason,
        persisted_ticket_class,
    )
    return TicketRoutingResult(
        ticket_class=final_class,
        routing_reason=_truncate_reason(final_reason),
        policy_version=TICKET_ROUTING_POLICY_VERSION,
    )


def supported_routing_intents() -> tuple[TicketIntent, ...]:
    """Return intents covered by the ticket routing policy map."""
    return ALL_TICKET_INTENTS
