"""LangGraph intake node implementation (T-052)."""

from __future__ import annotations

from typing import Any

from app.agent.exceptions import (
    IntakeAccessDeniedError,
    IntakePersistenceError,
    IntakeValidationError,
)
from app.agent.intake_context import build_customer_context_snapshot
from app.agent.intake_deps import IntakeDeps
from app.agent.nodes.base import NodeCallable
from app.agent.state import AgentState
from app.common.text_normalization import BlankMessageError, normalize_customer_message
from app.core.exceptions import NotFoundError
from app.messages.constants import META_NORMALIZED_TEXT
from app.messages.exceptions import MessageAccessDeniedError, MessageValidationError
from app.messages.schemas import MessageCreate
from app.tickets.constants import TERMINAL_STATUSES, TICKET_CLASS_TIER_2
from app.tickets.detail_service import ensure_ticket_belongs_to_customer
from app.tickets.exceptions import TicketAccessDeniedError
from app.tickets.models import TicketDocument
from app.tickets.schemas import TicketCreate
from app.users.constants import ROLE_CUSTOMER


def _ticket_subject(message: str, *, max_len: int = 80) -> str:
    text = message.strip()
    if len(text) <= max_len:
        return text
    return f"{text[: max_len - 3]}..."


def _resolve_session_id(state: AgentState) -> str:
    if state.session_id:
        return state.session_id
    return f"SES-{state.workflow_id[3:]}"


class IntakeNode:
    """Prepare customer workflow state and persist the incoming customer message."""

    def __init__(self, deps: IntakeDeps) -> None:
        self._deps = deps

    async def __call__(self, state: AgentState) -> dict[str, Any]:
        user = await self._deps.user_repository.find_by_user_id(state.user_id)
        if user is None:
            raise IntakeValidationError("authenticated user was not found")
        if not user.is_active:
            raise IntakeValidationError("authenticated user is inactive")
        if user.role != ROLE_CUSTOMER:
            raise IntakeAccessDeniedError("workflow intake requires a customer user")
        if not user.customer_id:
            raise IntakeValidationError("customer user is missing linked customer_id")

        customer_id = user.customer_id
        if state.customer_id is not None and state.customer_id != customer_id:
            raise IntakeAccessDeniedError("customer_id does not match authenticated user")

        customer = await self._deps.customer_repository.find_by_id(customer_id)
        if customer is None:
            raise IntakeValidationError("linked customer record was not found")

        try:
            normalized_message = normalize_customer_message(state.customer_message)
        except BlankMessageError as exc:
            raise IntakeValidationError("customer message is blank after normalization") from exc

        session_id = _resolve_session_id(state)
        ticket = await self._resolve_ticket(
            state=state,
            customer_id=customer_id,
            user_id=state.user_id,
            session_id=session_id,
        )

        message = await self._persist_customer_message(
            state=state,
            customer_id=customer_id,
            session_id=session_id,
            ticket=ticket,
            normalized_message=normalized_message,
        )

        loans = await self._deps.loan_repository.find_by_customer(customer_id)
        customer_context = build_customer_context_snapshot(customer, loans)

        return {
            "customer_id": customer_id,
            "session_id": session_id,
            "ticket_id": ticket.ticket_id,
            "message_id": message.message_id,
            "normalized_message": normalized_message,
            "customer_context": customer_context,
            "persisted_ticket_class": ticket.ticket_class,
        }

    async def _resolve_ticket(
        self,
        *,
        state: AgentState,
        customer_id: str,
        user_id: str,
        session_id: str,
    ) -> TicketDocument:
        if state.ticket_id is not None:
            try:
                ticket = await self._deps.ticket_service.get_ticket(state.ticket_id)
            except NotFoundError as exc:
                raise IntakeValidationError("ticket was not found") from exc
            try:
                ensure_ticket_belongs_to_customer(ticket, customer_id)
            except TicketAccessDeniedError as exc:
                raise IntakeAccessDeniedError("ticket does not belong to authenticated customer") from exc
            if ticket.user_id != user_id:
                raise IntakeAccessDeniedError("ticket does not belong to authenticated user")
            if ticket.session_id != session_id:
                raise IntakeValidationError("ticket session_id does not match workflow session")
            return ticket

        tickets = await self._deps.ticket_service.list_customer_tickets(customer_id)
        open_for_session = [
            ticket
            for ticket in tickets
            if ticket.session_id == session_id and ticket.status not in TERMINAL_STATUSES
        ]
        if open_for_session:
            open_for_session.sort(key=lambda item: item.updated_at, reverse=True)
            return open_for_session[0]

        try:
            return await self._deps.ticket_service.create_ticket(
                TicketCreate(
                    customer_id=customer_id,
                    user_id=user_id,
                    session_id=session_id,
                    intent="unknown",
                    ticket_class=TICKET_CLASS_TIER_2,
                    subject=_ticket_subject(state.customer_message),
                    description=state.customer_message,
                ),
                actor="system",
            )
        except Exception as exc:
            raise IntakePersistenceError("failed to create conversation ticket") from exc

    async def _persist_customer_message(
        self,
        *,
        state: AgentState,
        customer_id: str,
        session_id: str,
        ticket: TicketDocument,
        normalized_message: str,
    ):
        if state.message_id is not None:
            existing = await self._deps.message_repository.find_by_id(state.message_id)
            if existing is not None:
                if existing.customer_id != customer_id:
                    raise IntakeAccessDeniedError("message does not belong to authenticated customer")
                if existing.ticket_id != ticket.ticket_id:
                    raise IntakeValidationError("message ticket_id does not match workflow ticket")
                if existing.session_id != session_id:
                    raise IntakeValidationError("message session_id does not match workflow session")
                if existing.sender_id != state.user_id:
                    raise IntakeValidationError("message sender_id does not match authenticated user")
                return existing

        payload = MessageCreate(
            ticket_id=ticket.ticket_id,
            session_id=session_id,
            customer_id=customer_id,
            sender_type="customer",
            sender_id=state.user_id,
            message_text=state.customer_message,
            message_metadata={
                META_NORMALIZED_TEXT: normalized_message,
                "workflow_id": state.workflow_id,
            },
            message_id=state.message_id,
        )
        try:
            return await self._deps.message_service.create_message(
                payload,
                actor="customer",
                actor_customer_id=customer_id,
            )
        except (MessageAccessDeniedError, MessageValidationError) as exc:
            raise IntakeValidationError("message persistence validation failed") from exc
        except Exception as exc:
            raise IntakePersistenceError("failed to persist customer message") from exc


def build_intake_node(deps: IntakeDeps) -> NodeCallable:
    """Build the intake node callable for graph registration."""
    node = IntakeNode(deps)
    return node.__call__


__all__ = ["IntakeNode", "build_intake_node"]
