"""Shared types for deterministic guardrail evaluation (T-058)."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.constants import GuardrailDecision

GUARDRAIL_POLICY_VERSION = "1.0.0"
MAX_GUARDRAIL_REASON_LENGTH = 200

# Semantic action tokens for resolution planner / T-059 (stable identifiers).
ACTION_INSPECT_LOAN_STATUS = "inspect_loan_status"
ACTION_INSPECT_KYC_DOCUMENTS = "inspect_kyc_documents"
ACTION_SHARE_CUSTOMER_SAFE_REJECTION = "share_customer_safe_rejection_reason"
ACTION_INSPECT_REPAYMENT_SCHEDULE = "inspect_repayment_schedule"
ACTION_INSPECT_TRANSACTIONS = "inspect_transactions"
ACTION_PREPARE_FRAUD_CASE = "prepare_fraud_case"
ACTION_RECORD_MOCK_FREEZE_REFERENCE = "record_mock_freeze_reference"
ACTION_PREPARE_REVERSAL_REVIEW = "prepare_reversal_review"
ACTION_RETRIEVE_POLICY = "retrieve_policy"
ACTION_PREPARE_RM_CALLBACK = "prepare_rm_callback"
ACTION_GENERATE_MOCK_DOCUMENT = "generate_mock_document"
ACTION_CHECK_OFFER_ELIGIBILITY = "check_offer_eligibility"
ACTION_INSPECT_BUREAU_REPORTING = "inspect_bureau_reporting"
ACTION_CREATE_HUMAN_REVIEW_TICKET = "create_human_review_ticket"

TOOL_TO_ALLOWED_ACTIONS: dict[str, tuple[str, ...]] = {
    "LoanStatusTool": (ACTION_INSPECT_LOAN_STATUS,),
    "KYCDocumentTool": (ACTION_INSPECT_KYC_DOCUMENTS,),
    "RejectionReasonTool": (ACTION_SHARE_CUSTOMER_SAFE_REJECTION,),
    "RepaymentTool": (ACTION_INSPECT_REPAYMENT_SCHEDULE,),
    "TransactionTool": (ACTION_INSPECT_TRANSACTIONS, ACTION_PREPARE_REVERSAL_REVIEW),
    "FraudSecurityTool": (ACTION_PREPARE_FRAUD_CASE, ACTION_RECORD_MOCK_FREEZE_REFERENCE),
    "PolicyRAGTool": (ACTION_RETRIEVE_POLICY,),
    "RMRedirectTool": (ACTION_PREPARE_RM_CALLBACK,),
    "DocumentGenerationTool": (ACTION_GENERATE_MOCK_DOCUMENT,),
    "BureauReportingTool": (ACTION_INSPECT_BUREAU_REPORTING,),
    "OfferEligibilityTool": (ACTION_CHECK_OFFER_ELIGIBILITY,),
}


@dataclass(frozen=True)
class GuardrailEvaluationResult:
    """Outcome of deterministic guardrail policy evaluation."""

    decision: GuardrailDecision
    reason: str
    escalation_required: bool
    allowed_actions: tuple[str, ...] = ()
    approved_step_indexes: tuple[int, ...] = ()
    blocked_step_indexes: tuple[int, ...] = ()
    conditional_step_indexes: tuple[int, ...] = ()
    policy_version: str = GUARDRAIL_POLICY_VERSION
