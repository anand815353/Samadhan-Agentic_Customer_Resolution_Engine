"""RejectionReasonTool — return customer-safe rejection explanations from seeded demo data."""

from __future__ import annotations

from typing import Any

from app.customers.repositories import CustomerRepository
from app.lending.models import LoanApplicationDocument
from app.lending.repositories import LoanApplicationRepository
from app.tickets.constants import TicketIntent
from app.tools.audit_hook import ToolAuditHook
from app.tools.base import BaseMockTool
from app.tools.constants import ToolName
from app.tools.exceptions import ToolExecutionError, ToolValidationError
from app.tools.schemas import ToolInput, ToolRunResult

SUPPORTED_INTENTS: frozenset[TicketIntent] = frozenset({"rejection_reason"})

_FORBIDDEN_SUMMARY_TOKENS: frozenset[str] = frozenset(
    {
        "risk score",
        "underwriting",
        "cutoff",
        "probability",
        "internal rejection",
        "bureau score",
    }
)

_NO_RECORD_SUMMARY = (
    "I could not find a rejected loan application for this demo customer."
)
_FALLBACK_SAFE_SUMMARY = (
    "Your loan application shows as rejected in our demo records, "
    "but an approved customer-safe explanation is not available right now."
)
_DISPUTE_SUMMARY_SUFFIX = (
    " Since you are disputing the decision, this may need human review."
)


class RejectionReasonTool(BaseMockTool):
    """Mock tool to share approved customer-safe rejection reasons only."""

    def __init__(
        self,
        customer_repository: CustomerRepository,
        loan_application_repository: LoanApplicationRepository,
        audit_hook: ToolAuditHook | None = None,
    ) -> None:
        super().__init__(audit_hook=audit_hook)
        self._customer_repository = customer_repository
        self._loan_application_repository = loan_application_repository

    @property
    def tool_name(self) -> ToolName:
        return "RejectionReasonTool"

    def validate_input(self, tool_input: ToolInput) -> None:
        if tool_input.intent not in SUPPORTED_INTENTS:
            raise ToolValidationError(
                f"RejectionReasonTool does not support intent: {tool_input.intent}"
            )

    async def _run(self, tool_input: ToolInput) -> ToolRunResult:
        customer = await self._customer_repository.find_by_id(tool_input.customer_id)
        if customer is None:
            raise ToolExecutionError(
                "Customer record was not found for this demo profile.",
                code="not_found",
                retryable=False,
            )

        application = await _select_rejected_application(
            tool_input,
            loan_application_repository=self._loan_application_repository,
        )
        if application is None:
            return ToolRunResult(
                data={},
                customer_safe_summary=_NO_RECORD_SUMMARY,
                action_taken="rejection_reason_lookup_no_record",
                escalation_required=False,
            )

        dispute_escalation = _parse_dispute_escalation(tool_input.parameters)
        return _rejection_result(application, dispute_escalation=dispute_escalation)


async def _select_rejected_application(
    tool_input: ToolInput,
    *,
    loan_application_repository: LoanApplicationRepository,
) -> LoanApplicationDocument | None:
    application_id = tool_input.parameters.get("application_id")
    if isinstance(application_id, str) and application_id.strip():
        application = await loan_application_repository.find_by_id(application_id.strip())
        if application is None:
            return None
        if application.customer_id != tool_input.customer_id:
            return None
        if application.status != "rejected":
            return None
        return application

    applications = await loan_application_repository.find_by_customer(tool_input.customer_id)
    for application in applications:
        if application.status == "rejected":
            return application
    return None


def _parse_dispute_escalation(parameters: dict[str, Any]) -> bool:
    value = parameters.get("dispute_escalation")
    return value is True


def _rejection_result(
    application: LoanApplicationDocument,
    *,
    dispute_escalation: bool,
) -> ToolRunResult:
    safe_reason = _resolve_safe_summary(application)
    customer_safe_summary = safe_reason
    if dispute_escalation:
        customer_safe_summary = (
            "I have shared the approved reason available in our demo records."
            + _DISPUTE_SUMMARY_SUFFIX
        )

    data: dict[str, Any] = {
        "record_type": "rejection_reason",
        "application_id": application.application_id,
        "status": application.status,
    }
    if application.rejection_code is not None:
        data["rejection_code"] = application.rejection_code

    return ToolRunResult(
        data=data,
        customer_safe_summary=customer_safe_summary,
        action_taken="customer_safe_rejection_reason_shared",
        escalation_required=dispute_escalation,
    )


def _resolve_safe_summary(application: LoanApplicationDocument) -> str:
    reason = (application.customer_safe_rejection_reason or "").strip()
    if not reason:
        return _FALLBACK_SAFE_SUMMARY

    lowered = reason.lower()
    if any(token in lowered for token in _FORBIDDEN_SUMMARY_TOKENS):
        return _FALLBACK_SAFE_SUMMARY
    return reason
