"""Service request persistence models aligned with DATA_MODEL §8.1."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.service_requests.constants import (
    LOAN_ID_PATTERN,
    LOAN_REQUIRED_REQUEST_TYPES,
    TERMINAL_SR_STATUSES,
    RequestType,
    ServiceRequestCreatedBy,
    ServiceRequestStatus,
)
from app.service_requests.id_generation import (
    SERVICE_REQUEST_ID_PATTERN,
    validate_service_request_id,
)

TICKET_ID_PATTERN = r"^TKT-\d{4}-\d{4}$"
CUSTOMER_ID_PATTERN = r"^CUST-\d{3}$"


class ServiceRequestDocument(BaseModel):
    """MongoDB service_requests collection document."""

    model_config = ConfigDict(str_strip_whitespace=True)

    service_request_id: str = Field(..., pattern=SERVICE_REQUEST_ID_PATTERN)
    ticket_id: str = Field(..., pattern=TICKET_ID_PATTERN)
    customer_id: str = Field(..., pattern=CUSTOMER_ID_PATTERN)
    loan_id: str | None = Field(default=None, pattern=LOAN_ID_PATTERN)
    request_type: RequestType
    status: ServiceRequestStatus
    document_path: str | None = None
    customer_safe_summary: str = Field(..., min_length=1)
    created_by: ServiceRequestCreatedBy = "system"
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    @field_validator("loan_id")
    @classmethod
    def validate_loan_id_format(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("loan_id must be null or non-empty")
        return value

    @model_validator(mode="after")
    def validate_cross_field_rules(self) -> "ServiceRequestDocument":
        if not validate_service_request_id(self.service_request_id):
            raise ValueError("invalid service_request_id format")

        if self.request_type in LOAN_REQUIRED_REQUEST_TYPES and not self.loan_id:
            raise ValueError(f"loan_id required for request_type '{self.request_type}'")

        if self.status == "completed" and self.completed_at is None:
            raise ValueError("completed_at required when status is completed")

        if self.status != "completed" and self.completed_at is not None:
            raise ValueError("completed_at must be null unless status is completed")

        if self.status in TERMINAL_SR_STATUSES and self.status != "completed":
            if self.completed_at is not None:
                raise ValueError("completed_at must be null for failed/cancelled statuses")

        return self

    def to_mongo_dict(self) -> dict[str, object]:
        """Serialize for MongoDB insert/update."""
        return self.model_dump(mode="json")
