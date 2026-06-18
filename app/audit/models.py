"""Audit log persistence models aligned with DATA_MODEL §10.1."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.audit.constants import AuditCreatedBy, AuditEventType
from app.audit.id_generation import AUDIT_ID_PATTERN, validate_audit_id
from app.messages.id_generation import MESSAGE_ID_PATTERN
from app.service_requests.id_generation import SERVICE_REQUEST_ID_PATTERN
from app.tickets.constants import Priority, RiskLevel, TicketIntent
from app.tickets.id_generation import TICKET_ID_PATTERN

CUSTOMER_ID_PATTERN = r"^CUST-\d{3}$"
USER_ID_PATTERN = r"^USR-[A-Z]+-\d{3,4}$"


class AuditLogDocument(BaseModel):
    """MongoDB audit_logs collection document."""

    model_config = ConfigDict(str_strip_whitespace=True)

    audit_id: str = Field(..., pattern=AUDIT_ID_PATTERN)
    event_type: AuditEventType
    created_at: datetime

    ticket_id: str | None = Field(default=None, pattern=TICKET_ID_PATTERN)
    message_id: str | None = Field(default=None, pattern=MESSAGE_ID_PATTERN)
    customer_id: str | None = Field(default=None, pattern=CUSTOMER_ID_PATTERN)
    intent: TicketIntent | None = None
    risk_level: RiskLevel | None = None
    priority: Priority | None = None
    tool_called: str | None = None
    tool_input_masked: dict[str, Any] | str | None = None
    tool_output_summary: dict[str, Any] | str | None = None
    retrieved_policy_ids: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    action_taken: str | None = None
    customer_safe_summary: str | None = None
    raw_internal_trace: dict[str, Any] | None = None
    langsmith_trace_id: str | None = None

    user_id: str | None = Field(default=None, pattern=USER_ID_PATTERN)
    session_id: str | None = None
    service_request_id: str | None = Field(default=None, pattern=SERVICE_REQUEST_ID_PATTERN)
    workflow_id: str | None = None
    created_by: AuditCreatedBy | None = None
    decision: dict[str, Any] | str | None = None
    escalation_required: bool | None = None
    internal_summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("session_id must be null or non-empty")
        return value

    @field_validator("tool_called")
    @classmethod
    def validate_tool_called(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("tool_called must be null or non-empty")
        return value

    @model_validator(mode="after")
    def validate_cross_field_rules(self) -> AuditLogDocument:
        if not validate_audit_id(self.audit_id):
            raise ValueError("invalid audit_id format")
        return self

    def to_mongo_dict(self) -> dict[str, object]:
        """Serialize for MongoDB insert."""
        return self.model_dump(mode="json")
