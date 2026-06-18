"""Typed contracts for workflow ticket persistence."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.state import AgentState, CustomerResponseMetadata, ResolutionPlan
from app.tickets.constants import TicketClass, TicketStatus


@dataclass(frozen=True)
class WorkflowTicketUpdateCommand:
    """Validated inputs for workflow ticket persistence."""

    state: AgentState
    resolution_plan: ResolutionPlan
    customer_response: str
    customer_response_metadata: CustomerResponseMetadata


@dataclass(frozen=True)
class WorkflowTicketUpdateResult:
    """Outcome of workflow ticket persistence."""

    ticket_status: TicketStatus
    service_request_id: str | None
    update_summary: str
    document_path: str | None
    ai_message_id: str
    previous_ticket_class: TicketClass
    persisted_ticket_class: TicketClass
    previous_status: TicketStatus
    human_review_queued: bool
    idempotent_replay: bool
    class_preserved: bool = False
