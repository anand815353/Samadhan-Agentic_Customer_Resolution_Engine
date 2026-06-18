"""Service request input and API-safe schemas."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.service_requests.constants import RequestType, ServiceRequestCreatedBy, ServiceRequestStatus
from app.service_requests.id_generation import SERVICE_REQUEST_ID_PATTERN
from app.service_requests.models import ServiceRequestDocument


class ServiceRequestCreate(BaseModel):
    """Input for creating a service request."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ticket_id: str = Field(..., pattern=r"^TKT-\d{4}-\d{4}$")
    customer_id: str
    request_type: RequestType
    customer_safe_summary: str = Field(..., min_length=1)
    loan_id: str | None = None
    created_by: ServiceRequestCreatedBy = "system"
    service_request_id: str | None = Field(default=None, pattern=SERVICE_REQUEST_ID_PATTERN)
    status: ServiceRequestStatus | None = None
    document_path: str | None = None


class ServiceRequestRead(BaseModel):
    """API-safe service request representation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    service_request_id: str
    ticket_id: str
    customer_id: str
    loan_id: str | None = None
    request_type: RequestType
    status: ServiceRequestStatus
    document_path: str | None = None
    customer_safe_summary: str
    created_by: ServiceRequestCreatedBy
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    @classmethod
    def from_document(cls, document: ServiceRequestDocument) -> "ServiceRequestRead":
        return cls(
            service_request_id=document.service_request_id,
            ticket_id=document.ticket_id,
            customer_id=document.customer_id,
            loan_id=document.loan_id,
            request_type=document.request_type,
            status=document.status,
            document_path=document.document_path,
            customer_safe_summary=document.customer_safe_summary,
            created_by=document.created_by,
            created_at=document.created_at,
            updated_at=document.updated_at,
            completed_at=document.completed_at,
        )


def service_document_from_create(
    data: ServiceRequestCreate,
    *,
    service_request_id: str,
    now: datetime | None = None,
) -> ServiceRequestDocument:
    """Build a ServiceRequestDocument from create input."""
    timestamp = now or datetime.now(UTC)
    status = data.status or "created"
    completed_at = timestamp if status == "completed" else None

    return ServiceRequestDocument(
        service_request_id=service_request_id,
        ticket_id=data.ticket_id,
        customer_id=data.customer_id,
        loan_id=data.loan_id,
        request_type=data.request_type,
        status=status,
        document_path=data.document_path,
        customer_safe_summary=data.customer_safe_summary,
        created_by=data.created_by,
        created_at=timestamp,
        updated_at=timestamp,
        completed_at=completed_at,
    )
