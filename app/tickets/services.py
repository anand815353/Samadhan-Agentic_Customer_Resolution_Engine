"""Ticket business logic: creation, lifecycle transitions, and escalation."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import ValidationError

from app.common.service import BaseService
from app.core.exceptions import ConflictError, NotFoundError
from app.tickets.constants import (
    Priority,
    RiskLevel,
    TERMINAL_STATUSES,
    TICKET_CLASS_HUMAN_REVIEW,
    TICKET_CLASS_TIER_1,
    TicketClass,
    TicketIntent,
    TransitionActor,
)
from app.tickets.exceptions import InvalidTicketTransitionError, StaleTicketUpdateError
from app.tickets.id_generation import allocate_ticket_id
from app.tickets.lifecycle import apply_transition
from app.tickets.models import TicketDocument
from app.tickets.repositories import TicketRepository
from app.tickets.risk_rules import validate_risk_priority_rules
from app.tickets.schemas import TicketCreate, ticket_document_from_create


class TicketService(BaseService):
    """Domain service for ticket creation and lifecycle management."""

    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    async def create_ticket(
        self,
        data: TicketCreate,
        *,
        actor: TransitionActor = "system",
    ) -> TicketDocument:
        ticket_id = data.ticket_id
        if ticket_id is None:
            ticket_id = await allocate_ticket_id(self._repository)
        else:
            existing = await self._repository.find_by_id(ticket_id)
            if existing is not None:
                raise ConflictError(f"ticket already exists: {ticket_id}")

        document = ticket_document_from_create(data, ticket_id=ticket_id)
        return await self._repository.insert(document)

    async def get_ticket(self, ticket_id: str) -> TicketDocument:
        document = await self._repository.find_by_id(ticket_id)
        if document is None:
            raise NotFoundError(f"ticket not found: {ticket_id}")
        return document

    async def list_customer_tickets(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[TicketDocument]:
        return await self._repository.find_by_customer(customer_id, limit=limit)

    async def transition(
        self,
        ticket_id: str,
        to_status: str,
        *,
        actor: TransitionActor,
        reason: str | None = None,
        admin_override: bool = False,
        service_request_id: str | None = None,
        expected_from_status: str | None = None,
    ) -> TicketDocument:
        document = await self.get_ticket(ticket_id)
        from_status = document.status

        if expected_from_status is not None and from_status != expected_from_status:
            raise StaleTicketUpdateError(
                f"ticket {ticket_id} status changed from {expected_from_status} to {from_status}",
                ticket_id=ticket_id,
                expected_status=expected_from_status,
                actual_status=from_status,
            )

        try:
            result = apply_transition(
                ticket_class=document.ticket_class,
                from_status=from_status,
                to_status=to_status,  # type: ignore[arg-type]
                actor=actor,
                admin_override=admin_override,
            )
        except InvalidTicketTransitionError as exc:
            exc.ticket_id = ticket_id
            raise

        if to_status == "service_requested" and not document.service_request_id:
            if not service_request_id:
                raise InvalidTicketTransitionError(
                    "service_request_id required for service_requested transition",
                    ticket_id=ticket_id,
                    from_status=from_status,
                    to_status=to_status,
                )
            document.service_request_id = service_request_id

        now = datetime.now(UTC)
        document.status = result.new_status
        document.ticket_class = result.new_ticket_class
        document.updated_at = now

        if result.class_mutated:
            document.escalation_reason = reason or document.escalation_reason or "Escalated from tier_1 failure"

        if to_status == "escalated_to_human" and reason:
            document.escalation_reason = reason

        if to_status in TERMINAL_STATUSES:
            document.closed_at = now
            document.closure_reason = reason or document.closure_reason
        elif admin_override and from_status == "closed" and to_status == "open":
            document.closed_at = None
            document.closure_reason = None

        try:
            validated = TicketDocument.model_validate(document.model_dump())
        except ValidationError as exc:
            raise InvalidTicketTransitionError(
                f"transition produced invalid ticket state: {exc}",
                ticket_id=ticket_id,
                from_status=from_status,
                to_status=to_status,
            ) from exc

        return await self._repository.update(validated)

    async def escalate_to_human_review(
        self,
        ticket_id: str,
        *,
        reason: str,
        actor: TransitionActor = "system",
    ) -> TicketDocument:
        document = await self.get_ticket(ticket_id)
        if document.ticket_class == TICKET_CLASS_HUMAN_REVIEW:
            if document.status == "escalated_to_human":
                return document
            return await self.transition(
                ticket_id,
                "escalated_to_human",
                actor=actor,
                reason=reason,
            )

        return await self.transition(
            ticket_id,
            "escalated_to_human",
            actor=actor,
            reason=reason,
            admin_override=(actor == "admin"),
        )

    async def assign_agent(
        self,
        ticket_id: str,
        agent_id: str,
        *,
        actor: TransitionActor = "support_agent",
        move_to_under_review: bool = True,
    ) -> TicketDocument:
        document = await self.get_ticket(ticket_id)
        if document.ticket_class != TICKET_CLASS_HUMAN_REVIEW:
            raise InvalidTicketTransitionError(
                "agent assignment is only for human_review tickets",
                ticket_id=ticket_id,
            )

        document.assigned_agent_id = agent_id
        document.updated_at = datetime.now(UTC)

        if move_to_under_review and document.status == "escalated_to_human":
            return await self.transition(
                ticket_id,
                "under_review",
                actor=actor,
            )

        validated = TicketDocument.model_validate(document.model_dump())
        return await self._repository.update(validated)

    async def sync_workflow_metadata(
        self,
        ticket_id: str,
        *,
        desired_ticket_class: TicketClass,
        intent: TicketIntent,
        risk_level: RiskLevel,
        priority: Priority,
        escalation_reason: str | None = None,
        service_request_id: str | None = None,
    ) -> TicketDocument:
        """Promote ticket class and sync workflow metadata without changing status."""
        document = await self.get_ticket(ticket_id)
        previous_class = document.ticket_class

        from app.agent.persistence.ticket_class_policy import merge_ticket_class

        merged_class = merge_ticket_class(document.ticket_class, desired_ticket_class)
        document.ticket_class = merged_class

        if merged_class != previous_class or document.intent == "unknown":
            document.intent = intent
            document.risk_level = risk_level
            document.priority = priority

        if escalation_reason and merged_class == TICKET_CLASS_HUMAN_REVIEW:
            document.escalation_reason = escalation_reason

        if service_request_id and merged_class == TICKET_CLASS_TIER_1:
            if document.service_request_id is None:
                document.service_request_id = service_request_id
            elif document.service_request_id != service_request_id:
                raise InvalidTicketTransitionError(
                    f"ticket already linked to service request {document.service_request_id}",
                    ticket_id=ticket_id,
                )

        validate_risk_priority_rules(
            intent=document.intent,
            risk_level=document.risk_level,
            priority=document.priority,
            ticket_class=document.ticket_class,
        )

        document.updated_at = datetime.now(UTC)
        validated = TicketDocument.model_validate(document.model_dump())
        return await self._repository.update(validated)

    async def touch_message_snapshots(
        self,
        ticket_id: str,
        *,
        last_customer_message: str | None = None,
        last_ai_response: str | None = None,
    ) -> TicketDocument:
        """Update denormalized last message fields without lifecycle transition."""
        document = await self.get_ticket(ticket_id)
        if last_customer_message is not None:
            document.last_customer_message = last_customer_message
        if last_ai_response is not None:
            document.last_ai_response = last_ai_response
        document.updated_at = datetime.now(UTC)
        validated = TicketDocument.model_validate(document.model_dump())
        return await self._repository.update(validated)
