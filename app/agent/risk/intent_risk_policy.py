"""Deterministic intent-to-risk policy for the agent risk classifier (T-054)."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.constants import ClassificationSource
from app.tickets.constants import ALL_TICKET_INTENTS, Priority, RiskLevel, TicketIntent

RISK_CLASSIFIER_POLICY_VERSION = "1.0.0"
MAX_RISK_REASON_LENGTH = 200
LOW_INTENT_CONFIDENCE_THRESHOLD = 0.25

_HIGH_RISK_FLOOR_INTENTS: frozenset[TicketIntent] = frozenset(
    {
        "emi_payment_issue",
        "charges_refund_reversal",
        "bureau_reporting_issue",
    }
)

_RISK_PRIORITY_RANK: dict[str, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}


@dataclass(frozen=True)
class IntentRiskPolicy:
    """Canonical risk and priority mapping for one supported intent."""

    risk_level: RiskLevel
    priority: Priority
    reason: str


@dataclass(frozen=True)
class RiskClassificationResult:
    """Outcome of deterministic risk classification."""

    risk_level: RiskLevel
    priority: Priority
    risk_reason: str
    policy_version: str


INTENT_RISK_POLICY: dict[TicketIntent, IntentRiskPolicy] = {
    "policy_faq": IntentRiskPolicy(
        "low",
        "low",
        "General policy query is safe for automated informational handling.",
    ),
    "loan_application_status": IntentRiskPolicy(
        "low",
        "medium",
        "Loan status is customer-specific and requires normal operational tracking.",
    ),
    "rejection_reason": IntentRiskPolicy(
        "medium",
        "medium",
        "Rejection explanation is sensitive and requires auditable handling.",
    ),
    "kyc_document_issue": IntentRiskPolicy(
        "medium",
        "medium",
        "KYC or document issues may require an auditable service workflow.",
    ),
    "rm_redirection": IntentRiskPolicy(
        "medium",
        "medium",
        "RM callback coordination requires auditable service tracking.",
    ),
    "loan_statement_request": IntentRiskPolicy(
        "medium",
        "medium",
        "Loan statement servicing requires an auditable document workflow.",
    ),
    "noc_closure_certificate": IntentRiskPolicy(
        "medium",
        "medium",
        "NOC or closure certificate servicing requires auditable handling.",
    ),
    "topup_offer": IntentRiskPolicy(
        "medium",
        "medium",
        "Top-up eligibility may create a lead only; disbursement is not permitted.",
    ),
    "emi_payment_issue": IntentRiskPolicy(
        "high",
        "high",
        "Payment dispute has potential financial impact.",
    ),
    "charges_refund_reversal": IntentRiskPolicy(
        "high",
        "high",
        "Fee, refund, or reversal dispute has potential financial impact.",
    ),
    "bureau_reporting_issue": IntentRiskPolicy(
        "high",
        "high",
        "Bureau complaint may affect the customer's credit record.",
    ),
    "fraud_security_issue": IntentRiskPolicy(
        "critical",
        "critical",
        "Fraud or unauthorized-transaction report requires critical handling.",
    ),
    "unknown": IntentRiskPolicy(
        "high",
        "high",
        "Intent is unknown, so conservative handling is required.",
    ),
}


def _truncate_reason(reason: str) -> str:
    if len(reason) <= MAX_RISK_REASON_LENGTH:
        return reason
    return f"{reason[: MAX_RISK_REASON_LENGTH - 3]}..."


def _max_risk_level(current: RiskLevel, minimum: RiskLevel) -> RiskLevel:
    return current if _RISK_PRIORITY_RANK[current] >= _RISK_PRIORITY_RANK[minimum] else minimum


def _max_priority(current: Priority, minimum: Priority) -> Priority:
    return current if _RISK_PRIORITY_RANK[current] >= _RISK_PRIORITY_RANK[minimum] else minimum


def _apply_hard_floors(intent: TicketIntent, policy: IntentRiskPolicy) -> IntentRiskPolicy:
    risk_level = policy.risk_level
    priority = policy.priority

    if intent in _HIGH_RISK_FLOOR_INTENTS or intent == "unknown":
        risk_level = _max_risk_level(risk_level, "high")
        priority = _max_priority(priority, "high")

    if intent == "fraud_security_issue":
        risk_level = "critical"
        priority = "critical"

    if risk_level == "critical":
        priority = "critical"

    return IntentRiskPolicy(risk_level=risk_level, priority=priority, reason=policy.reason)


def classify_intent_risk(
    intent: TicketIntent,
    *,
    confidence: float | None = None,
    source: ClassificationSource | None = None,
) -> RiskClassificationResult:
    """Map a validated intent to deterministic risk level, priority, and reason."""
    _ = source
    policy = _apply_hard_floors(intent, INTENT_RISK_POLICY[intent])
    reason = policy.reason
    if confidence is not None and confidence < LOW_INTENT_CONFIDENCE_THRESHOLD and intent != "unknown":
        reason = (
            f"{reason} Intent confidence was low; routing will apply conservative handling."
        )
    return RiskClassificationResult(
        risk_level=policy.risk_level,
        priority=policy.priority,
        risk_reason=_truncate_reason(reason),
        policy_version=RISK_CLASSIFIER_POLICY_VERSION,
    )


def supported_policy_intents() -> tuple[TicketIntent, ...]:
    """Return intents covered by the risk classifier policy map."""
    return ALL_TICKET_INTENTS
