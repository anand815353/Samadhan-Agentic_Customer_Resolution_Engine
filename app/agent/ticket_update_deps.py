"""Dependency bundle for the agent ticket update node (T-062)."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.persistence.workflow_ticket_update_service import WorkflowTicketUpdateService
from app.core.config import Settings, get_settings
from app.messages.repositories import InMemoryMessageRepository, MessageRepository
from app.messages.services import MessageService
from app.service_requests.repositories import InMemoryServiceRequestRepository
from app.service_requests.services import ServiceRequestService
from app.tickets.repositories import InMemoryTicketRepository
from app.tickets.services import TicketService

_ticket_update_deps_override: TicketUpdateDeps | None = None


@dataclass(frozen=True)
class TicketUpdateDeps:
    """Injected services for ticket update node execution."""

    ticket_service: TicketService
    message_service: MessageService
    message_repository: MessageRepository
    service_request_service: ServiceRequestService
    settings: Settings

    @property
    def workflow_ticket_update_service(self) -> WorkflowTicketUpdateService:
        return WorkflowTicketUpdateService(
            ticket_service=self.ticket_service,
            message_service=self.message_service,
            message_repository=self.message_repository,
            service_request_service=self.service_request_service,
        )


def set_ticket_update_deps_override(deps: TicketUpdateDeps | None) -> None:
    """Override default ticket update dependencies (primarily for tests)."""
    global _ticket_update_deps_override
    _ticket_update_deps_override = deps


def build_in_memory_ticket_update_deps(
    *,
    tickets: InMemoryTicketRepository | None = None,
    messages: InMemoryMessageRepository | None = None,
    service_requests: InMemoryServiceRequestRepository | None = None,
) -> TicketUpdateDeps:
    """Build ticket update dependencies backed by in-memory repositories."""
    ticket_repository = tickets or InMemoryTicketRepository()
    ticket_service = TicketService(ticket_repository)
    message_repository = messages or InMemoryMessageRepository()
    message_service = MessageService(message_repository, ticket_service)
    sr_repository = service_requests or InMemoryServiceRequestRepository()
    sr_service = ServiceRequestService(sr_repository, ticket_service)
    return TicketUpdateDeps(
        ticket_service=ticket_service,
        message_service=message_service,
        message_repository=message_repository,
        service_request_service=sr_service,
        settings=get_settings(),
    )


def build_ticket_update_deps(*, settings: Settings | None = None) -> TicketUpdateDeps:
    """Build ticket update dependencies sharing intake persistence."""
    from app.agent.intake_deps import get_default_intake_deps

    resolved = settings or get_settings()
    intake = get_default_intake_deps(resolved)
    sr_service = ServiceRequestService(
        InMemoryServiceRequestRepository(),
        intake.ticket_service,
    )
    return TicketUpdateDeps(
        ticket_service=intake.ticket_service,
        message_service=intake.message_service,
        message_repository=intake.message_repository,
        service_request_service=sr_service,
        settings=resolved,
    )


def get_default_ticket_update_deps(settings: Settings | None = None) -> TicketUpdateDeps:
    """Return ticket update dependencies for workflow execution."""
    if _ticket_update_deps_override is not None:
        return _ticket_update_deps_override
    return build_ticket_update_deps(settings=settings)
