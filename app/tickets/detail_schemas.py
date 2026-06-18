"""Ticket detail aggregate read schemas (T-026)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from app.tickets.constants import TicketClass, TicketIntent, TicketStatus
from app.tickets.models import TicketDocument
from app.tickets.schemas import TicketRead

if TYPE_CHECKING:
    from app.audit.models import AuditLogDocument
    from app.messages.models import MessageDocument
    from app.service_requests.models import ServiceRequestDocument


class TicketDetailCounts(BaseModel):
    """Summary counts for a ticket detail view."""

    message_count: int
    audit_event_count: int
    has_service_request: bool


class TicketDetailRead(BaseModel):
    """Full ticket-centric detail for internal/agent views."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ticket: TicketRead
    messages: list[Any]
    service_request: Any | None = None
    audit_events: list[Any] = Field(default_factory=list)
    counts: TicketDetailCounts
    retrieved_at: datetime

    @classmethod
    def from_parts(
        cls,
        *,
        ticket: TicketDocument,
        messages: list[MessageDocument],
        service_request: ServiceRequestDocument | None,
        audit_events: list[AuditLogDocument],
        retrieved_at: datetime | None = None,
        include_internal_audit: bool = False,
    ) -> TicketDetailRead:
        from app.audit.schemas import AuditEventRead
        from app.messages.schemas import MessageRead
        from app.service_requests.schemas import ServiceRequestRead

        timestamp = retrieved_at or datetime.now(UTC)
        message_reads = [MessageRead.from_document(document) for document in messages]
        audit_reads = [
            AuditEventRead.from_document(document, include_internal=include_internal_audit)
            for document in audit_events
        ]
        sr_read = (
            ServiceRequestRead.from_document(service_request) if service_request is not None else None
        )
        return cls(
            ticket=TicketRead.from_document(ticket),
            messages=message_reads,
            service_request=sr_read,
            audit_events=audit_reads,
            counts=TicketDetailCounts(
                message_count=len(message_reads),
                audit_event_count=len(audit_reads),
                has_service_request=service_request is not None,
            ),
            retrieved_at=timestamp,
        )


class CustomerTicketRead(BaseModel):
    """Customer-safe ticket subset without internal routing fields."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ticket_id: str
    customer_id: str
    session_id: str
    ticket_class: TicketClass
    intent: TicketIntent
    status: TicketStatus
    subject: str
    description: str
    service_request_id: str | None = None
    last_customer_message: str
    last_ai_response: str
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None

    @classmethod
    def from_document(cls, document: TicketDocument) -> CustomerTicketRead:
        return cls(
            ticket_id=document.ticket_id,
            customer_id=document.customer_id,
            session_id=document.session_id,
            ticket_class=document.ticket_class,
            intent=document.intent,
            status=document.status,
            subject=document.subject,
            description=document.description,
            service_request_id=document.service_request_id,
            last_customer_message=document.last_customer_message,
            last_ai_response=document.last_ai_response,
            created_at=document.created_at,
            updated_at=document.updated_at,
            closed_at=document.closed_at,
        )


class CustomerTicketDetailRead(BaseModel):
    """Customer-safe ticket detail without audit trail."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ticket: CustomerTicketRead
    messages: list[Any]
    service_request: Any | None = None
    counts: TicketDetailCounts
    retrieved_at: datetime

    @classmethod
    def from_parts(
        cls,
        *,
        ticket: TicketDocument,
        messages: list[MessageDocument],
        service_request: ServiceRequestDocument | None,
        retrieved_at: datetime | None = None,
    ) -> CustomerTicketDetailRead:
        from app.messages.schemas import MessageRead
        from app.service_requests.schemas import ServiceRequestRead

        timestamp = retrieved_at or datetime.now(UTC)
        message_reads = [MessageRead.from_document(document) for document in messages]
        sr_read = (
            ServiceRequestRead.from_document(service_request) if service_request is not None else None
        )
        return cls(
            ticket=CustomerTicketRead.from_document(ticket),
            messages=message_reads,
            service_request=sr_read,
            counts=TicketDetailCounts(
                message_count=len(message_reads),
                audit_event_count=0,
                has_service_request=service_request is not None,
            ),
            retrieved_at=timestamp,
        )
