"""Mock tool domain constants aligned with MOCK_TOOLS_SPEC."""

from typing import Literal

ToolName = Literal[
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
]

ALL_TOOL_NAMES: tuple[ToolName, ...] = (
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
)

ToolErrorCode = Literal[
    "validation_failed",
    "not_found",
    "execution_failed",
    "audit_failed",
    "unexpected_error",
]

FORBIDDEN_ACTION_TOKENS: frozenset[str] = frozenset(
    {
        "disbursed",
        "refunded",
        "frozen",
        "approved_kyc",
        "bureau_updated",
        "refund_completed",
        "reversal_completed",
        "account_frozen",
        "kyc_approved",
    }
)
