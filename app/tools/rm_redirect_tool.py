"""RMRedirectTool — read RM mapping and create mock callback service requests."""

from __future__ import annotations

from typing import Any

from app.common.masking import mask_email, mask_mobile
from app.customers.repositories import CustomerRepository
from app.rm_mapping.models import RmMappingDocument
from app.rm_mapping.repositories import RmMappingRepository
from app.service_requests.exceptions import ServiceRequestValidationError
from app.service_requests.services import ServiceRequestService
from app.tickets.constants import TicketIntent
from app.tools.audit_hook import ToolAuditHook
from app.tools.base import BaseMockTool
from app.tools.constants import ToolName
from app.tools.exceptions import ToolExecutionError, ToolValidationError
from app.tools.schemas import ToolInput, ToolRunResult

SUPPORTED_INTENTS: frozenset[TicketIntent] = frozenset({"rm_redirection"})

_NO_RM_SUMMARY = (
    "I could not find an assigned relationship manager for this demo customer."
)
_UNAVAILABLE_SUMMARY = (
    "I found your assigned relationship manager in the demo records, but callback "
    "is not available right now."
)
_CALLBACK_CREATED_SUMMARY = (
    "I found your assigned relationship manager in the demo records and created a "
    "mock callback request. This does not send a real call, SMS, or email."
)
_CALLBACK_REUSED_SUMMARY = (
    "I found your assigned relationship manager in the demo records. Your mock "
    "callback request is already on record and in progress."
)
_MAPPING_CHECKED_SUMMARY = (
    "I found your assigned relationship manager in the demo records."
)
_SR_SUMMARY = "Your relationship manager callback request has been registered."


class RMRedirectTool(BaseMockTool):
    """Mock tool to read RM mapping and create or reuse callback service requests."""

    def __init__(
        self,
        customer_repository: CustomerRepository,
        rm_mapping_repository: RmMappingRepository,
        service_request_service: ServiceRequestService | None = None,
        audit_hook: ToolAuditHook | None = None,
    ) -> None:
        super().__init__(audit_hook=audit_hook)
        self._customer_repository = customer_repository
        self._rm_mapping_repository = rm_mapping_repository
        self._service_request_service = service_request_service

    @property
    def tool_name(self) -> ToolName:
        return "RMRedirectTool"

    def validate_input(self, tool_input: ToolInput) -> None:
        if tool_input.intent not in SUPPORTED_INTENTS:
            raise ToolValidationError(
                f"RMRedirectTool does not support intent: {tool_input.intent}"
            )

    async def _run(self, tool_input: ToolInput) -> ToolRunResult:
        customer = await self._customer_repository.find_by_id(tool_input.customer_id)
        if customer is None:
            raise ToolExecutionError(
                "Customer record was not found for this demo profile.",
                code="not_found",
                retryable=False,
            )

        mappings = await self._rm_mapping_repository.find_by_customer(tool_input.customer_id)
        mapping = _select_mapping(mappings)
        if mapping is None:
            return ToolRunResult(
                data={},
                customer_safe_summary=_NO_RM_SUMMARY,
                action_taken="rm_mapping_not_found",
                escalation_required=False,
            )

        if not mapping.callback_available:
            return ToolRunResult(
                data=_build_safe_data(mapping),
                customer_safe_summary=_UNAVAILABLE_SUMMARY,
                action_taken="rm_callback_unavailable",
                escalation_required=False,
            )

        should_request_callback = _should_request_callback(
            tool_input.intent,
            parameters=tool_input.parameters,
        )
        service_request_id: str | None = None
        callback_request_created: bool | None = None
        action_taken = "rm_mapping_checked"
        summary = _MAPPING_CHECKED_SUMMARY

        if should_request_callback and self._service_request_service is not None:
            sr_id, created_new = await _get_or_create_rm_callback_sr(
                self._service_request_service,
                ticket_id=tool_input.ticket_id,
                customer_safe_summary=_SR_SUMMARY,
            )
            if sr_id is not None:
                service_request_id = sr_id
                callback_request_created = created_new
                action_taken = "rm_callback_requested"
                summary = (
                    _CALLBACK_CREATED_SUMMARY if created_new else _CALLBACK_REUSED_SUMMARY
                )

        data = _build_safe_data(
            mapping,
            service_request_id=service_request_id,
            callback_request_created=callback_request_created,
        )
        return ToolRunResult(
            data=data,
            customer_safe_summary=summary,
            action_taken=action_taken,
            escalation_required=False,
            service_request_id=service_request_id,
        )


def _select_mapping(mappings: list[RmMappingDocument]) -> RmMappingDocument | None:
    if not mappings:
        return None
    return sorted(
        mappings,
        key=lambda mapping: (str(mapping.created_at), mapping.rm_mapping_id),
        reverse=True,
    )[0]


def _should_request_callback(intent: TicketIntent, *, parameters: dict[str, Any]) -> bool:
    if intent == "rm_redirection":
        return True
    return _parse_callback_requested(parameters)


def _parse_callback_requested(parameters: dict[str, Any]) -> bool:
    for key in ("request_callback", "proceed"):
        value = parameters.get(key)
        if value is True:
            return True
        if isinstance(value, str) and value.strip().lower() in {"true", "1", "yes"}:
            return True
        if value == 1:
            return True
    return False


async def _get_or_create_rm_callback_sr(
    service_request_service: ServiceRequestService,
    *,
    ticket_id: str,
    customer_safe_summary: str,
) -> tuple[str | None, bool]:
    existing = await service_request_service.get_for_ticket(ticket_id)
    if existing is not None:
        if existing.request_type == "rm_callback":
            return existing.service_request_id, False
        return None, False

    try:
        created = await service_request_service.create_for_ticket(
            ticket_id,
            "rm_callback",
            customer_safe_summary=customer_safe_summary,
        )
    except ServiceRequestValidationError:
        return None, False

    return created.service_request_id, True


def _build_safe_data(
    mapping: RmMappingDocument,
    *,
    service_request_id: str | None = None,
    callback_request_created: bool | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "rm_mapping_id": mapping.rm_mapping_id,
        "rm_name": mapping.rm_name,
        "branch": mapping.branch,
        "callback_available": mapping.callback_available,
        "rm_email_masked": mask_email(mapping.rm_email),
        "rm_phone_masked": mask_mobile(mapping.rm_phone),
    }
    if service_request_id is not None:
        data["service_request_id"] = service_request_id
    if callback_request_created is not None:
        data["callback_request_created"] = callback_request_created
    return data
