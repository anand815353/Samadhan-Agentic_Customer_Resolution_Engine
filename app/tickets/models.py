"""Ticket persistence models aligned with the MongoDB tickets collection."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.tickets.constants import (
    TIER_1_SR_REQUIRED_STATUSES,
    TERMINAL_STATUSES,
    TICKET_CLASS_HUMAN_REVIEW,
    CreatedBy,
    Priority,
    RiskLevel,
    SourceChannel,
    TicketClass,
    TicketIntent,
    TicketStatus,
)
from app.service_requests.id_generation import validate_service_request_id
from app.tickets.id_generation import (
    TICKET_ID_PATTERN,
    validate_ticket_id,
)
from app.tickets.risk_rules import validate_risk_priority_rules

USER_ID_PATTERN = r"^USR-[A-Z]+-\d{3,4}$"
CUSTOMER_ID_PATTERN = r"^CUST-\d{3}$"


class TicketDocument(BaseModel):
    """MongoDB tickets collection document."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ticket_id: str = Field(..., pattern=TICKET_ID_PATTERN)
    customer_id: str = Field(..., pattern=CUSTOMER_ID_PATTERN)
    user_id: str = Field(..., pattern=USER_ID_PATTERN)
    session_id: str = Field(..., min_length=1)
    ticket_class: TicketClass
    intent: TicketIntent
    risk_level: RiskLevel
    priority: Priority
    status: TicketStatus
    subject: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    source_channel: SourceChannel = "web_chat"
    service_request_id: str | None = None
    assigned_agent_id: str | None = Field(default=None, pattern=USER_ID_PATTERN)
    escalation_reason: str | None = None
    closure_reason: str | None = None
    last_customer_message: str = ""
    last_ai_response: str = ""
    created_by: CreatedBy = "system"
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None

    @field_validator("service_request_id")
    @classmethod
    def validate_sr_id_format(cls, value: str | None) -> str | None:
        if value is not None and not validate_service_request_id(value):
            raise ValueError("service_request_id must match SR-YYYY-NNNN format")
        return value

    @model_validator(mode="after")
    def validate_cross_field_rules(self) -> "TicketDocument":
        if not validate_ticket_id(self.ticket_id):
            raise ValueError("invalid ticket_id format")

        validate_risk_priority_rules(
            intent=self.intent,
            ticket_class=self.ticket_class,
            risk_level=self.risk_level,
            priority=self.priority,
        )

        if self.status == "escalated_to_human" and not self.escalation_reason:
            raise ValueError("escalation_reason required when status is escalated_to_human")

        if (
            self.ticket_class == "tier_1_service_request"
            and self.status in TIER_1_SR_REQUIRED_STATUSES
            and not self.service_request_id
        ):
            raise ValueError(
                "service_request_id required for tier_1 tickets in service workflow statuses"
            )

        if self.status in TERMINAL_STATUSES and self.closed_at is None:
            raise ValueError(f"closed_at required for terminal status '{self.status}'")

        if self.status not in TERMINAL_STATUSES and self.closed_at is not None:
            raise ValueError("closed_at must be null for non-terminal statuses")

        if self.ticket_class == TICKET_CLASS_HUMAN_REVIEW and self.status in (
            "auto_resolved",
            "auto_closed",
        ):
            raise ValueError("human_review tickets cannot have auto-close statuses")

        return self

    def to_mongo_dict(self) -> dict[str, object]:
        """Serialize for MongoDB insert/update."""
        return self.model_dump(mode="json")
