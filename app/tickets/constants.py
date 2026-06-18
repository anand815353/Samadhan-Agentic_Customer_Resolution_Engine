"""Ticket domain constants aligned with TICKETING_AND_RISK_MODEL and DATA_MODEL."""

from typing import Literal

TICKETS_COLLECTION = "tickets"

TicketClass = Literal["tier_2_conversation", "tier_1_service_request", "human_review"]

TicketStatus = Literal[
    "open",
    "auto_resolved",
    "auto_closed",
    "need_more_info",
    "service_requested",
    "in_progress",
    "service_completed",
    "failed",
    "escalated_to_human",
    "under_review",
    "need_customer_input",
    "resolved_by_agent",
    "escalated_further",
    "closed",
]

RiskLevel = Literal["low", "medium", "high", "critical"]
Priority = Literal["low", "medium", "high", "critical"]

TicketIntent = Literal[
    "loan_application_status",
    "rejection_reason",
    "kyc_document_issue",
    "emi_payment_issue",
    "charges_refund_reversal",
    "policy_faq",
    "rm_redirection",
    "loan_statement_request",
    "noc_closure_certificate",
    "bureau_reporting_issue",
    "fraud_security_issue",
    "topup_offer",
    "unknown",
]

TransitionActor = Literal["system", "customer", "support_agent", "admin"]
CreatedBy = Literal["customer", "system", "support_agent", "admin"]
SourceChannel = Literal["web_chat"]

TICKET_CLASS_TIER_2: TicketClass = "tier_2_conversation"
TICKET_CLASS_TIER_1: TicketClass = "tier_1_service_request"
TICKET_CLASS_HUMAN_REVIEW: TicketClass = "human_review"

TERMINAL_STATUSES: frozenset[str] = frozenset({"auto_closed", "closed"})

HUMAN_REVIEW_QUEUE_STATUSES: frozenset[str] = frozenset(
    {
        "escalated_to_human",
        "under_review",
        "need_customer_input",
        "escalated_further",
    }
)

TIER_1_SR_REQUIRED_STATUSES: frozenset[str] = frozenset(
    {"service_requested", "in_progress", "service_completed"}
)

ALL_TICKET_STATUSES: tuple[TicketStatus, ...] = (
    "open",
    "auto_resolved",
    "auto_closed",
    "need_more_info",
    "service_requested",
    "in_progress",
    "service_completed",
    "failed",
    "escalated_to_human",
    "under_review",
    "need_customer_input",
    "resolved_by_agent",
    "escalated_further",
    "closed",
)

ALL_TICKET_INTENTS: tuple[TicketIntent, ...] = (
    "loan_application_status",
    "rejection_reason",
    "kyc_document_issue",
    "emi_payment_issue",
    "charges_refund_reversal",
    "policy_faq",
    "rm_redirection",
    "loan_statement_request",
    "noc_closure_certificate",
    "bureau_reporting_issue",
    "fraud_security_issue",
    "topup_offer",
    "unknown",
)
