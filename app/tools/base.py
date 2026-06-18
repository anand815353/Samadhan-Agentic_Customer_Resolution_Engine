"""Base mock tool interface and execution wrapper."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from app.common.masking import mask_sensitive_data
from app.common.service import BaseService
from app.tools.audit_hook import ToolAuditHook
from app.tools.constants import FORBIDDEN_ACTION_TOKENS, ToolName
from app.tools.exceptions import ToolExecutionError, ToolValidationError
from app.tools.schemas import ToolError, ToolInput, ToolOutput, ToolRunResult


class BaseMockTool(BaseService):
    """Abstract base for all Samadhan mock internal tools."""

    def __init__(self, audit_hook: ToolAuditHook | None = None) -> None:
        self._audit_hook = audit_hook or ToolAuditHook()

    @property
    @abstractmethod
    def tool_name(self) -> ToolName: ...

    async def execute(self, tool_input: ToolInput, *, validate_links: bool = False) -> ToolOutput:
        try:
            self.validate_input(tool_input)
            result = await self._run(tool_input)
            output = self.build_success_output(tool_input, result)
            audit_id = await self._audit_hook.record_execution(
                tool_input=tool_input,
                tool_name=self.tool_name,
                success=True,
                data=output.data,
                customer_safe_summary=output.customer_safe_summary,
                action_taken=output.action_taken,
                escalation_required=output.escalation_required,
                service_request_id=output.service_request_id,
                error=None,
                validate_links=validate_links,
            )
            if audit_id is None and self._audit_hook.enabled:
                return self.build_failure_output(
                    error=ToolError(
                        code="audit_failed",
                        message="Tool result could not be audited safely.",
                        retryable=False,
                    ),
                    action_taken="audit_failed",
                    customer_safe_summary=output.customer_safe_summary,
                    data=output.data,
                    escalation_required=output.escalation_required,
                    service_request_id=output.service_request_id,
                )
            return output.model_copy(update={"audit_id": audit_id})
        except ToolValidationError as exc:
            return await self._handle_failure(
                tool_input,
                error=ToolError(
                    code="validation_failed",
                    message=exc.message,
                    retryable=False,
                ),
                action_taken="validation_failed",
                customer_safe_summary="The tool request could not be validated.",
                validate_links=validate_links,
            )
        except ToolExecutionError as exc:
            return await self._handle_failure(
                tool_input,
                error=ToolError(
                    code=exc.code,
                    message=exc.message,
                    retryable=exc.retryable,
                    details=mask_sensitive_data(exc.details) if exc.details else None,
                ),
                action_taken="execution_failed",
                customer_safe_summary=exc.message,
                validate_links=validate_links,
            )
        except Exception:
            return await self._handle_failure(
                tool_input,
                error=ToolError(
                    code="unexpected_error",
                    message="An unexpected error occurred while running the tool.",
                    retryable=True,
                ),
                action_taken="unexpected_error",
                customer_safe_summary="We could not complete this request right now. Please try again later.",
                validate_links=validate_links,
            )

    @abstractmethod
    async def _run(self, tool_input: ToolInput) -> ToolRunResult: ...

    def validate_input(self, tool_input: ToolInput) -> None:
        """Optional subclass hook for business validation beyond Pydantic."""

    def build_success_output(self, tool_input: ToolInput, result: ToolRunResult) -> ToolOutput:
        action_taken = result.action_taken.strip()
        normalized = action_taken.lower().replace("-", "_")
        if any(token in normalized for token in FORBIDDEN_ACTION_TOKENS):
            raise ToolValidationError(
                f"action_taken must not claim real financial actions: {action_taken}"
            )

        return ToolOutput(
            success=True,
            tool_name=self.tool_name,
            data=mask_sensitive_data(result.data),
            customer_safe_summary=result.customer_safe_summary,
            action_taken=action_taken,
            escalation_required=result.escalation_required,
            service_request_id=result.service_request_id,
            audit_id=None,
            error=None,
        )

    def build_failure_output(
        self,
        *,
        error: ToolError,
        action_taken: str,
        customer_safe_summary: str,
        data: dict[str, Any] | None = None,
        escalation_required: bool = False,
        service_request_id: str | None = None,
        audit_id: str | None = None,
    ) -> ToolOutput:
        return ToolOutput(
            success=False,
            tool_name=self.tool_name,
            data=mask_sensitive_data(data or {}),
            customer_safe_summary=customer_safe_summary,
            action_taken=action_taken,
            escalation_required=escalation_required,
            service_request_id=service_request_id,
            audit_id=audit_id,
            error=error,
        )

    async def _handle_failure(
        self,
        tool_input: ToolInput,
        *,
        error: ToolError,
        action_taken: str,
        customer_safe_summary: str,
        validate_links: bool,
    ) -> ToolOutput:
        output = self.build_failure_output(
            error=error,
            action_taken=action_taken,
            customer_safe_summary=customer_safe_summary,
        )
        audit_id = await self._audit_hook.record_execution(
            tool_input=tool_input,
            tool_name=self.tool_name,
            success=False,
            data=output.data,
            customer_safe_summary=output.customer_safe_summary,
            action_taken=output.action_taken,
            escalation_required=output.escalation_required,
            service_request_id=output.service_request_id,
            error=error,
            validate_links=validate_links,
        )
        if audit_id is None and self._audit_hook.enabled and error.code != "audit_failed":
            return self.build_failure_output(
                error=ToolError(
                    code="audit_failed",
                    message="Tool result could not be audited safely.",
                    retryable=False,
                ),
                action_taken="audit_failed",
                customer_safe_summary=customer_safe_summary,
            )
        return output.model_copy(update={"audit_id": audit_id})
