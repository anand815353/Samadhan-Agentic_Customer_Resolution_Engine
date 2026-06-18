"""Audit log business logic: safe event creation and retrieval."""

from __future__ import annotations

from typing import Any

from app.audit.constants import AuditCreatedBy, AuditEventType
from app.audit.exceptions import AuditValidationError
from app.audit.id_generation import allocate_audit_id
from app.audit.models import AuditLogDocument
from app.audit.repositories import AuditLogRepository
from app.audit.schemas import AuditEventCreate, audit_document_from_create
from app.common.masking import sensitive_violation_kind
from app.common.service import BaseService
from app.core.exceptions import NotFoundError
from app.messages.services import MessageService
from app.tickets.constants import Priority, RiskLevel, TicketIntent
from app.tickets.services import TicketService


class AuditService(BaseService):
    """Domain service for append-only audit log persistence."""

    def __init__(
        self,
        repository: AuditLogRepository,
        ticket_service: TicketService | None = None,
        message_service: MessageService | None = None,
    ) -> None:
        self._repository = repository
        self._ticket_service = ticket_service
        self._message_service = message_service

    async def create_event(
        self,
        data: AuditEventCreate,
        *,
        audit_id: str | None = None,
        validate_links: bool = True,
    ) -> AuditLogDocument:
        self._validate_masked_fields(data)

        if validate_links:
            await self._validate_links(data)

        resolved_id = audit_id or data.audit_id
        if resolved_id is None:
            resolved_id = await allocate_audit_id(self._repository)
        elif await self._repository.find_by_id(resolved_id) is not None:
            raise AuditValidationError(f"audit event already exists: {resolved_id}")

        document = audit_document_from_create(data, audit_id=resolved_id)
        return await self._repository.insert(document)

    async def get_event(self, audit_id: str) -> AuditLogDocument:
        document = await self._repository.find_by_id(audit_id)
        if document is None:
            raise NotFoundError(f"audit event not found: {audit_id}")
        return document

    async def list_for_ticket(self, ticket_id: str, *, limit: int = 200) -> list[AuditLogDocument]:
        return await self._repository.find_by_ticket(ticket_id, limit=limit)

    async def list_for_message(self, message_id: str, *, limit: int = 50) -> list[AuditLogDocument]:
        return await self._repository.find_by_message(message_id, limit=limit)

    async def list_for_customer(
        self,
        customer_id: str,
        *,
        limit: int = 50,
    ) -> list[AuditLogDocument]:
        return await self._repository.find_by_customer(customer_id, limit=limit)

    async def list_by_event_type(
        self,
        event_type: AuditEventType,
        *,
        limit: int = 100,
    ) -> list[AuditLogDocument]:
        return await self._repository.find_by_event_type(event_type, limit=limit)

    async def record_intent_classified(
        self,
        *,
        ticket_id: str,
        message_id: str | None = None,
        customer_id: str | None = None,
        intent: TicketIntent,
        confidence: float | None = None,
        created_by: AuditCreatedBy = "system",
        validate_links: bool = True,
    ) -> AuditLogDocument:
        return await self.create_event(
            AuditEventCreate(
                event_type="intent_classified",
                ticket_id=ticket_id,
                message_id=message_id,
                customer_id=customer_id,
                intent=intent,
                confidence=confidence,
                created_by=created_by,
            ),
            validate_links=validate_links,
        )

    async def record_risk_classified(
        self,
        *,
        ticket_id: str,
        message_id: str | None = None,
        customer_id: str | None = None,
        intent: TicketIntent | None = None,
        risk_level: RiskLevel,
        priority: Priority,
        created_by: AuditCreatedBy = "system",
        validate_links: bool = True,
    ) -> AuditLogDocument:
        return await self.create_event(
            AuditEventCreate(
                event_type="risk_classified",
                ticket_id=ticket_id,
                message_id=message_id,
                customer_id=customer_id,
                intent=intent,
                risk_level=risk_level,
                priority=priority,
                created_by=created_by,
            ),
            validate_links=validate_links,
        )

    async def record_ticket_routed(
        self,
        *,
        ticket_id: str,
        customer_id: str | None = None,
        intent: TicketIntent | None = None,
        risk_level: RiskLevel | None = None,
        priority: Priority | None = None,
        action_taken: str,
        created_by: AuditCreatedBy = "system",
        validate_links: bool = True,
    ) -> AuditLogDocument:
        return await self.create_event(
            AuditEventCreate(
                event_type="ticket_routed",
                ticket_id=ticket_id,
                customer_id=customer_id,
                intent=intent,
                risk_level=risk_level,
                priority=priority,
                action_taken=action_taken,
                created_by=created_by,
            ),
            validate_links=validate_links,
        )

    async def record_retrieval_performed(
        self,
        *,
        ticket_id: str,
        message_id: str | None = None,
        customer_id: str | None = None,
        retrieved_policy_ids: list[str],
        customer_safe_summary: str | None = None,
        created_by: AuditCreatedBy = "system",
        validate_links: bool = True,
    ) -> AuditLogDocument:
        return await self.create_event(
            AuditEventCreate(
                event_type="retrieval_performed",
                ticket_id=ticket_id,
                message_id=message_id,
                customer_id=customer_id,
                retrieved_policy_ids=retrieved_policy_ids,
                customer_safe_summary=customer_safe_summary,
                created_by=created_by,
            ),
            validate_links=validate_links,
        )

    async def record_tool_planned(
        self,
        *,
        ticket_id: str,
        customer_id: str | None = None,
        tool_name: str,
        tool_input_masked: dict[str, Any] | str | None = None,
        created_by: AuditCreatedBy = "system",
        validate_links: bool = True,
    ) -> AuditLogDocument:
        return await self.create_event(
            AuditEventCreate(
                event_type="tool_planned",
                ticket_id=ticket_id,
                customer_id=customer_id,
                tool_name=tool_name,
                tool_input_masked=tool_input_masked,
                created_by=created_by,
            ),
            validate_links=validate_links,
        )

    async def record_tool_called(
        self,
        *,
        ticket_id: str,
        customer_id: str | None = None,
        tool_name: str,
        tool_input_masked: dict[str, Any] | str | None = None,
        tool_output_summary: dict[str, Any] | str | None = None,
        action_taken: str | None = None,
        customer_safe_summary: str | None = None,
        escalation_required: bool | None = None,
        service_request_id: str | None = None,
        intent: TicketIntent | None = None,
        workflow_id: str | None = None,
        created_by: AuditCreatedBy = "system",
        validate_links: bool = True,
    ) -> AuditLogDocument:
        return await self.create_event(
            AuditEventCreate(
                event_type="tool_called",
                ticket_id=ticket_id,
                customer_id=customer_id,
                intent=intent,
                tool_name=tool_name,
                tool_input_masked=tool_input_masked,
                tool_output_summary=tool_output_summary,
                action_taken=action_taken,
                customer_safe_summary=customer_safe_summary,
                escalation_required=escalation_required,
                service_request_id=service_request_id,
                workflow_id=workflow_id,
                created_by=created_by,
            ),
            validate_links=validate_links,
        )

    async def record_guardrail_decided(
        self,
        *,
        ticket_id: str,
        message_id: str | None = None,
        customer_id: str | None = None,
        decision: dict[str, Any] | str,
        escalation_required: bool | None = None,
        customer_safe_summary: str | None = None,
        created_by: AuditCreatedBy = "system",
        validate_links: bool = True,
    ) -> AuditLogDocument:
        return await self.create_event(
            AuditEventCreate(
                event_type="guardrail_decided",
                ticket_id=ticket_id,
                message_id=message_id,
                customer_id=customer_id,
                decision=decision,
                escalation_required=escalation_required,
                customer_safe_summary=customer_safe_summary,
                created_by=created_by,
            ),
            validate_links=validate_links,
        )

    async def record_response_generated(
        self,
        *,
        ticket_id: str,
        message_id: str | None = None,
        customer_id: str | None = None,
        customer_safe_summary: str,
        created_by: AuditCreatedBy = "ai",
        validate_links: bool = True,
    ) -> AuditLogDocument:
        return await self.create_event(
            AuditEventCreate(
                event_type="response_generated",
                ticket_id=ticket_id,
                message_id=message_id,
                customer_id=customer_id,
                customer_safe_summary=customer_safe_summary,
                created_by=created_by,
            ),
            validate_links=validate_links,
        )

    async def record_ticket_updated(
        self,
        *,
        ticket_id: str,
        customer_id: str | None = None,
        action_taken: str,
        internal_summary: str | None = None,
        created_by: AuditCreatedBy = "system",
        validate_links: bool = True,
    ) -> AuditLogDocument:
        return await self.create_event(
            AuditEventCreate(
                event_type="ticket_updated",
                ticket_id=ticket_id,
                customer_id=customer_id,
                action_taken=action_taken,
                internal_summary=internal_summary,
                created_by=created_by,
            ),
            validate_links=validate_links,
        )

    async def record_service_request_created(
        self,
        *,
        ticket_id: str,
        service_request_id: str,
        customer_id: str | None = None,
        customer_safe_summary: str | None = None,
        created_by: AuditCreatedBy = "system",
        validate_links: bool = True,
    ) -> AuditLogDocument:
        return await self.create_event(
            AuditEventCreate(
                event_type="service_request_created",
                ticket_id=ticket_id,
                service_request_id=service_request_id,
                customer_id=customer_id,
                customer_safe_summary=customer_safe_summary,
                created_by=created_by,
            ),
            validate_links=validate_links,
        )

    async def record_error(
        self,
        *,
        ticket_id: str | None = None,
        message_id: str | None = None,
        customer_id: str | None = None,
        internal_summary: str,
        customer_safe_summary: str | None = None,
        workflow_id: str | None = None,
        created_by: AuditCreatedBy = "system",
        validate_links: bool = True,
    ) -> AuditLogDocument:
        return await self.create_event(
            AuditEventCreate(
                event_type="error_recorded",
                ticket_id=ticket_id,
                message_id=message_id,
                customer_id=customer_id,
                internal_summary=internal_summary,
                customer_safe_summary=customer_safe_summary,
                workflow_id=workflow_id,
                created_by=created_by,
            ),
            validate_links=validate_links,
        )

    async def find_workflow_completed(self, workflow_id: str) -> AuditLogDocument | None:
        """Return the latest workflow_completed audit for a workflow, if any."""
        matches = await self._repository.find_by_workflow_id(
            workflow_id,
            event_type="workflow_completed",
            limit=1,
        )
        return matches[0] if matches else None

    async def record_workflow_completed(
        self,
        data: AuditEventCreate,
        *,
        validate_links: bool = True,
    ) -> AuditLogDocument:
        if data.event_type != "workflow_completed":
            raise AuditValidationError("record_workflow_completed requires workflow_completed event_type")
        return await self.create_event(data, validate_links=validate_links)

    async def _validate_links(self, data: AuditEventCreate) -> None:
        if data.message_id and self._message_service is not None:
            message = await self._message_service.get_message(data.message_id, actor="system")
            if data.ticket_id and data.ticket_id != message.ticket_id:
                raise AuditValidationError(
                    "message_id does not belong to the provided ticket_id"
                )
            if data.customer_id and data.customer_id != message.customer_id:
                raise AuditValidationError(
                    "customer_id does not match linked message customer_id"
                )

        if data.ticket_id and self._ticket_service is not None:
            ticket = await self._ticket_service.get_ticket(data.ticket_id)
            if data.customer_id and data.customer_id != ticket.customer_id:
                raise AuditValidationError(
                    "customer_id does not match linked ticket customer_id"
                )

    def _validate_masked_fields(self, data: AuditEventCreate) -> None:
        if data.customer_safe_summary:
            self._reject_sensitive_patterns(data.customer_safe_summary, field="customer_safe_summary")

        if isinstance(data.tool_input_masked, str):
            self._reject_sensitive_patterns(data.tool_input_masked, field="tool_input_masked")
        elif isinstance(data.tool_input_masked, dict):
            self._reject_sensitive_dict_values(data.tool_input_masked, field="tool_input_masked")

        if isinstance(data.tool_output_summary, str):
            self._reject_sensitive_patterns(data.tool_output_summary, field="tool_output_summary")
        elif isinstance(data.tool_output_summary, dict):
            self._reject_sensitive_dict_values(data.tool_output_summary, field="tool_output_summary")

        if data.raw_internal_trace is not None:
            self._reject_sensitive_dict_values(data.raw_internal_trace, field="raw_internal_trace")

        if data.internal_summary:
            self._reject_sensitive_patterns(data.internal_summary, field="internal_summary")

    def _reject_sensitive_dict_values(self, payload: dict[str, Any], *, field: str) -> None:
        for value in payload.values():
            if isinstance(value, str):
                self._reject_sensitive_patterns(value, field=field)
            elif isinstance(value, dict):
                self._reject_sensitive_dict_values(value, field=field)

    def _reject_sensitive_patterns(self, value: str, *, field: str) -> None:
        violation = sensitive_violation_kind(value)
        if violation is not None:
            raise AuditValidationError(f"{field} must not contain unmasked {violation} values")
