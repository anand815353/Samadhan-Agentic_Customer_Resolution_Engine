"""Intent routing defaults and hard risk/priority constraints."""

from __future__ import annotations

from dataclasses import dataclass

from app.tickets.constants import (
    TICKET_CLASS_HUMAN_REVIEW,
    TICKET_CLASS_TIER_1,
    TICKET_CLASS_TIER_2,
    Priority,
    RiskLevel,
    TicketClass,
    TicketIntent,
)


@dataclass(frozen=True)
class IntentRouting:
    ticket_class: TicketClass
    risk_level: RiskLevel
    priority: Priority


INTENT_ROUTING_DEFAULTS: dict[TicketIntent, IntentRouting] = {
    "policy_faq": IntentRouting(TICKET_CLASS_TIER_2, "low", "low"),
    "loan_application_status": IntentRouting(TICKET_CLASS_TIER_2, "low", "medium"),
    "rejection_reason": IntentRouting(TICKET_CLASS_TIER_2, "medium", "medium"),
    "kyc_document_issue": IntentRouting(TICKET_CLASS_TIER_1, "medium", "medium"),
    "emi_payment_issue": IntentRouting(TICKET_CLASS_HUMAN_REVIEW, "high", "high"),
    "charges_refund_reversal": IntentRouting(TICKET_CLASS_HUMAN_REVIEW, "high", "high"),
    "rm_redirection": IntentRouting(TICKET_CLASS_TIER_1, "medium", "medium"),
    "loan_statement_request": IntentRouting(TICKET_CLASS_TIER_1, "medium", "medium"),
    "noc_closure_certificate": IntentRouting(TICKET_CLASS_TIER_1, "medium", "medium"),
    "bureau_reporting_issue": IntentRouting(TICKET_CLASS_HUMAN_REVIEW, "high", "high"),
    "fraud_security_issue": IntentRouting(TICKET_CLASS_HUMAN_REVIEW, "critical", "critical"),
    "topup_offer": IntentRouting(TICKET_CLASS_TIER_2, "medium", "medium"),
    "unknown": IntentRouting(TICKET_CLASS_HUMAN_REVIEW, "high", "high"),
}


def apply_intent_defaults(
    *,
    intent: TicketIntent,
    ticket_class: TicketClass | None,
    risk_level: RiskLevel | None,
    priority: Priority | None,
) -> tuple[TicketClass, RiskLevel, Priority]:
    defaults = INTENT_ROUTING_DEFAULTS[intent]
    return (
        ticket_class or defaults.ticket_class,
        risk_level or defaults.risk_level,
        priority or defaults.priority,
    )


def validate_risk_priority_rules(
    *,
    intent: TicketIntent,
    ticket_class: TicketClass,
    risk_level: RiskLevel,
    priority: Priority,
) -> None:
    """Raise ValueError when hard routing constraints are violated."""
    if intent == "fraud_security_issue":
        if ticket_class != TICKET_CLASS_HUMAN_REVIEW:
            raise ValueError("fraud_security_issue requires human_review ticket class")
        if risk_level != "critical" or priority != "critical":
            raise ValueError("fraud_security_issue requires critical risk and priority")

    if intent == "emi_payment_issue":
        if ticket_class != TICKET_CLASS_HUMAN_REVIEW:
            raise ValueError("emi_payment_issue requires human_review ticket class")
        if risk_level != "high" or priority != "high":
            raise ValueError("emi_payment_issue requires high risk and priority")

    if ticket_class == TICKET_CLASS_HUMAN_REVIEW and intent == "fraud_security_issue":
        if risk_level != "critical" or priority != "critical":
            raise ValueError("human_review fraud cases must be critical/critical")

    if ticket_class == TICKET_CLASS_TIER_1 and risk_level == "critical":
        raise ValueError("tier_1_service_request cannot have critical risk level")

    if risk_level == "critical" and priority != "critical":
        raise ValueError("critical risk level requires critical priority")
