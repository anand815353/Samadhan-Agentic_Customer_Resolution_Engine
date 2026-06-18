"""Versioned prompt builder for intent classifier LLM fallback (T-053)."""

from __future__ import annotations

from app.tickets.constants import ALL_TICKET_INTENTS

INTENT_CLASSIFIER_PROMPT_VERSION = "1.0.0"

_INTENT_DEFINITIONS: dict[str, str] = {
    "loan_application_status": "Customer asks about pending/approved loan or application status.",
    "rejection_reason": "Customer asks why a loan was rejected or declined.",
    "kyc_document_issue": "Customer has KYC or document upload/verification problems.",
    "emi_payment_issue": "Customer reports EMI/payment problems including duplicate debit.",
    "charges_refund_reversal": "Customer asks about fees, refunds, or reversals.",
    "policy_faq": "General policy/process question without a customer-specific action request.",
    "rm_redirection": "Customer wants RM contact or callback.",
    "loan_statement_request": "Customer requests loan/account/repayment statement.",
    "noc_closure_certificate": "Customer requests NOC or loan closure certificate.",
    "bureau_reporting_issue": "Customer reports CIBIL/credit bureau reporting problems.",
    "fraud_security_issue": "Customer reports fraud, unauthorized, or suspicious activity.",
    "topup_offer": "Customer asks about top-up or additional loan eligibility.",
    "unknown": "Intent is unclear or unsupported.",
}


def build_intent_classifier_system_prompt() -> str:
    """Build provider-neutral system instruction for intent classification."""
    intent_lines = "\n".join(
        f"- {intent}: {_INTENT_DEFINITIONS[intent]}"
        for intent in ALL_TICKET_INTENTS
    )
    return (
        "You are an intent classifier for a mock digital lending support assistant.\n"
        "Classify the customer message into exactly one primary intent code.\n"
        "Return only structured JSON matching the provided schema.\n"
        "Choose unknown when evidence is insufficient.\n"
        "Provide a short internal reason only; do not include chain-of-thought.\n"
        "Supported intent codes:\n"
        f"{intent_lines}\n"
        f"Prompt version: {INTENT_CLASSIFIER_PROMPT_VERSION}"
    )


def build_intent_classifier_user_prompt(normalized_message: str) -> str:
    """Build the user prompt containing only the normalized customer message."""
    return normalized_message.strip()
