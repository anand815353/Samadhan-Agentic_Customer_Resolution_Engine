"""Ticket detail aggregate read service (T-026)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.audit.models import AuditLogDocument
from app.audit.services import AuditService
from app.common.service import BaseService
from app.messages.models import MessageDocument
from app.messages.services import MessageService
from app.service_requests.models import ServiceRequestDocument
from app.service_requests.services import ServiceRequestService
from app.tickets.detail_schemas import CustomerTicketDetailRead, TicketDetailRead
from app.tickets.exceptions import TicketAccessDeniedError
from app.tickets.models import TicketDocument
from app.tickets.services import TicketService


def ensure_ticket_belongs_to_customer(ticket: TicketDocument, customer_id: str) -> None:
    """Raise TicketAccessDeniedError when ticket is not owned by the customer."""
    if ticket.customer_id != customer_id:
        raise TicketAccessDeniedError(
            f"ticket {ticket.ticket_id} does not belong to customer {customer_id}"
        )


def _sort_by_created_at_asc(items: list[MessageDocument] | list[AuditLogDocument]) -> list:
    return sorted(items, key=lambda item: item.created_at)


class TicketDetailService(BaseService):
    """Read-only aggregate service for ticket-centric detail views."""

    def __init__(
        self,
        ticket_service: TicketService,
        message_service: MessageService,
        service_request_service: ServiceRequestService,
        audit_service: AuditService,
    ) -> None:
        self._ticket_service = ticket_service
        self._message_service = message_service
        self._service_request_service = service_request_service
        self._audit_service = audit_service

    async def get_ticket_detail(
        self,
        ticket_id: str,
        *,
        include_internal_audit: bool = False,
    ) -> TicketDetailRead:
        """Return full ticket detail for internal/system use."""
        return await self._build_ticket_detail(
            ticket_id,
            message_actor="system",
            include_audits=True,
            include_internal_audit=include_internal_audit,
        )

    async def get_agent_ticket_detail(
        self,
        ticket_id: str,
        *,
        include_internal_audit: bool = False,
    ) -> TicketDetailRead:
        """Return ticket detail for support-agent views."""
        return await self._build_ticket_detail(
            ticket_id,
            message_actor="support_agent",
            include_audits=True,
            include_internal_audit=include_internal_audit,
        )

    async def get_customer_ticket_detail(
        self,
        ticket_id: str,
        customer_id: str,
    ) -> CustomerTicketDetailRead:
        """Return customer-safe ticket detail scoped to the owning customer."""
        ticket = await self._ticket_service.get_ticket(ticket_id)
        ensure_ticket_belongs_to_customer(ticket, customer_id)

        messages = await self._message_service.list_ticket_messages(
            ticket_id,
            actor="customer",
            actor_customer_id=customer_id,
        )
        service_request = await self._service_request_service.get_for_ticket(ticket_id)

        return CustomerTicketDetailRead.from_parts(
            ticket=ticket,
            messages=_sort_by_created_at_asc(messages),
            service_request=service_request,
            retrieved_at=datetime.now(UTC),
        )

    async def _build_ticket_detail(
        self,
        ticket_id: str,
        *,
        message_actor: str,
        include_audits: bool,
        include_internal_audit: bool,
    ) -> TicketDetailRead:
        ticket = await self._ticket_service.get_ticket(ticket_id)

        messages = await self._message_service.list_ticket_messages(
            ticket_id,
            actor=message_actor,  # type: ignore[arg-type]
        )
        service_request = await self._service_request_service.get_for_ticket(ticket_id)

        audit_events: list[AuditLogDocument] = []
        if include_audits:
            audit_events = await self._audit_service.list_for_ticket(ticket_id)

        return TicketDetailRead.from_parts(
            ticket=ticket,
            messages=_sort_by_created_at_asc(messages),
            service_request=service_request,
            audit_events=_sort_by_created_at_asc(audit_events),
            retrieved_at=datetime.now(UTC),
            include_internal_audit=include_internal_audit,
        )
