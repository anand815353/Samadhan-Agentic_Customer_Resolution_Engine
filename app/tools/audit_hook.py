"""Audit hook for mock tool execution events."""

from __future__ import annotations

from typing import Any

from app.audit.constants import AuditCreatedBy
from app.audit.exceptions import AuditValidationError
from app.audit.services import AuditService
from app.common.masking import mask_loan_account, mask_sensitive_data
from app.tickets.constants import TransitionActor
from app.tools.schemas import ToolError, ToolInput

_ACTOR_TO_CREATED_BY: dict[TransitionActor, AuditCreatedBy] = {
    "system": "system",
    "customer": "customer",
    "support_agent": "support_agent",
    "admin": "admin",
}


class ToolAuditHook:
    """Records masked tool execution events via AuditService."""

    def __init__(self, audit_service: AuditService | None = None) -> None:
        self._audit_service = audit_service

    @property
    def enabled(self) -> bool:
        return self._audit_service is not None

    async def record_execution(
        self,
        *,
        tool_input: ToolInput,
        tool_name: str,
        success: bool,
        data: dict[str, Any],
        customer_safe_summary: str,
        action_taken: str,
        escalation_required: bool,
        service_request_id: str | None,
        error: ToolError | None,
        validate_links: bool,
    ) -> str | None:
        if self._audit_service is None:
            return None

        tool_input_masked = _audit_safe_tool_input(tool_input.model_dump())
        tool_output_summary: dict[str, Any] = {
            "success": success,
            "data": _audit_safe_tool_data(data),
        }
        if error is not None:
            tool_output_summary["error"] = {
                "code": error.code,
                "message": error.message,
                "retryable": error.retryable,
            }
            if error.details is not None:
                tool_output_summary["error"]["details"] = mask_sensitive_data(error.details)

        try:
            audit_event = await self._audit_service.record_tool_called(
                ticket_id=tool_input.ticket_id,
                customer_id=tool_input.customer_id,
                tool_name=tool_name,
                tool_input_masked=tool_input_masked,
                tool_output_summary=tool_output_summary,
                action_taken=action_taken,
                customer_safe_summary=customer_safe_summary,
                escalation_required=escalation_required,
                service_request_id=service_request_id,
                intent=tool_input.intent,
                workflow_id=tool_input.request_id,
                created_by=_ACTOR_TO_CREATED_BY[tool_input.actor],
                validate_links=validate_links,
            )
        except AuditValidationError:
            return None

        return audit_event.audit_id


def _audit_safe_tool_input(payload: dict[str, Any]) -> dict[str, Any]:
    """Mask tool input for audit persistence without altering runtime tool input."""
    masked = mask_sensitive_data(payload)
    if not isinstance(masked, dict):
        return masked
    safe = dict(masked)
    parameters = safe.get("parameters")
    if isinstance(parameters, dict):
        params = dict(parameters)
        loan_id = params.get("loan_id")
        if isinstance(loan_id, str):
            params["loan_id"] = mask_loan_account(loan_id)
        transaction_id = params.get("transaction_id")
        if isinstance(transaction_id, str):
            params["transaction_id"] = mask_loan_account(transaction_id)
        safe["parameters"] = params
    return safe


def _audit_safe_tool_data(data: dict[str, Any]) -> dict[str, Any]:
    """Mask tool data for audit persistence without altering customer-facing output."""
    masked = mask_sensitive_data(data)
    if not isinstance(masked, dict):
        return masked
    safe = dict(masked)
    loan_id = safe.get("loan_id")
    if isinstance(loan_id, str):
        safe["loan_id"] = mask_loan_account(loan_id)
    transaction_id = safe.get("transaction_id")
    if isinstance(transaction_id, str):
        safe["transaction_id"] = mask_loan_account(transaction_id)
    return safe
