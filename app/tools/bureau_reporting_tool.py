"""BureauReportingTool — check mock bureau reporting logs and escalate mismatches."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.bureau.models import BureauReportingLogDocument
from app.bureau.repositories import BureauReportingLogRepository
from app.common.masking import mask_loan_account
from app.customers.repositories import CustomerRepository
from app.lending.models import LoanDocument
from app.lending.repositories import LoanRepository
from app.service_requests.constants import INTENT_TO_REQUEST_TYPE
from app.service_requests.exceptions import ServiceRequestValidationError
from app.service_requests.services import ServiceRequestService
from app.tickets.constants import TicketIntent
from app.tools.audit_hook import ToolAuditHook
from app.tools.base import BaseMockTool
from app.tools.constants import ToolName
from app.tools.exceptions import ToolExecutionError, ToolValidationError
from app.tools.schemas import ToolInput, ToolRunResult

SUPPORTED_INTENTS: frozenset[TicketIntent] = frozenset({"bureau_reporting_issue"})

_NO_RECORD_SUMMARY = (
    "I could not find a bureau reporting record for this demo customer and loan. "
    "This may need review."
)
_LAG_SUMMARY = (
    "Your loan is marked closed in our demo records. The latest bureau reporting batch "
    "has been submitted, and credit bureau updates can take around 30–45 days."
)
_MISMATCH_SUMMARY = (
    "Your loan is marked closed in our demo records, but the latest bureau reporting "
    "record does not show the expected closed status. Because this can affect credit "
    "reporting, this needs human review."
)
_STATUS_CHECKED_SUMMARY = (
    "Your loan bureau reporting status was checked against our demo records."
)
_CLOSURE_LETTER_SR_SUMMARY = (
    "A mock closure letter request has been created for this bureau reporting issue. "
    "This does not mean a real bureau update has been completed."
)
_ACTIVE_LOAN_MISMATCH_SUMMARY = (
    "The selected loan is not marked closed in our demo records, but you raised a "
    "bureau reporting issue. This needs human review."
)


@dataclass(frozen=True)
class _BureauAssessment:
    action_taken: str
    escalation_required: bool
    customer_safe_summary: str


class BureauReportingTool(BaseMockTool):
    """Mock tool to read bureau reporting logs and assess closure reporting status."""

    def __init__(
        self,
        customer_repository: CustomerRepository,
        loan_repository: LoanRepository,
        bureau_reporting_log_repository: BureauReportingLogRepository,
        service_request_service: ServiceRequestService | None = None,
        audit_hook: ToolAuditHook | None = None,
    ) -> None:
        super().__init__(audit_hook=audit_hook)
        self._customer_repository = customer_repository
        self._loan_repository = loan_repository
        self._bureau_reporting_log_repository = bureau_reporting_log_repository
        self._service_request_service = service_request_service

    @property
    def tool_name(self) -> ToolName:
        return "BureauReportingTool"

    def validate_input(self, tool_input: ToolInput) -> None:
        if tool_input.intent not in SUPPORTED_INTENTS:
            raise ToolValidationError(
                f"BureauReportingTool does not support intent: {tool_input.intent}"
            )

    async def _run(self, tool_input: ToolInput) -> ToolRunResult:
        customer = await self._customer_repository.find_by_id(tool_input.customer_id)
        if customer is None:
            raise ToolExecutionError(
                "Customer record was not found for this demo profile.",
                code="not_found",
                retryable=False,
            )

        loans = await self._loan_repository.find_by_customer(tool_input.customer_id)
        loan = _resolve_loan(loans, parameters=tool_input.parameters)
        if loan is None or loan.loan_id is None:
            return _no_record_result()

        if loan.status != "closed":
            return ToolRunResult(
                data=_build_safe_data(
                    loan=loan,
                    latest_log=None,
                    prior_logs=[],
                ),
                customer_safe_summary=_ACTIVE_LOAN_MISMATCH_SUMMARY,
                action_taken="bureau_reporting_mismatch_detected",
                escalation_required=True,
            )

        logs = await self._bureau_reporting_log_repository.find_by_loan(loan.loan_id)
        if not logs:
            return _no_record_result(loan=loan)

        latest_log = logs[0]
        prior_logs = logs[1:]
        assessment = _assess_bureau_reporting(loan, latest_log)

        if _force_escalation(tool_input.parameters):
            assessment = _BureauAssessment(
                action_taken=assessment.action_taken,
                escalation_required=True,
                customer_safe_summary=assessment.customer_safe_summary,
            )

        service_request_id: str | None = None
        action_taken = assessment.action_taken
        summary = assessment.customer_safe_summary

        if (
            assessment.escalation_required
            and loan.status == "closed"
            and self._service_request_service is not None
            and _should_request_closure_letter(tool_input.parameters, escalate=True)
        ):
            sr_id = await _maybe_create_bureau_closure_letter_sr(
                self._service_request_service,
                ticket_id=tool_input.ticket_id,
                loan_id=loan.loan_id,
                customer_safe_summary=_CLOSURE_LETTER_SR_SUMMARY,
            )
            if sr_id is not None:
                service_request_id = sr_id
                action_taken = "bureau_closure_letter_requested"
                summary = _CLOSURE_LETTER_SR_SUMMARY

        data = _build_safe_data(
            loan=loan,
            latest_log=latest_log,
            prior_logs=prior_logs,
        )

        return ToolRunResult(
            data=data,
            customer_safe_summary=summary,
            action_taken=action_taken,
            escalation_required=assessment.escalation_required,
            service_request_id=service_request_id,
        )


def _resolve_loan(
    loans: list[LoanDocument],
    *,
    parameters: dict[str, Any],
) -> LoanDocument | None:
    loan_id = parameters.get("loan_id")
    if isinstance(loan_id, str) and loan_id.strip():
        return next((loan for loan in loans if loan.loan_id == loan_id.strip()), None)

    closed_loans = [loan for loan in loans if loan.status == "closed"]
    if closed_loans:
        return closed_loans[0]
    return loans[0] if loans else None


def _assess_bureau_reporting(
    loan: LoanDocument,
    latest_log: BureauReportingLogDocument,
) -> _BureauAssessment:
    if loan.status != "closed":
        return _BureauAssessment(
            action_taken="bureau_reporting_mismatch_detected",
            escalation_required=True,
            customer_safe_summary=_ACTIVE_LOAN_MISMATCH_SUMMARY,
        )

    status_mismatch = latest_log.internal_loan_status != latest_log.reported_status
    active_on_bureau = latest_log.reported_status == "active"
    batch_failed = (
        latest_log.batch_status == "failed" and loan.bureau_status == "pending_update"
    )

    if status_mismatch or active_on_bureau or batch_failed:
        return _BureauAssessment(
            action_taken="bureau_reporting_mismatch_detected",
            escalation_required=True,
            customer_safe_summary=_MISMATCH_SUMMARY,
        )

    if latest_log.batch_status == "submitted" and latest_log.reported_status == "closed":
        return _BureauAssessment(
            action_taken="bureau_reporting_lag_explained",
            escalation_required=False,
            customer_safe_summary=_LAG_SUMMARY,
        )

    return _BureauAssessment(
        action_taken="bureau_reporting_status_checked",
        escalation_required=False,
        customer_safe_summary=_STATUS_CHECKED_SUMMARY,
    )


def _force_escalation(parameters: dict[str, Any]) -> bool:
    for key in ("customer_complaint", "dispute_escalation"):
        value = parameters.get(key)
        if value is True:
            return True
        if isinstance(value, str) and value.strip().lower() in {"true", "1", "yes"}:
            return True
    return False


def _should_request_closure_letter(parameters: dict[str, Any], *, escalate: bool) -> bool:
    if not escalate:
        return False
    value = parameters.get("request_closure_letter")
    if value is False:
        return False
    if isinstance(value, str) and value.strip().lower() in {"false", "0", "no"}:
        return False
    if value is True:
        return True
    if isinstance(value, str) and value.strip().lower() in {"true", "1", "yes"}:
        return True
    return True


def _prior_mismatch_found(
    loan: LoanDocument,
    prior_logs: list[BureauReportingLogDocument],
) -> bool:
    if loan.status != "closed":
        return False
    return any(log.reported_status == "active" for log in prior_logs)


def _no_record_result(*, loan: LoanDocument | None = None) -> ToolRunResult:
    data: dict[str, Any] = {}
    if loan is not None and loan.loan_id is not None:
        data["loan_id"] = loan.loan_id
        if loan.loan_account_number:
            data["loan_account_masked"] = mask_loan_account(loan.loan_account_number)
    return ToolRunResult(
        data=data,
        customer_safe_summary=_NO_RECORD_SUMMARY,
        action_taken="bureau_reporting_record_not_found",
        escalation_required=True,
    )


def _build_safe_data(
    *,
    loan: LoanDocument,
    latest_log: BureauReportingLogDocument | None,
    prior_logs: list[BureauReportingLogDocument],
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "loan_id": loan.loan_id,
        "internal_status": loan.status,
        "bureau_status": loan.bureau_status,
        "prior_mismatch_found": _prior_mismatch_found(loan, prior_logs),
    }
    if loan.closure_date is not None:
        data["closure_date"] = str(loan.closure_date)
    if loan.loan_account_number:
        data["loan_account_masked"] = mask_loan_account(loan.loan_account_number)
    if latest_log is not None:
        data.update(
            {
                "reporting_month": latest_log.reporting_month,
                "reported_status": latest_log.reported_status,
                "latest_batch_status": latest_log.batch_status,
                "expected_update_window_days": latest_log.expected_update_window_days,
                "bureau_name": latest_log.bureau_name,
            }
        )
    return data


async def _maybe_create_bureau_closure_letter_sr(
    service_request_service: ServiceRequestService,
    *,
    ticket_id: str,
    loan_id: str,
    customer_safe_summary: str,
) -> str | None:
    request_type = INTENT_TO_REQUEST_TYPE["bureau_reporting_issue"]
    existing = await service_request_service.get_for_ticket(ticket_id)
    if existing is not None:
        if existing.request_type == request_type:
            return existing.service_request_id
        return None

    try:
        created = await service_request_service.create_for_ticket(
            ticket_id,
            request_type,
            loan_id=loan_id,
            customer_safe_summary=customer_safe_summary,
        )
    except ServiceRequestValidationError:
        return None

    return created.service_request_id
