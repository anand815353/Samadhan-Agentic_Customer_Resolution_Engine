"""Audit log input and API-safe schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.audit.constants import AuditCreatedBy, AuditEventType
from app.audit.id_generation import AUDIT_ID_PATTERN
from app.audit.models import AuditLogDocument
from app.tickets.constants import Priority, RiskLevel, TicketIntent


class AuditEventCreate(BaseModel):
    """Input for creating an audit log event."""

    model_config = ConfigDict(str_strip_whitespace=True)

    event_type: AuditEventType
    audit_id: str | None = Field(default=None, pattern=AUDIT_ID_PATTERN)

    ticket_id: str | None = Field(default=None, pattern=r"^TKT-\d{4}-\d{4}$")
    message_id: str | None = Field(default=None, pattern=r"^MSG-\d{4}-\d{4}$")
    customer_id: str | None = None
    intent: TicketIntent | None = None
    risk_level: RiskLevel | None = None
    priority: Priority | None = None
    tool_called: str | None = None
    tool_name: str | None = None
    tool_input_masked: dict[str, Any] | str | None = None
    tool_output_summary: dict[str, Any] | str | None = None
    retrieved_policy_ids: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    action_taken: str | None = None
    customer_safe_summary: str | None = None
    raw_internal_trace: dict[str, Any] | None = None
    langsmith_trace_id: str | None = None

    user_id: str | None = None
    session_id: str | None = None
    service_request_id: str | None = Field(default=None, pattern=r"^SR-\d{4}-\d{4}$")
    workflow_id: str | None = None
    created_by: AuditCreatedBy | None = None
    decision: dict[str, Any] | str | None = None
    escalation_required: bool | None = None
    internal_summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_tool_name(self) -> AuditEventCreate:
        if self.tool_called is None and self.tool_name is not None:
            object.__setattr__(self, "tool_called", self.tool_name)
        return self


class AuditEventRead(BaseModel):
    """API-safe audit event representation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    audit_id: str
    event_type: AuditEventType
    created_at: datetime
    ticket_id: str | None = None
    message_id: str | None = None
    customer_id: str | None = None
    intent: TicketIntent | None = None
    risk_level: RiskLevel | None = None
    priority: Priority | None = None
    tool_called: str | None = None
    tool_input_masked: dict[str, Any] | str | None = None
    tool_output_summary: dict[str, Any] | str | None = None
    retrieved_policy_ids: list[str] = Field(default_factory=list)
    confidence: float | None = None
    action_taken: str | None = None
    customer_safe_summary: str | None = None
    langsmith_trace_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    service_request_id: str | None = None
    workflow_id: str | None = None
    created_by: AuditCreatedBy | None = None
    decision: dict[str, Any] | str | None = None
    escalation_required: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw_internal_trace: dict[str, Any] | None = None
    internal_summary: str | None = None

    @classmethod
    def from_document(
        cls,
        document: AuditLogDocument,
        *,
        include_internal: bool = False,
    ) -> AuditEventRead:
        payload = document.model_dump()
        if not include_internal:
            payload.pop("raw_internal_trace", None)
            payload.pop("internal_summary", None)
        return cls(**payload)


def audit_document_from_create(
    data: AuditEventCreate,
    *,
    audit_id: str,
    now: datetime | None = None,
) -> AuditLogDocument:
    """Build an AuditLogDocument from create input."""
    timestamp = now or datetime.now(UTC)
    return AuditLogDocument(
        audit_id=audit_id,
        event_type=data.event_type,
        created_at=timestamp,
        ticket_id=data.ticket_id,
        message_id=data.message_id,
        customer_id=data.customer_id,
        intent=data.intent,
        risk_level=data.risk_level,
        priority=data.priority,
        tool_called=data.tool_called,
        tool_input_masked=data.tool_input_masked,
        tool_output_summary=data.tool_output_summary,
        retrieved_policy_ids=list(data.retrieved_policy_ids),
        confidence=data.confidence,
        action_taken=data.action_taken,
        customer_safe_summary=data.customer_safe_summary,
        raw_internal_trace=data.raw_internal_trace,
        langsmith_trace_id=data.langsmith_trace_id,
        user_id=data.user_id,
        session_id=data.session_id,
        service_request_id=data.service_request_id,
        workflow_id=data.workflow_id,
        created_by=data.created_by,
        decision=data.decision,
        escalation_required=data.escalation_required,
        internal_summary=data.internal_summary,
        metadata=dict(data.metadata),
    )
