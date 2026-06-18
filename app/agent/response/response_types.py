"""Typed contracts for customer response generation (T-061)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RESPONSE_PROMPT_VERSION = "1.0.0"
RESPONSE_MAX_CHARACTERS = 2000
RESPONSE_MAX_SNIPPET_CHARACTERS = 300
RESPONSE_MAX_POLICY_SNIPPETS = 2
RESPONSE_MAX_CUSTOMER_EXCERPT = 200
RESPONSE_LLM_MAX_OUTPUT_TOKENS = 512

ResponseGenerationSource = Literal["llm", "deterministic_template"]
ResponseSafetyStatus = Literal["passed", "fallback_used"]

MOCK_DISCLAIMER_SYSTEM_ACTIONS: frozenset[str] = frozenset(
    {
        "mock_fraud_action_recorded",
        "mock_document_generated",
        "mock_callback_requested",
        "reversal_review_created",
        "service_request_created",
    }
)

MOCK_DISCLAIMER_INTENTS: frozenset[str] = frozenset(
    {
        "fraud_security_issue",
        "emi_payment_issue",
        "charges_refund_reversal",
        "bureau_reporting_issue",
        "topup_offer",
    }
)

DOCUMENT_COMPLETED_ACTIONS: frozenset[str] = frozenset(
    {
        "loan_statement_generated",
        "noc_generated",
        "closure_letter_generated",
    }
)

FORBIDDEN_INTERNAL_PHRASES: tuple[str, ...] = (
    "internal risk score",
    "risk score",
    "model probability",
    "underwriting cutoff",
    "bureau score rule",
    "raw tool payload",
    "raw tool",
    "guardrail blocked",
    "langsmith",
    "trace id",
    "system prompt",
    "chain-of-thought",
)

FORBIDDEN_REAL_ACTION_PHRASES: tuple[str, ...] = (
    "refund completed",
    "refund has been completed",
    "reversal completed",
    "transaction was reversed",
    "amount has been credited",
    "money has been credited",
    "account has been frozen",
    "card is blocked",
    "card has been blocked",
    "loan is approved",
    "loan has been approved",
    "funds will be disbursed",
    "loan disbursed",
    "cibil corrected",
    "cibil has been corrected",
    "bureau has accepted",
    "bureau updated",
    "real bureau updated",
    "kyc is approved",
    "kyc has been approved",
    "legally binding",
    "bank has secured",
)

SUCCESS_CLAIM_PHRASES: tuple[str, ...] = (
    "has been completed",
    "was completed",
    "successfully completed",
    "has been processed",
    "was processed",
    "has been credited",
    "was credited",
    "has been reversed",
    "was reversed",
    "has been approved",
    "was approved",
    "has been disbursed",
    "was disbursed",
    "has been frozen",
    "was frozen",
    "has been corrected",
    "was corrected",
)


@dataclass(frozen=True)
class ResponseGenerationResult:
    """Internal result from response generation service."""

    response_text: str
    generation_source: ResponseGenerationSource
    prompt_version: str
    safety_status: ResponseSafetyStatus
    referenced_ticket_id: str | None
    referenced_service_request_ids: tuple[str, ...]
    referenced_source_ids: tuple[str, ...]
    fallback_reason: str | None
    mock_disclaimer_included: bool
