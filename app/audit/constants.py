"""Audit log domain constants aligned with DATA_MODEL §10.1."""

from typing import Literal

AUDIT_LOGS_COLLECTION = "audit_logs"

AuditEventType = Literal[
    "intent_classified",
    "risk_classified",
    "ticket_routed",
    "retrieval_performed",
    "tool_planned",
    "guardrail_decided",
    "tool_called",
    "response_generated",
    "ticket_updated",
    "service_request_created",
    "error_recorded",
    "workflow_completed",
]

AuditCreatedBy = Literal["system", "customer", "support_agent", "admin", "ai"]

ALL_AUDIT_EVENT_TYPES: tuple[AuditEventType, ...] = (
    "intent_classified",
    "risk_classified",
    "ticket_routed",
    "retrieval_performed",
    "tool_planned",
    "guardrail_decided",
    "tool_called",
    "response_generated",
    "ticket_updated",
    "service_request_created",
    "error_recorded",
    "workflow_completed",
)
