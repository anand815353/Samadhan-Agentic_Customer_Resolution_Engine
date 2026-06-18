"""Orchestrate consolidated workflow audit persistence."""

from __future__ import annotations

import logging

from app.agent.exceptions import AuditNodePersistenceError, AuditNodeValidationError
from app.agent.workflow_audit.tool_audit_link_validator import collect_linked_tool_audit_ids
from app.agent.workflow_audit.workflow_audit_builder import (
    build_workflow_audit_event,
    workflow_audit_fingerprint,
)
from app.agent.workflow_audit.workflow_audit_types import WorkflowAuditCommand, WorkflowAuditResult
from app.audit.exceptions import AuditValidationError
from app.audit.services import AuditService
from app.messages.services import MessageService
from app.tickets.services import TicketService

logger = logging.getLogger("samadhan.agent")


class WorkflowAuditService:
    """Persist one consolidated workflow_completed audit per workflow invocation."""

    def __init__(
        self,
        *,
        audit_service: AuditService,
        ticket_service: TicketService,
        message_service: MessageService,
    ) -> None:
        self._audit_service = audit_service
        self._ticket_service = ticket_service
        self._message_service = message_service

    async def persist(self, command: WorkflowAuditCommand) -> WorkflowAuditResult:
        state = command.state

        try:
            linked_tool_audit_ids = await collect_linked_tool_audit_ids(
                state,
                self._audit_service,
            )
        except AuditNodeValidationError:
            raise

        event_create = build_workflow_audit_event(
            state,
            linked_tool_audit_ids=linked_tool_audit_ids,
        )
        fingerprint = workflow_audit_fingerprint(
            state,
            linked_tool_audit_ids=linked_tool_audit_ids,
        )

        await self._validate_persisted_links(state)

        existing = await self._audit_service.find_workflow_completed(state.workflow_id)
        if existing is not None:
            existing_fp = None
            if existing.raw_internal_trace:
                existing_fp = existing.raw_internal_trace.get("idempotency_fingerprint")
            if existing_fp == fingerprint:
                logger.info(
                    "workflow audit replay workflow_id=%s audit_id=%s",
                    state.workflow_id,
                    existing.audit_id,
                )
                return WorkflowAuditResult(
                    workflow_audit_id=existing.audit_id,
                    event_type=existing.event_type,
                    linked_tool_audit_ids=linked_tool_audit_ids,
                    langsmith_trace_id=existing.langsmith_trace_id,
                    workflow_status="completed",
                    idempotent_replay=True,
                    persisted_at=existing.created_at,
                )
            raise AuditNodeValidationError(
                f"workflow audit already exists for {state.workflow_id} with different payload",
            )

        try:
            saved = await self._audit_service.record_workflow_completed(event_create)
        except AuditValidationError as exc:
            raise AuditNodeValidationError(str(exc)) from exc
        except Exception as exc:
            raise AuditNodePersistenceError("failed to persist workflow audit") from exc

        logger.info(
            "workflow audit persisted workflow_id=%s audit_id=%s tool_audits=%s trace=%s",
            state.workflow_id,
            saved.audit_id,
            len(linked_tool_audit_ids),
            bool(saved.langsmith_trace_id),
        )
        return WorkflowAuditResult(
            workflow_audit_id=saved.audit_id,
            event_type=saved.event_type,
            linked_tool_audit_ids=linked_tool_audit_ids,
            langsmith_trace_id=saved.langsmith_trace_id,
            workflow_status="completed",
            idempotent_replay=False,
            persisted_at=saved.created_at,
        )

    async def _validate_persisted_links(self, state) -> None:
        ticket = await self._ticket_service.get_ticket(state.ticket_id)  # type: ignore[arg-type]
        if ticket.customer_id != state.customer_id:
            raise AuditNodeValidationError("ticket does not belong to customer")
        if state.session_id and ticket.session_id != state.session_id:
            raise AuditNodeValidationError("ticket session_id does not match workflow state")

        customer_message = await self._message_service.get_message(
            state.message_id,  # type: ignore[arg-type]
            actor="system",
        )
        if customer_message.ticket_id != state.ticket_id:
            raise AuditNodeValidationError("customer message is not linked to ticket")
        if customer_message.customer_id != state.customer_id:
            raise AuditNodeValidationError("customer message customer mismatch")

        ai_message_id = state.ticket_update.ai_message_id  # type: ignore[union-attr]
        ai_message = await self._message_service.get_message(ai_message_id, actor="system")
        if ai_message.ticket_id != state.ticket_id:
            raise AuditNodeValidationError("AI message is not linked to ticket")
        if ai_message.sender_type != "ai":
            raise AuditNodeValidationError("persisted message is not an AI message")
