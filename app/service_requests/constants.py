"""Service request domain constants aligned with DATA_MODEL §8.1."""

from typing import Literal

SERVICE_REQUESTS_COLLECTION = "service_requests"

RequestType = Literal[
    "loan_statement",
    "noc_request",
    "closure_letter",
    "rm_callback",
    "kyc_reupload",
    "bureau_closure_letter",
]

ServiceRequestStatus = Literal[
    "created",
    "in_progress",
    "completed",
    "failed",
    "cancelled",
]

ServiceRequestCreatedBy = Literal["system", "customer", "agent", "admin"]
ServiceRequestActor = Literal["system", "customer", "agent", "admin"]

ALL_REQUEST_TYPES: tuple[RequestType, ...] = (
    "loan_statement",
    "noc_request",
    "closure_letter",
    "rm_callback",
    "kyc_reupload",
    "bureau_closure_letter",
)

ALL_SERVICE_REQUEST_STATUSES: tuple[ServiceRequestStatus, ...] = (
    "created",
    "in_progress",
    "completed",
    "failed",
    "cancelled",
)

TERMINAL_SR_STATUSES: frozenset[str] = frozenset({"completed", "failed", "cancelled"})

LOAN_REQUIRED_REQUEST_TYPES: frozenset[str] = frozenset(
    {
        "loan_statement",
        "noc_request",
        "closure_letter",
        "bureau_closure_letter",
    }
)

INTENT_TO_REQUEST_TYPE: dict[str, RequestType] = {
    "loan_statement_request": "loan_statement",
    "noc_closure_certificate": "noc_request",
    "rm_redirection": "rm_callback",
    "kyc_document_issue": "kyc_reupload",
    "bureau_reporting_issue": "bureau_closure_letter",
}

LOAN_ID_PATTERN = r"^LN-\d{4}-\d{4}$"
