"""Deterministic retrieval-required policy for the agent workflow (T-056)."""

from __future__ import annotations

from app.tickets.constants import ALL_TICKET_INTENTS, TicketIntent

RETRIEVAL_POLICY_VERSION = "1.0.0"

_RETRIEVAL_REQUIRED_INTENTS: frozenset[TicketIntent] = frozenset(
    {
        "policy_faq",
        "rejection_reason",
        "kyc_document_issue",
        "emi_payment_issue",
        "charges_refund_reversal",
        "loan_statement_request",
        "noc_closure_certificate",
        "bureau_reporting_issue",
        "fraud_security_issue",
        "topup_offer",
    }
)

_RETRIEVAL_SKIPPED_INTENTS: frozenset[TicketIntent] = frozenset(
    {
        "loan_application_status",
        "rm_redirection",
        "unknown",
    }
)

_INTERNAL_SOP_INTENTS: frozenset[TicketIntent] = frozenset(
    {
        "fraud_security_issue",
        "bureau_reporting_issue",
    }
)


def is_retrieval_required(intent: TicketIntent) -> bool:
    """Return whether policy retrieval should run for the classified intent."""
    if intent in _RETRIEVAL_SKIPPED_INTENTS:
        return False
    return intent in _RETRIEVAL_REQUIRED_INTENTS


def retrieval_customer_visible_only(intent: TicketIntent) -> bool:
    """Whether retrieval should filter to customer-visible chunks only."""
    return intent not in _INTERNAL_SOP_INTENTS


def supported_retrieval_policy_intents() -> tuple[TicketIntent, ...]:
    """Return intents covered by the retrieval-required policy."""
    return ALL_TICKET_INTENTS
