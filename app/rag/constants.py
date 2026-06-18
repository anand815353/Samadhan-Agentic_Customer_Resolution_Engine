"""RAG domain constants aligned with RAG_AND_KNOWLEDGE_BASE and seed policy domains."""

from typing import Literal

from app.tickets.constants import TicketIntent

POLICIES_QDRANT_COLLECTION = "samadhan_policies"

DEFAULT_TOP_K = 5
DEFAULT_MIN_TOP_K = 1
DEFAULT_MAX_TOP_K = 10

PolicyDomain = Literal[
    "loan_status",
    "rejection",
    "kyc",
    "emi",
    "refund",
    "noc",
    "bureau",
    "fraud",
    "topup",
    "rm",
    "safety",
]

ALL_POLICY_DOMAINS: tuple[PolicyDomain, ...] = (
    "loan_status",
    "rejection",
    "kyc",
    "emi",
    "refund",
    "noc",
    "bureau",
    "fraud",
    "topup",
    "rm",
    "safety",
)

INTENT_TO_POLICY_DOMAIN: dict[TicketIntent, PolicyDomain | None] = {
    "policy_faq": None,
    "loan_application_status": "loan_status",
    "rejection_reason": "rejection",
    "kyc_document_issue": "kyc",
    "emi_payment_issue": "emi",
    "charges_refund_reversal": "refund",
    "rm_redirection": "rm",
    "loan_statement_request": "noc",
    "noc_closure_certificate": "noc",
    "bureau_reporting_issue": "bureau",
    "fraud_security_issue": "fraud",
    "topup_offer": "topup",
}

_HIGH_RISK_RETRIEVAL_FAILURE_INTENTS: frozenset[TicketIntent] = frozenset(
    {
        "fraud_security_issue",
        "bureau_reporting_issue",
    }
)

HIGH_RISK_RETRIEVAL_FAILURE_INTENTS = _HIGH_RISK_RETRIEVAL_FAILURE_INTENTS
