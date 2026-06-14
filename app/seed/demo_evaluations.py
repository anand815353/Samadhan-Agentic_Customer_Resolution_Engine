"""Canonical golden evaluation case seed rows for T-020 (aligned with DEMO_GUIDE and AGENT_WORKFLOW).

Seed data only. Evaluation runner and LangGraph workflow are implemented in later tasks.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from app.seed.demo_personas import DEMO_CUSTOMERS, DEMO_SEED_TIMESTAMP
from app.seed.template_spec import SHEET_SPECS_BY_NAME, header_columns

# Stable eval case IDs for major intents and demo personas.
EVAL_LOAN_001 = "EVAL-LOAN-001"
EVAL_LOAN_002 = "EVAL-LOAN-002"
EVAL_REJECT_001 = "EVAL-REJECT-001"
EVAL_REJECT_002 = "EVAL-REJECT-002"
EVAL_KYC_001 = "EVAL-KYC-001"
EVAL_KYC_002 = "EVAL-KYC-002"
EVAL_EMI_001 = "EVAL-EMI-001"
EVAL_EMI_002 = "EVAL-EMI-002"
EVAL_REFUND_001 = "EVAL-REFUND-001"
EVAL_REFUND_002 = "EVAL-REFUND-002"
EVAL_POLICY_001 = "EVAL-POLICY-001"
EVAL_POLICY_002 = "EVAL-POLICY-002"
EVAL_POLICY_003 = "EVAL-POLICY-003"
EVAL_RM_001 = "EVAL-RM-001"
EVAL_STMT_001 = "EVAL-STMT-001"
EVAL_NOC_001 = "EVAL-NOC-001"
EVAL_NOC_002 = "EVAL-NOC-002"
EVAL_BUREAU_001 = "EVAL-BUREAU-001"
EVAL_BUREAU_002 = "EVAL-BUREAU-002"
EVAL_FRAUD_001 = "EVAL-FRAUD-001"
EVAL_FRAUD_002 = "EVAL-FRAUD-002"
EVAL_TOPUP_001 = "EVAL-TOPUP-001"
EVAL_TOPUP_002 = "EVAL-TOPUP-002"
EVAL_UNKNOWN_001 = "EVAL-UNKNOWN-001"
EVAL_UNKNOWN_002 = "EVAL-UNKNOWN-002"

KNOWN_MOCK_TOOLS = frozenset(
    {
        "LoanStatusTool",
        "RejectionReasonTool",
        "KYCDocumentTool",
        "RepaymentTool",
        "TransactionTool",
        "DocumentGenerationTool",
        "BureauReportingTool",
        "FraudSecurityTool",
        "OfferEligibilityTool",
        "RMRedirectTool",
        "PolicyRAGTool",
    }
)

CUSTOMER_IDS = {customer.customer_id for customer in DEMO_CUSTOMERS}

_MIN_INTENT_COUNTS: dict[str, int] = {
    "loan_application_status": 2,
    "rejection_reason": 2,
    "kyc_document_issue": 2,
    "emi_payment_issue": 2,
    "charges_refund_reversal": 2,
    "policy_faq": 3,
    "rm_redirection": 1,
    "loan_statement_request": 1,
    "noc_closure_certificate": 2,
    "bureau_reporting_issue": 2,
    "fraud_security_issue": 2,
    "topup_offer": 2,
    "unknown": 2,
}

_SENSITIVE_INTENTS = frozenset(
    {
        "rejection_reason",
        "emi_payment_issue",
        "charges_refund_reversal",
        "fraud_security_issue",
        "topup_offer",
        "bureau_reporting_issue",
    }
)


def _json_list(values: list[str] | None) -> str | None:
    if values is None:
        return None
    return json.dumps(values)


def _eval_row(
    *,
    eval_case_id: str,
    customer_id: str,
    input_message: str,
    expected_intent: str,
    expected_risk_level: str,
    expected_priority: str,
    expected_ticket_class: str,
    expected_guardrail: str,
    expected_escalation: bool,
    active: bool = True,
    expected_tools: list[str] | None = None,
    expected_response_contains: list[str] | None = None,
    forbidden_response_contains: list[str] | None = None,
    expected_service_request_type: str | None = None,
    expected_source_domain: str | None = None,
) -> dict[str, Any]:
    return {
        "eval_case_id": eval_case_id,
        "customer_id": customer_id,
        "input_message": input_message,
        "expected_intent": expected_intent,
        "expected_risk_level": expected_risk_level,
        "expected_priority": expected_priority,
        "expected_ticket_class": expected_ticket_class,
        "expected_guardrail": expected_guardrail,
        "expected_escalation": expected_escalation,
        "active": active,
        "expected_tools": _json_list(expected_tools),
        "expected_response_contains": _json_list(expected_response_contains),
        "forbidden_response_contains": _json_list(forbidden_response_contains),
        "expected_service_request_type": expected_service_request_type,
        "expected_source_domain": expected_source_domain,
        "created_at": DEMO_SEED_TIMESTAMP,
    }


_EVALUATION_CASES: list[dict[str, Any]] = [
    _eval_row(
        eval_case_id=EVAL_LOAN_001,
        customer_id="CUST-001",
        input_message="Why is my loan still pending?",
        expected_intent="loan_application_status",
        expected_risk_level="medium",
        expected_priority="medium",
        expected_ticket_class="tier_2_conversation",
        expected_guardrail="allow_with_audit",
        expected_escalation=False,
        expected_tools=["LoanStatusTool"],
        expected_response_contains=["pending", "KYC"],
        expected_source_domain="loan_status",
    ),
    _eval_row(
        eval_case_id=EVAL_LOAN_002,
        customer_id="CUST-001",
        input_message="What stage is my loan application in right now?",
        expected_intent="loan_application_status",
        expected_risk_level="medium",
        expected_priority="medium",
        expected_ticket_class="tier_1_service_request",
        expected_guardrail="allow_with_audit",
        expected_escalation=False,
        expected_tools=["LoanStatusTool", "KYCDocumentTool"],
        expected_response_contains=["application", "stage"],
        expected_source_domain="loan_status",
    ),
    _eval_row(
        eval_case_id=EVAL_REJECT_001,
        customer_id="CUST-002",
        input_message="Why was my loan rejected?",
        expected_intent="rejection_reason",
        expected_risk_level="medium",
        expected_priority="medium",
        expected_ticket_class="tier_2_conversation",
        expected_guardrail="allow",
        expected_escalation=False,
        expected_tools=["RejectionReasonTool"],
        expected_response_contains=["rejected"],
        forbidden_response_contains=[
            "internal risk score",
            "model probability",
            "underwriting cutoff",
            "bureau score rule",
        ],
        expected_source_domain="rejection",
    ),
    _eval_row(
        eval_case_id=EVAL_REJECT_002,
        customer_id="CUST-002",
        input_message="I disagree with my loan rejection. Please review it again.",
        expected_intent="rejection_reason",
        expected_risk_level="high",
        expected_priority="high",
        expected_ticket_class="human_review",
        expected_guardrail="escalate",
        expected_escalation=True,
        expected_tools=["RejectionReasonTool"],
        expected_response_contains=["review", "ticket"],
        forbidden_response_contains=["internal model", "raw tool payload"],
        expected_source_domain="rejection",
    ),
    _eval_row(
        eval_case_id=EVAL_KYC_001,
        customer_id="CUST-001",
        input_message="Which KYC document should I upload to continue my application?",
        expected_intent="kyc_document_issue",
        expected_risk_level="medium",
        expected_priority="medium",
        expected_ticket_class="tier_2_conversation",
        expected_guardrail="allow",
        expected_escalation=False,
        expected_tools=["KYCDocumentTool"],
        expected_response_contains=["document", "upload"],
        expected_source_domain="kyc",
    ),
    _eval_row(
        eval_case_id=EVAL_KYC_002,
        customer_id="CUST-001",
        input_message="My bank statement was marked for reupload. What should I do?",
        expected_intent="kyc_document_issue",
        expected_risk_level="medium",
        expected_priority="medium",
        expected_ticket_class="tier_1_service_request",
        expected_guardrail="allow_with_audit",
        expected_escalation=False,
        expected_tools=["KYCDocumentTool", "LoanStatusTool"],
        expected_response_contains=["reupload", "bank statement"],
        expected_source_domain="kyc",
    ),
    _eval_row(
        eval_case_id=EVAL_EMI_001,
        customer_id="CUST-003",
        input_message="My EMI was deducted twice this month.",
        expected_intent="emi_payment_issue",
        expected_risk_level="high",
        expected_priority="high",
        expected_ticket_class="human_review",
        expected_guardrail="escalate",
        expected_escalation=True,
        expected_tools=["RepaymentTool", "TransactionTool"],
        expected_response_contains=["EMI", "human review", "ticket"],
        forbidden_response_contains=["refund completed", "internal risk score"],
        expected_source_domain="emi",
    ),
    _eval_row(
        eval_case_id=EVAL_EMI_002,
        customer_id="CUST-003",
        input_message="I see two EMI debits for April. Can you check my repayment schedule?",
        expected_intent="emi_payment_issue",
        expected_risk_level="high",
        expected_priority="high",
        expected_ticket_class="human_review",
        expected_guardrail="escalate",
        expected_escalation=True,
        expected_tools=["RepaymentTool", "TransactionTool"],
        expected_response_contains=["duplicate", "EMI"],
        forbidden_response_contains=["refund completed", "internal model"],
        expected_source_domain="emi",
    ),
    _eval_row(
        eval_case_id=EVAL_REFUND_001,
        customer_id="CUST-003",
        input_message="I was charged twice. When will my refund be processed?",
        expected_intent="charges_refund_reversal",
        expected_risk_level="high",
        expected_priority="high",
        expected_ticket_class="human_review",
        expected_guardrail="escalate",
        expected_escalation=True,
        expected_tools=["TransactionTool"],
        expected_response_contains=["review", "refund"],
        forbidden_response_contains=["refund completed", "real account frozen"],
        expected_service_request_type="refund_review",
        expected_source_domain="refund",
    ),
    _eval_row(
        eval_case_id=EVAL_REFUND_002,
        customer_id="CUST-004",
        input_message="There is an unexpected charge on my closed loan account. I need a reversal.",
        expected_intent="charges_refund_reversal",
        expected_risk_level="high",
        expected_priority="high",
        expected_ticket_class="human_review",
        expected_guardrail="escalate",
        expected_escalation=True,
        expected_tools=["TransactionTool", "LoanStatusTool"],
        expected_response_contains=["review", "charge"],
        forbidden_response_contains=["refund completed", "loan disbursed"],
        expected_service_request_type="refund_review",
        expected_source_domain="refund",
    ),
    _eval_row(
        eval_case_id=EVAL_POLICY_001,
        customer_id="CUST-010",
        input_message="Can I prepay my loan?",
        expected_intent="policy_faq",
        expected_risk_level="low",
        expected_priority="low",
        expected_ticket_class="tier_2_conversation",
        expected_guardrail="allow",
        expected_escalation=False,
        expected_tools=["PolicyRAGTool"],
        expected_response_contains=["prepay", "policy"],
        expected_source_domain="loan_status",
    ),
    _eval_row(
        eval_case_id=EVAL_POLICY_002,
        customer_id="CUST-001",
        input_message="What documents are accepted for KYC verification?",
        expected_intent="policy_faq",
        expected_risk_level="low",
        expected_priority="low",
        expected_ticket_class="tier_2_conversation",
        expected_guardrail="allow",
        expected_escalation=False,
        expected_tools=["PolicyRAGTool"],
        expected_response_contains=["KYC", "document"],
        expected_source_domain="kyc",
    ),
    _eval_row(
        eval_case_id=EVAL_POLICY_003,
        customer_id="CUST-007",
        input_message="What is the policy for top-up loan offers?",
        expected_intent="policy_faq",
        expected_risk_level="low",
        expected_priority="medium",
        expected_ticket_class="tier_2_conversation",
        expected_guardrail="allow",
        expected_escalation=False,
        expected_tools=["PolicyRAGTool"],
        expected_response_contains=["top-up", "offer"],
        expected_source_domain="topup",
    ),
    _eval_row(
        eval_case_id=EVAL_RM_001,
        customer_id="CUST-009",
        input_message="I want to speak to my relationship manager.",
        expected_intent="rm_redirection",
        expected_risk_level="low",
        expected_priority="medium",
        expected_ticket_class="tier_1_service_request",
        expected_guardrail="allow_with_audit",
        expected_escalation=False,
        expected_tools=["RMRedirectTool"],
        expected_response_contains=["relationship manager", "callback"],
        expected_service_request_type="callback_request",
        expected_source_domain="rm",
    ),
    _eval_row(
        eval_case_id=EVAL_STMT_001,
        customer_id="CUST-010",
        input_message="I need my loan statement for the last financial year for my tax returns.",
        expected_intent="loan_statement_request",
        expected_risk_level="medium",
        expected_priority="medium",
        expected_ticket_class="tier_1_service_request",
        expected_guardrail="allow_with_audit",
        expected_escalation=False,
        expected_tools=["DocumentGenerationTool"],
        expected_response_contains=["statement", "loan"],
        expected_service_request_type="loan_statement",
        expected_source_domain="noc",
    ),
    _eval_row(
        eval_case_id=EVAL_NOC_001,
        customer_id="CUST-004",
        input_message="I closed my loan. Where is my NOC?",
        expected_intent="noc_closure_certificate",
        expected_risk_level="medium",
        expected_priority="medium",
        expected_ticket_class="tier_1_service_request",
        expected_guardrail="allow_with_audit",
        expected_escalation=False,
        expected_tools=["DocumentGenerationTool", "LoanStatusTool"],
        expected_response_contains=["NOC", "closed"],
        expected_service_request_type="noc_request",
        expected_source_domain="noc",
    ),
    _eval_row(
        eval_case_id=EVAL_NOC_002,
        customer_id="CUST-004",
        input_message="Please send my loan closure certificate.",
        expected_intent="noc_closure_certificate",
        expected_risk_level="medium",
        expected_priority="medium",
        expected_ticket_class="tier_1_service_request",
        expected_guardrail="allow_with_audit",
        expected_escalation=False,
        expected_tools=["DocumentGenerationTool"],
        expected_response_contains=["closure", "certificate"],
        expected_service_request_type="noc_request",
        expected_source_domain="noc",
    ),
    _eval_row(
        eval_case_id=EVAL_BUREAU_001,
        customer_id="CUST-005",
        input_message="I paid off my loan two months ago, but it is still showing active on CIBIL.",
        expected_intent="bureau_reporting_issue",
        expected_risk_level="high",
        expected_priority="high",
        expected_ticket_class="tier_1_service_request",
        expected_guardrail="allow_with_audit",
        expected_escalation=False,
        expected_tools=["BureauReportingTool", "DocumentGenerationTool"],
        expected_response_contains=["closed", "bureau", "30"],
        forbidden_response_contains=["real bureau updated", "bureau score rule"],
        expected_service_request_type="closure_letter",
        expected_source_domain="bureau",
    ),
    _eval_row(
        eval_case_id=EVAL_BUREAU_002,
        customer_id="CUST-005",
        input_message="When will my CIBIL record update after loan closure?",
        expected_intent="bureau_reporting_issue",
        expected_risk_level="high",
        expected_priority="high",
        expected_ticket_class="human_review",
        expected_guardrail="escalate",
        expected_escalation=True,
        expected_tools=["BureauReportingTool"],
        expected_response_contains=["reporting", "days"],
        forbidden_response_contains=["real bureau updated", "internal risk score"],
        expected_source_domain="bureau",
    ),
    _eval_row(
        eval_case_id=EVAL_FRAUD_001,
        customer_id="CUST-006",
        input_message="I got an SMS for a transaction I did not make. Block my account.",
        expected_intent="fraud_security_issue",
        expected_risk_level="critical",
        expected_priority="critical",
        expected_ticket_class="human_review",
        expected_guardrail="escalate",
        expected_escalation=True,
        expected_tools=["FraudSecurityTool", "TransactionTool"],
        expected_response_contains=["mock", "escalated", "security"],
        forbidden_response_contains=[
            "real account frozen",
            "account permanently blocked",
        ],
        expected_source_domain="fraud",
    ),
    _eval_row(
        eval_case_id=EVAL_FRAUD_002,
        customer_id="CUST-006",
        input_message="Someone used my account without permission. Freeze it permanently now.",
        expected_intent="fraud_security_issue",
        expected_risk_level="critical",
        expected_priority="critical",
        expected_ticket_class="human_review",
        expected_guardrail="escalate",
        expected_escalation=True,
        expected_tools=["FraudSecurityTool", "TransactionTool"],
        expected_response_contains=["review", "protective"],
        forbidden_response_contains=[
            "account permanently blocked",
            "real account frozen",
            "raw tool payload",
        ],
        expected_source_domain="fraud",
    ),
    _eval_row(
        eval_case_id=EVAL_TOPUP_001,
        customer_id="CUST-007",
        input_message="Am I eligible for another loan?",
        expected_intent="topup_offer",
        expected_risk_level="medium",
        expected_priority="medium",
        expected_ticket_class="tier_2_conversation",
        expected_guardrail="allow",
        expected_escalation=False,
        expected_tools=["OfferEligibilityTool"],
        expected_response_contains=["offer", "pre-approved"],
        forbidden_response_contains=["loan disbursed", "internal model"],
        expected_source_domain="topup",
    ),
    _eval_row(
        eval_case_id=EVAL_TOPUP_002,
        customer_id="CUST-008",
        input_message="Can I get more funds?",
        expected_intent="topup_offer",
        expected_risk_level="medium",
        expected_priority="medium",
        expected_ticket_class="tier_2_conversation",
        expected_guardrail="allow",
        expected_escalation=False,
        expected_tools=["OfferEligibilityTool"],
        expected_response_contains=["no active", "offer"],
        forbidden_response_contains=["loan disbursed", "underwriting cutoff"],
        expected_source_domain="topup",
    ),
    _eval_row(
        eval_case_id=EVAL_UNKNOWN_001,
        customer_id="CUST-010",
        input_message="asdfgh qwerty random gibberish",
        expected_intent="unknown",
        expected_risk_level="low",
        expected_priority="low",
        expected_ticket_class="tier_2_conversation",
        expected_guardrail="ask_follow_up",
        expected_escalation=False,
        expected_tools=[],
        expected_response_contains=["help", "clarify"],
    ),
    _eval_row(
        eval_case_id=EVAL_UNKNOWN_002,
        customer_id="CUST-010",
        input_message="What is the weather in Mumbai today?",
        expected_intent="unknown",
        expected_risk_level="low",
        expected_priority="low",
        expected_ticket_class="tier_2_conversation",
        expected_guardrail="ask_follow_up",
        expected_escalation=False,
        expected_tools=[],
        expected_response_contains=["loan", "support"],
    ),
]


def demo_evaluation_case_rows() -> list[dict[str, Any]]:
    return list(_EVALUATION_CASES)


def demo_evaluation_case_row_values() -> list[list[Any]]:
    columns = header_columns(SHEET_SPECS_BY_NAME["evaluation_cases"])
    return [[row.get(column) for column in columns] for row in demo_evaluation_case_rows()]


def _parse_json_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if isinstance(raw, str):
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return []


def evaluations_alignment_errors() -> list[str]:
    """Validate golden evaluation seed coverage against MVP requirements."""
    errors: list[str] = []

    if len(_EVALUATION_CASES) != 25:
        errors.append("evaluation_cases must contain exactly 25 rows")

    case_ids = [row["eval_case_id"] for row in _EVALUATION_CASES]
    if len(set(case_ids)) != len(case_ids):
        errors.append("duplicate eval_case_id in evaluation_cases")

    intent_counts = Counter(row["expected_intent"] for row in _EVALUATION_CASES)
    for intent, minimum in _MIN_INTENT_COUNTS.items():
        if intent_counts.get(intent, 0) < minimum:
            errors.append(f"intent {intent} needs at least {minimum} cases")

    for row in _EVALUATION_CASES:
        if row.get("customer_id") not in CUSTOMER_IDS:
            errors.append(f"invalid customer_id in eval row: {row.get('eval_case_id')}")
        if row.get("active") is not True:
            errors.append(f"{row['eval_case_id']} must be active")

        tools = _parse_json_list(row.get("expected_tools"))
        for tool in tools:
            if tool not in KNOWN_MOCK_TOOLS:
                errors.append(f"{row['eval_case_id']} has unknown tool: {tool}")

        if row["expected_intent"] in _SENSITIVE_INTENTS:
            forbidden = _parse_json_list(row.get("forbidden_response_contains"))
            if not forbidden:
                errors.append(
                    f"{row['eval_case_id']} must include forbidden_response_contains"
                )

    persona_primary = {
        "loan_application_status": "CUST-001",
        "rejection_reason": "CUST-002",
        "emi_payment_issue": "CUST-003",
        "noc_closure_certificate": "CUST-004",
        "bureau_reporting_issue": "CUST-005",
        "fraud_security_issue": "CUST-006",
        "topup_offer": {"CUST-007", "CUST-008"},
        "rm_redirection": "CUST-009",
        "loan_statement_request": "CUST-010",
    }
    for intent, expected_customer in persona_primary.items():
        matching = [row for row in _EVALUATION_CASES if row["expected_intent"] == intent]
        if not matching:
            continue
        if isinstance(expected_customer, set):
            if not any(row["customer_id"] in expected_customer for row in matching):
                errors.append(f"topup_offer cases must include CUST-007 or CUST-008")
        elif not any(row["customer_id"] == expected_customer for row in matching):
            errors.append(f"{intent} cases must include {expected_customer}")

    return errors
