"""Ticket domain module — model, lifecycle, repository, and service (T-021)."""

from __future__ import annotations

from app.tickets.constants import (
    ALL_TICKET_INTENTS,
    ALL_TICKET_STATUSES,
    HUMAN_REVIEW_QUEUE_STATUSES,
    TERMINAL_STATUSES,
    TICKETS_COLLECTION,
)
from app.tickets.exceptions import InvalidTicketTransitionError, TicketAccessDeniedError
from app.tickets.lifecycle import apply_transition, can_transition, default_status_for_class
from app.tickets.models import TicketDocument
from app.tickets.repositories import InMemoryTicketRepository, MongoTicketRepository, TicketRepository
from app.tickets.schemas import TicketCreate, TicketRead, ticket_document_from_create
from app.tickets.services import TicketService

_DETAIL_LAZY_EXPORTS = frozenset(
    {
        "CustomerTicketDetailRead",
        "CustomerTicketRead",
        "TicketDetailCounts",
        "TicketDetailRead",
        "TicketDetailService",
        "ensure_ticket_belongs_to_customer",
    }
)


def __getattr__(name: str) -> object:
    if name == "CustomerTicketDetailRead":
        from app.tickets.detail_schemas import CustomerTicketDetailRead

        return CustomerTicketDetailRead
    if name == "CustomerTicketRead":
        from app.tickets.detail_schemas import CustomerTicketRead

        return CustomerTicketRead
    if name == "TicketDetailCounts":
        from app.tickets.detail_schemas import TicketDetailCounts

        return TicketDetailCounts
    if name == "TicketDetailRead":
        from app.tickets.detail_schemas import TicketDetailRead

        return TicketDetailRead
    if name == "TicketDetailService":
        from app.tickets.detail_service import TicketDetailService

        return TicketDetailService
    if name == "ensure_ticket_belongs_to_customer":
        from app.tickets.detail_service import ensure_ticket_belongs_to_customer

        return ensure_ticket_belongs_to_customer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ALL_TICKET_INTENTS",
    "ALL_TICKET_STATUSES",
    "CustomerTicketDetailRead",
    "CustomerTicketRead",
    "HUMAN_REVIEW_QUEUE_STATUSES",
    "InvalidTicketTransitionError",
    "InMemoryTicketRepository",
    "MongoTicketRepository",
    "TERMINAL_STATUSES",
    "TICKETS_COLLECTION",
    "TicketAccessDeniedError",
    "TicketCreate",
    "TicketDetailCounts",
    "TicketDetailRead",
    "TicketDetailService",
    "TicketDocument",
    "TicketRead",
    "TicketRepository",
    "TicketService",
    "apply_transition",
    "can_transition",
    "default_status_for_class",
    "ensure_ticket_belongs_to_customer",
    "ticket_document_from_create",
]
