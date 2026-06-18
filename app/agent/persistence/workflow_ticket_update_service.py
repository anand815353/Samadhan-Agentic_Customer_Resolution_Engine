"""Orchestrate workflow ticket updates after response generation."""

from __future__ import annotations

import logging

from app.agent.exceptions import TicketUpdatePersistenceError, TicketUpdateValidationError
from app.agent.persistence.ai_message_idempotency import persist_ai_message
from app.agent.persistence.persistence_types import (
    WorkflowTicketUpdateCommand,
    WorkflowTicketUpdateResult,
)
from app.agent.persistence.service_request_validator import validate_service_request_link
from app.agent.persistence.ticket_class_policy import merge_ticket_class
from app.messages.repositories import MessageRepository
from app.messages.services import MessageService
from app.service_requests.models import ServiceRequestDocument
from app.service_requests.services import ServiceRequestService
from app.tickets.constants import TICKET_CLASS_HUMAN_REVIEW, TicketStatus
from app.tickets.exceptions import InvalidTicketTransitionError, StaleTicketUpdateError
from app.agent.persistence.stale_ticket_policy import assert_ticket_mutable_for_workflow
from app.tickets.lifecycle import can_transition
from app.tickets.models import TicketDocument
from app.tickets.services import TicketService

logger = logging.getLogger("samadhan.agent")

_FORBIDDEN_PLANNED_STATUSES: frozenset[TicketStatus] = frozenset(
    {
        "auto_closed",
        "closed",
        "under_review",
        "resolved_by_agent",
        "escalated_further",
    }
)

_SR_REQUIRED_STATUSES: frozenset[TicketStatus] = frozenset(
    {
        "service_requested",
        "service_completed",
    }
)


