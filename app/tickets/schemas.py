"""Ticket input and API-safe schemas."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.tickets.constants import (
    CreatedBy,
    Priority,
    RiskLevel,
    SourceChannel,
    TicketClass,
    TicketIntent,
    TicketStatus,
    TransitionActor,
)
from app.tickets.id_generation import TICKET_ID_PATTERN
from app.tickets.lifecycle import default_status_for_class
from app.tickets.models import TicketDocument
from app.tickets.risk_rules import apply_intent_defaults, validate_risk_priority_rules


class TicketCreate(BaseModel):
    """Input for creating a ticket."""

    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: str
    user_id: str
    session_id: str
    intent: TicketIntent
    ticket_class: TicketClass | None = None
    risk_level: RiskLevel | None = None
    priority: Priority | None = None
    status: TicketStatus | None = None
    subject: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    source_channel: SourceChannel = "web_chat"
    ticket_id: str | None = Field(default=None, pattern=TICKET_ID_PATTERN)
    service_request_id: str | None = None
    assigned_agent_id: str | None = None
    escalation_reason: str | None = None
    last_customer_message: str = ""
    last_ai_response: str = ""
    created_by: CreatedBy = "system"


class TicketRead(BaseModel):
    """API-safe ticket representation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ticket_id: str
    customer_id: str
    user_id: str
    session_id: str
    ticket_class: TicketClass
    intent: TicketIntent
    risk_level: RiskLevel
    priority: Priority
    status: TicketStatus
    subject: str
    description: str
    source_channel: SourceChannel
    service_request_id: str | None = None
    assigned_agent_id: str | None = None
    escalation_reason: str | None = None
    closure_reason: str | None = None
    last_customer_message: str
    last_ai_response: str
    created_by: CreatedBy
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None

    @classmethod
    def from_document(cls, document: TicketDocument) -> "TicketRead":
        return cls(
            ticket_id=document.ticket_id,
            customer_id=document.customer_id,
            user_id=document.user_id,
            session_id=document.session_id,
            ticket_class=document.ticket_class,
            intent=document.intent,
            risk_level=document.risk_level,
            priority=document.priority,
            status=document.status,
            subject=document.subject,
            description=document.description,
            source_channel=document.source_channel,
            service_request_id=document.service_request_id,
            assigned_agent_id=document.assigned_agent_id,
            escalation_reason=document.escalation_reason,
            closure_reason=document.closure_reason,
            last_customer_message=document.last_customer_message,
            last_ai_response=document.last_ai_response,
            created_by=document.created_by,
            created_at=document.created_at,
            updated_at=document.updated_at,
            closed_at=document.closed_at,
        )


def ticket_document_from_create(
    data: TicketCreate,
    *,
    ticket_id: str,
    now: datetime | None = None,
) -> TicketDocument:
    """Build a TicketDocument from create input with resolved routing defaults."""
    timestamp = now or datetime.now(UTC)

    ticket_class, risk_level, priority = apply_intent_defaults(
        intent=data.intent,
        ticket_class=data.ticket_class,
        risk_level=data.risk_level,
        priority=data.priority,
    )
    validate_risk_priority_rules(
        intent=data.intent,
        ticket_class=ticket_class,
        risk_level=risk_level,
        priority=priority,
    )

    status = data.status or default_status_for_class(ticket_class)
    escalation_reason = data.escalation_reason
    if status == "escalated_to_human" and not escalation_reason:
        escalation_reason = f"Escalated for intent: {data.intent}"

    closed_at = None
    if status in ("auto_closed", "closed"):
        closed_at = timestamp

    return TicketDocument(
        ticket_id=ticket_id,
        customer_id=data.customer_id,
        user_id=data.user_id,
        session_id=data.session_id,
        ticket_class=ticket_class,
        intent=data.intent,
        risk_level=risk_level,
        priority=priority,
        status=status,
        subject=data.subject,
        description=data.description,
        source_channel=data.source_channel,
        service_request_id=data.service_request_id,
        assigned_agent_id=data.assigned_agent_id,
        escalation_reason=escalation_reason,
        last_customer_message=data.last_customer_message,
        last_ai_response=data.last_ai_response,
        created_by=data.created_by,
        created_at=timestamp,
        updated_at=timestamp,
        closed_at=closed_at,
    )


def resolve_create_actor(created_by: CreatedBy) -> TransitionActor:
    if created_by == "customer":
        return "customer"
    if created_by == "support_agent":
        return "support_agent"
    if created_by == "admin":
        return "admin"
    return "system"
