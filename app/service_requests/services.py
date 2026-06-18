"""Service request business logic: creation, lifecycle, and ticket orchestration."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import ValidationError

from app.common.service import BaseService
from app.core.exceptions import ConflictError, NotFoundError
from app.service_requests.constants import (
    ServiceRequestActor,
    ServiceRequestCreatedBy,
    ServiceRequestStatus,
)
from app.service_requests.exceptions import (
    InvalidServiceRequestTransitionError,
    ServiceRequestValidationError,
)
from app.service_requests.id_generation import allocate_service_request_id
from app.service_requests.lifecycle import (
    SR_TO_TICKET_STATUS,
    validate_transition,
)
from app.service_requests.models import ServiceRequestDocument
from app.service_requests.repositories import ServiceRequestRepository
from app.service_requests.schemas import ServiceRequestCreate, service_document_from_create
from app.tickets.constants import TICKET_CLASS_TIER_1
from app.tickets.exceptions import InvalidTicketTransitionError
from app.tickets.models import TicketDocument
from app.tickets.services import TicketService


class ServiceRequestService(BaseService):
    """Domain service for service request persistence and ticket linkage."""

    def __init__(
        self,
        repository: ServiceRequestRepository,
        ticket_service: TicketService,
    ) -> None:
        self._repository = repository
        self._ticket_service = ticket_service

    async def create_for_ticket(
        self,
        ticket_id: str,
        request_type: str,
        *,
        customer_safe_summary: str,
        loan_id: str | None = None,
        created_by: ServiceRequestCreatedBy = "system",
        actor: ServiceRequestActor = "system",
        sync_ticket: bool = True,
        service_request_id: str | None = None,
    ) -> ServiceRequestDocument:
        ticket = await self._ticket_service.get_ticket(ticket_id)
        self._validate_ticket_for_create(ticket)

        existing = await self._repository.find_by_ticket(ticket_id)
        if existing is not None:
            raise ConflictError(f"service request already exists for ticket: {ticket_id}")

        create_data = ServiceRequestCreate(
            ticket_id=ticket_id,
            customer_id=ticket.customer_id,
            request_type=request_type,  # type: ignore[arg-type]
            customer_safe_summary=customer_safe_summary,
            loan_id=loan_id,
            created_by=created_by,
            service_request_id=service_request_id,
        )

        sr_id = service_request_id
        if sr_id is None:
            sr_id = await allocate_service_request_id(self._repository)
        else:
            if await self._repository.find_by_id(sr_id) is not None:
                raise ConflictError(f"service request already exists: {sr_id}")

        document = service_document_from_create(create_data, service_request_id=sr_id)
        saved = await self._repository.insert(document)

        if sync_ticket:
            try:
                await self._ticket_service.transition(
                    ticket_id,
                    "service_requested",
                    actor="system",
                    service_request_id=sr_id,
                )
            except (InvalidTicketTransitionError, ValidationError):
                await self._repository.delete(sr_id)
                raise

        return saved

    async def get_service_request(self, service_request_id: str) -> ServiceRequestDocument:
        document = await self._repository.find_by_id(service_request_id)
        if document is None:
            raise NotFoundError(f"service request not found: {service_request_id}")
        return document

    async def get_for_ticket(self, ticket_id: str) -> ServiceRequestDocument | None:
        return await self._repository.find_by_ticket(ticket_id)

    async def list_customer_service_requests(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[ServiceRequestDocument]:
        return await self._repository.find_by_customer(customer_id, limit=limit)

    async def transition(
        self,
        service_request_id: str,
        to_status: ServiceRequestStatus,
        *,
        actor: ServiceRequestActor,
        sync_ticket: bool = False,
    ) -> ServiceRequestDocument:
        document = await self.get_service_request(service_request_id)
        from_status = document.status

        try:
            validate_transition(from_status=from_status, to_status=to_status, actor=actor)
        except InvalidServiceRequestTransitionError as exc:
            exc.service_request_id = service_request_id
            raise

        now = datetime.now(UTC)
        document.status = to_status
        document.updated_at = now
        if to_status == "completed":
            document.completed_at = now

        try:
            validated = ServiceRequestDocument.model_validate(document.model_dump())
        except ValidationError as exc:
            raise InvalidServiceRequestTransitionError(
                f"transition produced invalid service request state: {exc}",
                service_request_id=service_request_id,
                from_status=from_status,
                to_status=to_status,
            ) from exc

        updated = await self._repository.update(validated)

        if sync_ticket:
            ticket_status = SR_TO_TICKET_STATUS.get(to_status)
            if ticket_status:
                await self._ticket_service.transition(
                    updated.ticket_id,
                    ticket_status,
                    actor="system",
                )

        return updated

    async def record_mock_document_path(
        self,
        service_request_id: str,
        document_path: str,
        *,
        mark_completed: bool = True,
        actor: ServiceRequestActor = "system",
    ) -> ServiceRequestDocument:
        document = await self.get_service_request(service_request_id)
        if document.document_path == document_path:
            return document

        now = datetime.now(UTC)
        document.document_path = document_path
        document.updated_at = now
        updated = await self._repository.update(
            ServiceRequestDocument.model_validate(document.model_dump())
        )

        if not mark_completed or updated.status in {"completed", "failed", "cancelled"}:
            return updated

        if updated.status in {"created", "in_progress"}:
            if updated.status == "created":
                updated = await self.transition(
                    service_request_id,
                    "in_progress",
                    actor=actor,
                    sync_ticket=False,
                )
            return await self.transition(
                service_request_id,
                "completed",
                actor=actor,
                sync_ticket=False,
            )

        return updated

    async def fail_and_prepare_escalation(
        self,
        service_request_id: str,
        *,
        actor: ServiceRequestActor = "system",
    ) -> tuple[ServiceRequestDocument, TicketDocument]:
        sr = await self.transition(
            service_request_id,
            "failed",
            actor=actor,
            sync_ticket=True,
        )
        ticket = await self._ticket_service.get_ticket(sr.ticket_id)
        return sr, ticket

    def _validate_ticket_for_create(self, ticket: TicketDocument) -> None:
        if ticket.ticket_class != TICKET_CLASS_TIER_1:
            raise ServiceRequestValidationError(
                "service requests can only be created for tier_1_service_request tickets"
            )
        if ticket.service_request_id is not None:
            raise ServiceRequestValidationError(
                "ticket already has a linked service_request_id"
            )
        if ticket.status != "open":
            raise ServiceRequestValidationError(
                f"service request creation requires ticket status 'open', got '{ticket.status}'"
            )
