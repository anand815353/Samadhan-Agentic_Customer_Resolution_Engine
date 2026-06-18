"""LoanStatusTool — fetch loan application and loan status from seeded demo data."""

from __future__ import annotations

from typing import Any, Literal

from app.common.masking import mask_loan_account
from app.customers.repositories import CustomerRepository
from app.lending.models import LoanApplicationDocument, LoanDocument
from app.lending.repositories import LoanApplicationRepository, LoanRepository
from app.tickets.constants import TicketIntent
from app.tools.audit_hook import ToolAuditHook
from app.tools.base import BaseMockTool
from app.tools.constants import ToolName
from app.tools.exceptions import ToolExecutionError, ToolValidationError
from app.tools.schemas import ToolInput, ToolRunResult

SUPPORTED_INTENTS: frozenset[TicketIntent] = frozenset(
    {
        "loan_application_status",
        "noc_closure_certificate",
        "bureau_reporting_issue",
        "topup_offer",
        "kyc_document_issue",
        "charges_refund_reversal",
    }
)

RecordKind = Literal["application", "loan"]


class LoanStatusTool(BaseMockTool):
    """Mock tool to read loan application and loan status for a customer."""

    def __init__(
        self,
        customer_repository: CustomerRepository,
        loan_application_repository: LoanApplicationRepository,
        loan_repository: LoanRepository,
        audit_hook: ToolAuditHook | None = None,
    ) -> None:
        super().__init__(audit_hook=audit_hook)
        self._customer_repository = customer_repository
        self._loan_application_repository = loan_application_repository
        self._loan_repository = loan_repository

    @property
    def tool_name(self) -> ToolName:
        return "LoanStatusTool"

    def validate_input(self, tool_input: ToolInput) -> None:
        if tool_input.intent not in SUPPORTED_INTENTS:
            raise ToolValidationError(
                f"LoanStatusTool does not support intent: {tool_input.intent}"
            )

    async def _run(self, tool_input: ToolInput) -> ToolRunResult:
        customer = await self._customer_repository.find_by_id(tool_input.customer_id)
        if customer is None:
            raise ToolExecutionError(
                "Customer record was not found for this demo profile.",
                code="not_found",
                retryable=False,
            )

        applications = await self._loan_application_repository.find_by_customer(
            tool_input.customer_id
        )
        loans = await self._loan_repository.find_by_customer(tool_input.customer_id)

        selected = _select_record(
            intent=tool_input.intent,
            parameters=tool_input.parameters,
            applications=applications,
            loans=loans,
        )
        if selected is None:
            return ToolRunResult(
                data={},
                customer_safe_summary=(
                    "I could not find an active loan application or loan record "
                    "for this demo customer."
                ),
                action_taken="loan_status_lookup_no_record",
                escalation_required=False,
            )

        kind, record = selected
        if kind == "application":
            return _application_result(record)
        return _loan_result(record, intent=tool_input.intent)


def _select_record(
    *,
    intent: TicketIntent,
    parameters: dict[str, Any],
    applications: list[LoanApplicationDocument],
    loans: list[LoanDocument],
) -> tuple[RecordKind, LoanApplicationDocument | LoanDocument] | None:
    loan_id = parameters.get("loan_id")
    if isinstance(loan_id, str):
        matched_loan = next((loan for loan in loans if loan.loan_id == loan_id), None)
        if matched_loan is not None:
            return ("loan", matched_loan)

    application_id = parameters.get("application_id")
    if isinstance(application_id, str):
        matched_application = next(
            (app for app in applications if app.application_id == application_id),
            None,
        )
        if matched_application is not None:
            return ("application", matched_application)

    if intent == "loan_application_status":
        return _select_for_loan_application_status(applications, loans)
    if intent in {"noc_closure_certificate", "bureau_reporting_issue"}:
        return _select_for_closure_context(applications, loans)
    if intent == "topup_offer":
        return _select_for_topup_offer(applications, loans)
    return None


def _select_for_loan_application_status(
    applications: list[LoanApplicationDocument],
    loans: list[LoanDocument],
) -> tuple[RecordKind, LoanApplicationDocument | LoanDocument] | None:
    active_loans = [loan for loan in loans if loan.status == "active"]
    if active_loans:
        return ("loan", active_loans[0])

    pending_applications = [app for app in applications if app.status == "pending"]
    if pending_applications:
        return ("application", pending_applications[0])

    if applications:
        return ("application", applications[0])
    if loans:
        return ("loan", loans[0])
    return None


def _select_for_closure_context(
    applications: list[LoanApplicationDocument],
    loans: list[LoanDocument],
) -> tuple[RecordKind, LoanApplicationDocument | LoanDocument] | None:
    closed_loans = [loan for loan in loans if loan.status == "closed"]
    if closed_loans:
        return ("loan", closed_loans[0])
    if applications:
        return ("application", applications[0])
    if loans:
        return ("loan", loans[0])
    return None


def _select_for_topup_offer(
    applications: list[LoanApplicationDocument],
    loans: list[LoanDocument],
) -> tuple[RecordKind, LoanApplicationDocument | LoanDocument] | None:
    active_loans = [loan for loan in loans if loan.status == "active"]
    if active_loans:
        return ("loan", active_loans[0])
    if loans:
        return ("loan", loans[0])
    if applications:
        return ("application", applications[0])
    return None


def _application_result(application: LoanApplicationDocument) -> ToolRunResult:
    data: dict[str, Any] = {
        "record_type": "application",
        "application_id": application.application_id,
        "status": application.status,
        "current_stage": application.current_stage,
        "product_type": application.product_type,
    }
    summary = _application_summary(application)
    return ToolRunResult(
        data=data,
        customer_safe_summary=summary,
        action_taken="loan_application_status_checked",
        escalation_required=False,
    )


def _loan_result(loan: LoanDocument, *, intent: TicketIntent) -> ToolRunResult:
    data: dict[str, Any] = {
        "record_type": "loan",
        "loan_id": loan.loan_id,
        "status": loan.status,
        "product_type": loan.product_type,
        "loan_account_masked": mask_loan_account(loan.loan_account_number),
    }
    if loan.closure_date is not None:
        data["closure_date"] = loan.closure_date
    if loan.noc_status is not None:
        data["noc_status"] = loan.noc_status

    summary = _loan_summary(loan, intent=intent)
    return ToolRunResult(
        data=data,
        customer_safe_summary=summary,
        action_taken="loan_status_checked",
        escalation_required=False,
    )


def _application_summary(application: LoanApplicationDocument) -> str:
    if application.status == "pending" and application.current_stage == "kyc_review":
        return (
            "Your loan application is currently pending because document "
            "verification is not complete."
        )
    if application.status == "rejected":
        return "Your loan application shows as rejected in our demo records."
    if application.status == "pending":
        return "Your loan application is currently pending in our demo records."
    if application.status == "approved":
        return "Your loan application is approved in our demo records."
    return "Your loan application status was retrieved from our demo records."


def _loan_summary(loan: LoanDocument, *, intent: TicketIntent) -> str:
    if loan.status == "closed" and intent == "bureau_reporting_issue":
        return (
            "Your loan is closed in our demo records. This context can be used "
            "for bureau reporting review."
        )
    if loan.status == "closed" and loan.noc_status == "pending":
        return (
            "Your loan is marked closed in our demo records, and the NOC status is pending."
        )
    if loan.status == "closed":
        return "Your loan is marked closed in our demo records."
    if loan.status == "active":
        return "Your loan is active in our demo records."
    return "Your loan status was retrieved from our demo records."
