"""Typed contracts for deterministic resolution planning (T-060)."""

from __future__ import annotations

from typing import Literal

RESOLUTION_PLANNER_POLICY_VERSION = "1.0.0"
MAX_ESCALATION_REASON_LENGTH = 200

CustomerAction = Literal[
    "no_action_required",
    "wait_for_support_agent",
    "wait_for_service_completion",
    "provide_more_information",
    "upload_clear_document",
    "check_documents_section",
    "review_policy_information",
    "contact_support_if_not_updated",
    "decide_whether_to_proceed_with_offer",
]

SystemAction = Literal[
    "information_checked",
    "policy_context_retrieved",
    "service_request_created",
    "mock_document_generated",
    "mock_callback_requested",
    "reversal_review_created",
    "mock_fraud_action_recorded",
    "eligibility_checked",
    "prepare_auto_resolution",
    "prepare_service_ticket_update",
    "prepare_human_escalation",
    "request_more_information",
    "safe_no_answer_available",
    "blocked_action_requires_review",
]

CustomerResponseType = Literal[
    "explain_information",
    "explain_policy",
    "explain_and_escalate",
    "confirm_service_request",
    "confirm_mock_document",
    "request_more_information",
    "explain_safe_failure",
    "explain_no_approved_answer",
    "explain_offer_eligibility",
]

ALL_CUSTOMER_ACTIONS: tuple[CustomerAction, ...] = (
    "no_action_required",
    "wait_for_support_agent",
    "wait_for_service_completion",
    "provide_more_information",
    "upload_clear_document",
    "check_documents_section",
    "review_policy_information",
    "contact_support_if_not_updated",
    "decide_whether_to_proceed_with_offer",
)

ALL_SYSTEM_ACTIONS: tuple[SystemAction, ...] = (
    "information_checked",
    "policy_context_retrieved",
    "service_request_created",
    "mock_document_generated",
    "mock_callback_requested",
    "reversal_review_created",
    "mock_fraud_action_recorded",
    "eligibility_checked",
    "prepare_auto_resolution",
    "prepare_service_ticket_update",
    "prepare_human_escalation",
    "request_more_information",
    "safe_no_answer_available",
    "blocked_action_requires_review",
)

ALL_CUSTOMER_RESPONSE_TYPES: tuple[CustomerResponseType, ...] = (
    "explain_information",
    "explain_policy",
    "explain_and_escalate",
    "confirm_service_request",
    "confirm_mock_document",
    "request_more_information",
    "explain_safe_failure",
    "explain_no_approved_answer",
    "explain_offer_eligibility",
)

DOCUMENT_COMPLETED_ACTIONS: frozenset[str] = frozenset(
    {
        "loan_statement_generated",
        "noc_generated",
        "closure_letter_generated",
    }
)

SERVICE_REQUEST_CREATED_ACTIONS: frozenset[str] = frozenset(
    {
        "loan_statement_requested",
        "noc_request_created",
        "closure_letter_requested",
        "kyc_reupload_requested",
        "rm_callback_requested",
        "reversal_review_created",
        "bureau_closure_letter_requested",
    }
)

MANDATORY_ESCALATE_INTENTS: frozenset[str] = frozenset(
    {
        "fraud_security_issue",
        "emi_payment_issue",
        "charges_refund_reversal",
    }
)
