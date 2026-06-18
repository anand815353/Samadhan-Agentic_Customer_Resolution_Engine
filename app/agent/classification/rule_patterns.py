"""Declarative intent rule patterns for deterministic classification (T-053)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.tickets.constants import TicketIntent

RULE_CLASSIFIER_VERSION = "1.0.0"

RuleKind = Literal["phrase", "keyword"]


@dataclass(frozen=True)
class RuleDefinition:
    """Single deterministic match rule."""

    rule_id: str
    intent: TicketIntent
    pattern: str
    weight: float
    kind: RuleKind = "phrase"


@dataclass(frozen=True)
class ExclusionDefinition:
    """Penalize an intent when a conflicting cue is present."""

    rule_id: str
    penalized_intent: TicketIntent
    conflict_pattern: str
    penalty: float


# Safety-aware intent precedence for tie-breaking (highest first).
INTENT_PRECEDENCE: tuple[TicketIntent, ...] = (
    "fraud_security_issue",
    "emi_payment_issue",
    "charges_refund_reversal",
    "bureau_reporting_issue",
    "rejection_reason",
    "noc_closure_certificate",
    "loan_statement_request",
    "kyc_document_issue",
    "rm_redirection",
    "topup_offer",
    "loan_application_status",
    "policy_faq",
    "unknown",
)

_INTENT_PRECEDENCE_RANK: dict[TicketIntent, int] = {
    intent: index for index, intent in enumerate(INTENT_PRECEDENCE)
}

RULE_DEFINITIONS: tuple[RuleDefinition, ...] = (
    # fraud_security_issue
    RuleDefinition("fraud-phrase-001", "fraud_security_issue", "fraud", 0.85, "keyword"),
    RuleDefinition("fraud-phrase-002", "fraud_security_issue", "unauthorized", 0.90, "keyword"),
    RuleDefinition("fraud-phrase-003", "fraud_security_issue", "suspicious transaction", 1.0, "phrase"),
    RuleDefinition("fraud-phrase-004", "fraud_security_issue", "did not make", 0.95, "phrase"),
    RuleDefinition("fraud-phrase-005", "fraud_security_issue", "transaction i did not make", 1.0, "phrase"),
    RuleDefinition("fraud-phrase-006", "fraud_security_issue", "block my account", 0.95, "phrase"),
    RuleDefinition("fraud-phrase-007", "fraud_security_issue", "stolen credentials", 1.0, "phrase"),
    RuleDefinition("fraud-phrase-008", "fraud_security_issue", "unknown transaction", 0.90, "phrase"),
  # emi_payment_issue
    RuleDefinition("emi-phrase-001", "emi_payment_issue", "emi deducted twice", 1.0, "phrase"),
    RuleDefinition("emi-phrase-002", "emi_payment_issue", "double emi", 1.0, "phrase"),
    RuleDefinition("emi-phrase-003", "emi_payment_issue", "duplicate debit", 0.95, "phrase"),
    RuleDefinition("emi-phrase-004", "emi_payment_issue", "emi not reflected", 0.90, "phrase"),
    RuleDefinition("emi-phrase-005", "emi_payment_issue", "emi payment failed", 0.90, "phrase"),
    RuleDefinition("emi-phrase-006", "emi_payment_issue", "installment issue", 0.85, "phrase"),
    RuleDefinition("emi-kw-001", "emi_payment_issue", " emi ", 0.50, "keyword"),
    RuleDefinition("emi-kw-001", "emi_payment_issue", "duplicate emi", 0.95, "phrase"),
  # charges_refund_reversal
    RuleDefinition("refund-phrase-001", "charges_refund_reversal", "refund not received", 1.0, "phrase"),
    RuleDefinition("refund-phrase-002", "charges_refund_reversal", "processing fee charged twice", 1.0, "phrase"),
    RuleDefinition("refund-phrase-003", "charges_refund_reversal", "duplicate fee", 0.95, "phrase"),
    RuleDefinition("refund-phrase-004", "charges_refund_reversal", "extra charge", 0.85, "phrase"),
    RuleDefinition("refund-kw-001", "charges_refund_reversal", "refund", 0.70, "keyword"),
    RuleDefinition("refund-kw-002", "charges_refund_reversal", "reversal", 0.75, "keyword"),
  # bureau_reporting_issue
    RuleDefinition("bureau-phrase-001", "bureau_reporting_issue", "closed loan showing active", 1.0, "phrase"),
    RuleDefinition("bureau-phrase-002", "bureau_reporting_issue", "loan still active", 0.90, "phrase"),
    RuleDefinition("bureau-phrase-003", "bureau_reporting_issue", "bureau not updated", 0.95, "phrase"),
    RuleDefinition("bureau-phrase-004", "bureau_reporting_issue", "credit report", 0.80, "phrase"),
    RuleDefinition("bureau-kw-001", "bureau_reporting_issue", "cibil", 0.85, "keyword"),
    RuleDefinition("bureau-kw-002", "bureau_reporting_issue", "credit bureau", 0.90, "phrase"),
    RuleDefinition("bureau-kw-003", "bureau_reporting_issue", "still active", 0.80, "phrase"),
  # rejection_reason
    RuleDefinition("reject-phrase-001", "rejection_reason", "why was my loan rejected", 1.0, "phrase"),
    RuleDefinition("reject-phrase-002", "rejection_reason", "rejection reason", 0.95, "phrase"),
    RuleDefinition("reject-phrase-003", "rejection_reason", "loan rejected", 0.95, "phrase"),
    RuleDefinition("reject-phrase-004", "rejection_reason", "loan rejection", 0.95, "phrase"),
    RuleDefinition("reject-phrase-005", "rejection_reason", "loan was rejected", 0.95, "phrase"),
    RuleDefinition("reject-kw-001", "rejection_reason", "rejected", 0.80, "keyword"),
    RuleDefinition("reject-kw-002", "rejection_reason", "declined", 0.75, "keyword"),
    RuleDefinition("reject-kw-003", "rejection_reason", "not approved", 0.80, "phrase"),
  # noc_closure_certificate
    RuleDefinition("noc-phrase-001", "noc_closure_certificate", "no objection certificate", 1.0, "phrase"),
    RuleDefinition("noc-phrase-002", "noc_closure_certificate", "closure certificate", 0.95, "phrase"),
    RuleDefinition("noc-phrase-003", "noc_closure_certificate", "loan closure letter", 0.95, "phrase"),
    RuleDefinition("noc-phrase-004", "noc_closure_certificate", "closed loan certificate", 0.95, "phrase"),
    RuleDefinition("noc-kw-001", "noc_closure_certificate", "noc", 0.85, "keyword"),
  # loan_statement_request
    RuleDefinition("stmt-phrase-001", "loan_statement_request", "loan statement", 1.0, "phrase"),
    RuleDefinition("stmt-phrase-002", "loan_statement_request", "account statement", 0.95, "phrase"),
    RuleDefinition("stmt-phrase-003", "loan_statement_request", "repayment statement", 0.95, "phrase"),
    RuleDefinition("stmt-phrase-004", "loan_statement_request", "tax filing", 0.85, "phrase"),
    RuleDefinition("stmt-phrase-005", "loan_statement_request", "financial year statement", 1.0, "phrase"),
  # kyc_document_issue
    RuleDefinition("kyc-phrase-001", "kyc_document_issue", "kyc failed", 0.95, "phrase"),
    RuleDefinition("kyc-phrase-002", "kyc_document_issue", "document rejected", 0.90, "phrase"),
    RuleDefinition("kyc-phrase-003", "kyc_document_issue", "upload document", 0.85, "phrase"),
    RuleDefinition("kyc-phrase-004", "kyc_document_issue", "verification failed", 0.90, "phrase"),
    RuleDefinition("kyc-phrase-005", "kyc_document_issue", "re-upload", 0.85, "keyword"),
    RuleDefinition("kyc-phrase-006", "kyc_document_issue", "unclear document", 0.90, "phrase"),
    RuleDefinition("kyc-kw-001", "kyc_document_issue", "kyc", 0.65, "keyword"),
  # rm_redirection
    RuleDefinition("rm-phrase-001", "rm_redirection", "relationship manager", 0.95, "phrase"),
    RuleDefinition("rm-phrase-002", "rm_redirection", "speak to manager", 0.90, "phrase"),
    RuleDefinition("rm-phrase-003", "rm_redirection", "contact my rm", 0.95, "phrase"),
    RuleDefinition("rm-kw-001", "rm_redirection", "callback", 0.70, "keyword"),
    RuleDefinition("rm-kw-002", "rm_redirection", " rm ", 0.75, "keyword"),
  # topup_offer
    RuleDefinition("topup-phrase-001", "topup_offer", "pre-approved offer", 1.0, "phrase"),
    RuleDefinition("topup-phrase-002", "topup_offer", "additional loan", 0.90, "phrase"),
    RuleDefinition("topup-phrase-003", "topup_offer", "increase my loan", 0.90, "phrase"),
    RuleDefinition("topup-phrase-004", "topup_offer", "more funds", 0.85, "phrase"),
    RuleDefinition("topup-kw-001", "topup_offer", "top-up", 0.90, "keyword"),
    RuleDefinition("topup-kw-002", "topup_offer", "topup", 0.90, "keyword"),
    RuleDefinition("topup-kw-003", "topup_offer", "top up", 0.90, "phrase"),
    RuleDefinition("topup-kw-003", "topup_offer", "another loan", 0.85, "phrase"),
  # loan_application_status
    RuleDefinition("loan-phrase-001", "loan_application_status", "application status", 0.90, "phrase"),
    RuleDefinition("loan-phrase-002", "loan_application_status", "loan status", 0.90, "phrase"),
    RuleDefinition("loan-phrase-003", "loan_application_status", "pending loan", 0.90, "phrase"),
    RuleDefinition("loan-phrase-004", "loan_application_status", "approved yet", 0.85, "phrase"),
    RuleDefinition("loan-phrase-005", "loan_application_status", "under review", 0.85, "phrase"),
    RuleDefinition("loan-phrase-006", "loan_application_status", "where is my application", 0.95, "phrase"),
    RuleDefinition("loan-phrase-007", "loan_application_status", "loan still pending", 0.95, "phrase"),
    RuleDefinition("loan-phrase-008", "loan_application_status", "loan application", 0.75, "phrase"),
    RuleDefinition("loan-kw-001", "loan_application_status", "pending", 0.55, "keyword"),
  # policy_faq
    RuleDefinition("policy-phrase-001", "policy_faq", "foreclosure charges", 0.95, "phrase"),
    RuleDefinition("policy-phrase-002", "policy_faq", "part payment", 0.90, "phrase"),
    RuleDefinition("policy-phrase-003", "policy_faq", "eligibility policy", 0.95, "phrase"),
    RuleDefinition("policy-phrase-004", "policy_faq", "policy for", 0.95, "phrase"),
    RuleDefinition("policy-phrase-005", "policy_faq", "policy for top", 1.0, "phrase"),
    RuleDefinition("policy-kw-001", "policy_faq", "prepayment", 0.85, "keyword"),
    RuleDefinition("policy-kw-002", "policy_faq", "prepay", 0.80, "keyword"),
)

EXCLUSION_DEFINITIONS: tuple[ExclusionDefinition, ...] = (
    ExclusionDefinition(
        "excl-loan-vs-reject",
        "loan_application_status",
        "reject",
        0.60,
    ),
    ExclusionDefinition(
        "excl-loan-vs-reject-2",
        "loan_application_status",
        "declined",
        0.55,
    ),
    ExclusionDefinition(
        "excl-policy-vs-stmt",
        "policy_faq",
        "loan statement",
        0.70,
    ),
    ExclusionDefinition(
        "excl-policy-vs-noc",
        "policy_faq",
        "noc",
        0.70,
    ),
    ExclusionDefinition(
        "excl-refund-vs-fraud",
        "charges_refund_reversal",
        "fraud",
        0.50,
    ),
    ExclusionDefinition(
        "excl-topup-vs-policy-for",
        "topup_offer",
        "policy for",
        0.85,
    ),
)


def intent_precedence_rank(intent: TicketIntent) -> int:
    """Lower rank value means higher precedence."""
    return _INTENT_PRECEDENCE_RANK.get(intent, len(INTENT_PRECEDENCE))