class WorkflowTicketUpdateService:
    """Persist AI message, promote ticket class, and apply lifecycle transitions."""

    def __init__(
        self,
        *,
        ticket_service: TicketService,
        message_service: MessageService,
        message_repository: MessageRepository,
        service_request_service: ServiceRequestService,
    ) -> None:
        self._ticket_service = ticket_service
        self._message_service = message_service
        self._message_repository = message_repository
        self._service_request_service = service_request_service

    async def persist(self, command: WorkflowTicketUpdateCommand) -> WorkflowTicketUpdateResult:
        state = command.state
        plan = command.resolution_plan
        response_text = command.customer_response.strip()

        if not state.ticket_id:
            raise TicketUpdateValidationError("ticket_id is required")
        if not state.customer_id:
            raise TicketUpdateValidationError("customer_id is required")
        if not state.session_id:
            raise TicketUpdateValidationError("session_id is required")
        if not state.workflow_id:
            raise TicketUpdateValidationError("workflow_id is required")
        if not response_text:
            raise TicketUpdateValidationError("customer_response is required")
        if plan.ticket_status is None:
            raise TicketUpdateValidationError("resolution_plan.ticket_status is required")

        planned_status = plan.ticket_status
        if planned_status in _FORBIDDEN_PLANNED_STATUSES:
            raise TicketUpdateValidationError(
                f"ticket status {planned_status} is not allowed for workflow persistence",
            )

        ticket = await self._ticket_service.get_ticket(state.ticket_id)
        if ticket.customer_id != state.customer_id:
            raise TicketUpdateValidationError("ticket does not belong to customer")
        if ticket.session_id != state.session_id:
            raise TicketUpdateValidationError("ticket session_id does not match workflow state")

        if state.message_id:
            try:
                customer_message = await self._message_service.get_message(
                    state.message_id,
                    actor="system",
                )
            except Exception as exc:
                raise TicketUpdateValidationError(
                    f"customer message not found: {state.message_id}",
                ) from exc
            if customer_message.ticket_id != state.ticket_id:
                raise TicketUpdateValidationError("customer message is not linked to ticket")

        previous_status = ticket.status
        previous_class = ticket.ticket_class
        expected_from_status = previous_status

        assert_ticket_mutable_for_workflow(
            ticket,
            planned_status=planned_status,
            ticket_id=state.ticket_id,
        )

        service_request_id = plan.service_request_id
        sr_document: ServiceRequestDocument | None = None
        if planned_status in _SR_REQUIRED_STATUSES:
            if not service_request_id:
                raise TicketUpdateValidationError(
                    "service_request_id is required for service ticket updates",
                )
            sr_document = await validate_service_request_link(
                self._service_request_service,
                service_request_id=service_request_id,
                ticket_id=state.ticket_id,
                customer_id=state.customer_id,
            )

        try:
            ai_message, idempotent_replay = await persist_ai_message(
                self._message_service,
                self._message_repository,
                state,
                customer_response=response_text,
            )
        except TicketUpdateValidationError:
            raise
        except Exception as exc:
            raise TicketUpdatePersistenceError("failed to persist AI message") from exc

        try:
            synced = await self._ticket_service.sync_workflow_metadata(
                state.ticket_id,
                desired_ticket_class=plan.ticket_class,
                intent=plan.intent,
                risk_level=plan.risk_level,
                priority=plan.priority,
                escalation_reason=plan.escalation_reason,
                service_request_id=service_request_id,
            )
        except InvalidTicketTransitionError as exc:
            raise TicketUpdateValidationError(str(exc)) from exc

        class_preserved = (
            previous_class == synced.ticket_class
            and merge_ticket_class(previous_class, plan.ticket_class) == previous_class
            and plan.ticket_class != previous_class
        )

        status_idempotent = synced.status == planned_status
        updated_ticket = synced
        should_apply_status = (
            not status_idempotent
            and (
                can_transition(
                    ticket_class=synced.ticket_class,
                    from_status=synced.status,
                    to_status=planned_status,
                    actor="system",
                )
                or planned_status == "service_completed"
            )
        )
        if should_apply_status:
            updated_ticket = await self._apply_planned_status(
                state.ticket_id,
                planned_status=planned_status,
                escalation_reason=plan.escalation_reason,
                service_request_id=service_request_id,
                expected_from_status=expected_from_status,
            )

        document_path = sr_document.document_path if sr_document is not None else None
        human_review_queued = (
            updated_ticket.ticket_class == TICKET_CLASS_HUMAN_REVIEW
            and updated_ticket.status == "escalated_to_human"
        )

        update_summary = self._build_update_summary(
            previous_status=previous_status,
            ticket=updated_ticket,
            planned_status=planned_status,
            class_preserved=class_preserved,
        )

        logger.info(
            "ticket update persisted workflow_id=%s ticket_id=%s status=%s class=%s ai_message=%s replay=%s",
            state.workflow_id,
            state.ticket_id,
            updated_ticket.status,
            updated_ticket.ticket_class,
            ai_message.message_id,
            idempotent_replay or status_idempotent,
        )

        return WorkflowTicketUpdateResult(
            ticket_status=updated_ticket.status,
            service_request_id=updated_ticket.service_request_id,
            update_summary=update_summary,
            document_path=document_path,
            ai_message_id=ai_message.message_id,
            previous_ticket_class=previous_class,
            persisted_ticket_class=updated_ticket.ticket_class,
            previous_status=previous_status,
            human_review_queued=human_review_queued,
            idempotent_replay=idempotent_replay and status_idempotent,
            class_preserved=class_preserved,
        )

    async def _apply_planned_status(
        self,
        ticket_id: str,
        *,
        planned_status: TicketStatus,
        escalation_reason: str | None,
        service_request_id: str | None,
        expected_from_status: str,
    ) -> TicketDocument:
        ticket = await self._ticket_service.get_ticket(ticket_id)
        if ticket.status == planned_status:
            return ticket

        try:
            if planned_status == "escalated_to_human":
                return await self._ticket_service.escalate_to_human_review(
                    ticket_id,
                    reason=escalation_reason or "Workflow escalation",
                    actor="system",
                )

            if planned_status == "service_completed":
                return await self._apply_service_completed(
                    ticket_id,
                    service_request_id=service_request_id,
                    expected_from_status=expected_from_status,
                )

            return await self._ticket_service.transition(
                ticket_id,
                planned_status,
                actor="system",
                reason=escalation_reason,
                service_request_id=service_request_id,
                expected_from_status=expected_from_status,
            )
        except StaleTicketUpdateError:
            raise TicketUpdateValidationError(
                f"ticket {ticket_id} changed before status transition could apply",
            )
        except InvalidTicketTransitionError as exc:
            if planned_status == "service_completed":
                return await self._apply_service_completed(
                    ticket_id,
                    service_request_id=service_request_id,
                    expected_from_status=None,
                )
            raise TicketUpdateValidationError(str(exc)) from exc

    async def _apply_service_completed(
        self,
        ticket_id: str,
        *,
        service_request_id: str | None,
        expected_from_status: str | None,
    ) -> TicketDocument:
        ticket = await self._ticket_service.get_ticket(ticket_id)
        if ticket.status == "service_completed":
            return ticket

        if ticket.status == "open":
            ticket = await self._ticket_service.transition(
                ticket_id,
                "service_requested",
                actor="system",
                service_request_id=service_request_id,
                expected_from_status=expected_from_status,
            )
            expected_from_status = None

        if ticket.status == "service_requested":
            ticket = await self._ticket_service.transition(
                ticket_id,
                "in_progress",
                actor="system",
                expected_from_status=expected_from_status,
            )

        if ticket.status == "in_progress":
            return await self._ticket_service.transition(
                ticket_id,
                "service_completed",
                actor="system",
            )

        return await self._ticket_service.transition(
            ticket_id,
            "service_completed",
            actor="system",
        )

    @staticmethod
    def _build_update_summary(
        *,
        previous_status: TicketStatus,
        ticket: TicketDocument,
        planned_status: TicketStatus,
        class_preserved: bool,
    ) -> str:
        parts = [f"status {previous_status} -> {ticket.status}"]
        if class_preserved:
            parts.append("class preserved")
        elif ticket.ticket_class:
            parts.append(f"class {ticket.ticket_class}")
        if ticket.status != planned_status:
            parts.append(f"planned {planned_status}")
        summary = "; ".join(parts)
        return summary[:200]
