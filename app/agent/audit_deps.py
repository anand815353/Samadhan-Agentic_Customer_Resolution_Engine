"""Dependency bundle for the agent audit node (T-063)."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.workflow_audit.workflow_audit_service import WorkflowAuditService
from app.audit.repositories import InMemoryAuditLogRepository
from app.audit.services import AuditService
from app.core.config import Settings, get_settings
from app.messages.services import MessageService
from app.tickets.services import TicketService

_audit_deps_override: AuditDeps | None = None


@dataclass(frozen=True)
class AuditDeps:
    """Injected services for audit node execution."""

    audit_service: AuditService
    ticket_service: TicketService
    message_service: MessageService
    settings: Settings

    @property
    def workflow_audit_service(self) -> WorkflowAuditService:
        return WorkflowAuditService(
            audit_service=self.audit_service,
            ticket_service=self.ticket_service,
            message_service=self.message_service,
        )


def set_audit_deps_override(deps: AuditDeps | None) -> None:
    """Override default audit dependencies (primarily for tests)."""
    global _audit_deps_override
    _audit_deps_override = deps


def build_in_memory_audit_deps(
    *,
    audit_repository: InMemoryAuditLogRepository | None = None,
    ticket_service: TicketService | None = None,
    message_service: MessageService | None = None,
) -> AuditDeps:
    """Build audit dependencies backed by in-memory repositories."""
    from app.agent.ticket_update_deps import build_in_memory_ticket_update_deps

    ticket_update = build_in_memory_ticket_update_deps()
    resolved_ticket = ticket_service or ticket_update.ticket_service
    resolved_message = message_service or ticket_update.message_service
    repository = audit_repository or InMemoryAuditLogRepository()
    audit_service = AuditService(
        repository,
        ticket_service=resolved_ticket,
        message_service=resolved_message,
    )
    return AuditDeps(
        audit_service=audit_service,
        ticket_service=resolved_ticket,
        message_service=resolved_message,
        settings=get_settings(),
    )


def build_audit_deps(*, settings: Settings | None = None) -> AuditDeps:
    """Build audit dependencies sharing ticket-update persistence."""
    from app.agent.ticket_update_deps import get_default_ticket_update_deps

    resolved = settings or get_settings()
    ticket_update = get_default_ticket_update_deps(resolved)
    repository = InMemoryAuditLogRepository()
    audit_service = AuditService(
        repository,
        ticket_service=ticket_update.ticket_service,
        message_service=ticket_update.message_service,
    )
    return AuditDeps(
        audit_service=audit_service,
        ticket_service=ticket_update.ticket_service,
        message_service=ticket_update.message_service,
        settings=resolved,
    )


def get_default_audit_deps(settings: Settings | None = None) -> AuditDeps:
    """Return audit dependencies for workflow execution."""
    if _audit_deps_override is not None:
        return _audit_deps_override
    return build_audit_deps(settings=settings)
