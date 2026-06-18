"""Idempotent AI message persistence for workflow replays."""

from __future__ import annotations

from app.agent.exceptions import TicketUpdateValidationError
from app.agent.state import AgentState
from app.messages.models import MessageDocument
from app.messages.repositories import MessageRepository
from app.messages.schemas import MessageCreate
from app.messages.services import MessageService


async def find_workflow_ai_message(
    repository: MessageRepository,
    *,
    ticket_id: str,
    workflow_id: str,
) -> MessageDocument | None:
    """Return an existing AI message for this workflow replay, if any."""
    messages = await repository.find_by_ticket(ticket_id)
    for message in reversed(messages):
        if message.sender_type != "ai":
            continue
        metadata = message.message_metadata or {}
        if metadata.get("workflow_id") == workflow_id:
            return message
    return None


async def persist_ai_message(
    message_service: MessageService,
    message_repository: MessageRepository,
    state: AgentState,
    *,
    customer_response: str,
) -> tuple[MessageDocument, bool]:
    """Persist AI response once per workflow_id; return (message, idempotent_replay)."""
    if not state.ticket_id:
        raise TicketUpdateValidationError("ticket_id is required to persist AI message")
    if not state.workflow_id:
        raise TicketUpdateValidationError("workflow_id is required to persist AI message")
    if not state.customer_id:
        raise TicketUpdateValidationError("customer_id is required to persist AI message")
    if not state.session_id:
        raise TicketUpdateValidationError("session_id is required to persist AI message")
    if not customer_response.strip():
        raise TicketUpdateValidationError("customer_response is required to persist AI message")

    existing = await find_workflow_ai_message(
        message_repository,
        ticket_id=state.ticket_id,
        workflow_id=state.workflow_id,
    )
    if existing is not None:
        return existing, True

    plan = state.resolution_plan
    message = await message_service.create_message(
        MessageCreate(
            ticket_id=state.ticket_id,
            customer_id=state.customer_id,
            session_id=state.session_id,
            sender_type="ai",
            sender_id=None,
            message_text=customer_response,
            message_metadata={
                "workflow_id": state.workflow_id,
                "intent": plan.intent if plan else None,
                "risk_level": plan.risk_level if plan else None,
                "ticket_class": plan.ticket_class if plan else None,
                "ticket_status": plan.ticket_status if plan else None,
                "priority": plan.priority if plan else None,
                "generation_source": (
                    state.customer_response_metadata.generation_source
                    if state.customer_response_metadata
                    else None
                ),
                "prompt_version": (
                    state.customer_response_metadata.prompt_version
                    if state.customer_response_metadata
                    else None
                ),
                "safety_status": (
                    state.customer_response_metadata.safety_status
                    if state.customer_response_metadata
                    else None
                ),
                "service_request_id": plan.service_request_id if plan else None,
                "mock_disclaimer_included": (
                    state.customer_response_metadata.mock_disclaimer_included
                    if state.customer_response_metadata
                    else False
                ),
            },
        ),
        actor="ai",
    )
    return message, False
