"""Message business logic: creation, retrieval, and ticket linkage."""

from __future__ import annotations

from app.common.service import BaseService
from app.core.exceptions import NotFoundError
from app.messages.constants import MessageActor
from app.messages.exceptions import MessageAccessDeniedError, MessageValidationError
from app.messages.id_generation import allocate_message_id
from app.messages.models import MessageDocument
from app.messages.repositories import MessageRepository
from app.messages.schemas import MessageCreate, message_document_from_create
from app.tickets.constants import TERMINAL_STATUSES
from app.tickets.models import TicketDocument
from app.tickets.services import TicketService


class MessageService(BaseService):
    """Domain service for chat message persistence."""

    def __init__(
        self,
        repository: MessageRepository,
        ticket_service: TicketService,
    ) -> None:
        self._repository = repository
        self._ticket_service = ticket_service

    async def create_message(
        self,
        data: MessageCreate,
        *,
        actor: MessageActor,
        actor_customer_id: str | None = None,
    ) -> MessageDocument:
        ticket = await self._ticket_service.get_ticket(data.ticket_id)
        self._authorize_create(data, ticket=ticket, actor=actor, actor_customer_id=actor_customer_id)
        self._validate_ticket_linkage(data, ticket)

        message_id = data.message_id
        if message_id is None:
            message_id = await allocate_message_id(self._repository)

        document = message_document_from_create(data, message_id=message_id)
        saved = await self._repository.insert(document)

        if data.sender_type == "customer":
            await self._ticket_service.touch_message_snapshots(
                data.ticket_id,
                last_customer_message=data.message_text,
            )
        elif data.sender_type == "ai":
            await self._ticket_service.touch_message_snapshots(
                data.ticket_id,
                last_ai_response=data.message_text,
            )

        return saved

    async def get_message(
        self,
        message_id: str,
        *,
        actor: MessageActor,
        actor_customer_id: str | None = None,
    ) -> MessageDocument:
        document = await self._repository.find_by_id(message_id)
        if document is None:
            raise NotFoundError(f"message not found: {message_id}")
        self._authorize_read(document, actor=actor, actor_customer_id=actor_customer_id)
        return document

    async def list_ticket_messages(
        self,
        ticket_id: str,
        *,
        actor: MessageActor,
        actor_customer_id: str | None = None,
    ) -> list[MessageDocument]:
        ticket = await self._ticket_service.get_ticket(ticket_id)
        self._authorize_ticket_read(ticket, actor=actor, actor_customer_id=actor_customer_id)
        return await self._repository.find_by_ticket(ticket_id)

    async def list_session_messages(
        self,
        session_id: str,
        *,
        actor: MessageActor,
        actor_customer_id: str | None = None,
    ) -> list[MessageDocument]:
        messages = await self._repository.find_by_session(session_id)
        if not messages:
            return []
        ticket = await self._ticket_service.get_ticket(messages[0].ticket_id)
        self._authorize_ticket_read(ticket, actor=actor, actor_customer_id=actor_customer_id)
        return messages

    async def list_customer_messages(
        self,
        customer_id: str,
        *,
        actor: MessageActor,
        actor_customer_id: str | None = None,
    ) -> list[MessageDocument]:
        if actor == "customer":
            if actor_customer_id != customer_id:
                raise MessageAccessDeniedError("customers may only list their own messages")
        return await self._repository.find_by_customer(customer_id)

    async def find_workflow_ai_message(
        self,
        ticket_id: str,
        workflow_id: str,
    ) -> MessageDocument | None:
        """Return an existing AI message for this workflow replay, if any."""
        from app.agent.persistence.ai_message_idempotency import find_workflow_ai_message

        return await find_workflow_ai_message(
            self._repository,
            ticket_id=ticket_id,
            workflow_id=workflow_id,
        )

    def _validate_ticket_linkage(self, data: MessageCreate, ticket: TicketDocument) -> None:
        if data.customer_id != ticket.customer_id:
            raise MessageValidationError("message customer_id must match ticket customer_id")
        if data.session_id != ticket.session_id:
            raise MessageValidationError("message session_id must match ticket session_id")
        if data.sender_type == "customer" and data.sender_id != ticket.user_id:
            raise MessageValidationError("customer sender_id must match ticket user_id")

    def _authorize_create(
        self,
        data: MessageCreate,
        *,
        ticket: TicketDocument,
        actor: MessageActor,
        actor_customer_id: str | None,
    ) -> None:
        if actor == "customer":
            if actor_customer_id != ticket.customer_id:
                raise MessageAccessDeniedError("customers may only message their own tickets")
            if data.sender_type != "customer":
                raise MessageAccessDeniedError("customers may only send customer messages")
            if ticket.status in TERMINAL_STATUSES:
                raise MessageAccessDeniedError("cannot append messages to closed tickets")
        elif actor == "support_agent":
            if data.sender_type != "support_agent":
                raise MessageAccessDeniedError("support agents must use support_agent sender_type")
        elif actor == "ai":
            if data.sender_type != "ai":
                raise MessageAccessDeniedError("ai actor must use ai sender_type")
        elif actor == "system":
            if data.sender_type != "system":
                raise MessageAccessDeniedError("system actor must use system sender_type")

    def _authorize_read(
        self,
        document: MessageDocument,
        *,
        actor: MessageActor,
        actor_customer_id: str | None,
    ) -> None:
        if actor == "customer" and actor_customer_id != document.customer_id:
            raise MessageAccessDeniedError("customers may only read their own messages")

    def _authorize_ticket_read(
        self,
        ticket: TicketDocument,
        *,
        actor: MessageActor,
        actor_customer_id: str | None,
    ) -> None:
        if actor == "customer" and actor_customer_id != ticket.customer_id:
            raise MessageAccessDeniedError("customers may only read their own ticket messages")
