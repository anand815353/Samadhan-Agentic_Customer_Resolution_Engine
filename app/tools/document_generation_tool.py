"""DocumentGenerationTool — create mock document service requests and record safe paths."""

from __future__ import annotations

from typing import Any

from app.common.masking import mask_loan_account
from app.customers.repositories import CustomerRepository
from app.lending.models import LoanDocument
from app.lending.repositories import LoanRepository
from app.repayments.models import RepaymentScheduleDocument
from app.repayments.repositories import RepaymentScheduleRepository
from app.service_requests.constants import INTENT_TO_REQUEST_TYPE, RequestType
from app.service_requests.document_paths import build_mock_document_path
from app.service_requests.exceptions import ServiceRequestValidationError
from app.service_requests.services import ServiceRequestService
from app.tickets.constants import TicketIntent
from app.tools.audit_hook import ToolAuditHook
from app.tools.base import BaseMockTool
from app.tools.constants import ToolName
from app.tools.exceptions import ToolExecutionError, ToolValidationError
from app.tools.schemas import ToolInput, ToolRunResult

SUPPORTED_INTENTS: frozenset[TicketIntent] = frozenset(
    {
        "loan_statement_request",
        "noc_closure_certificate",
        "bureau_reporting_issue",
    }
)

_INTENT_TO_DOCUMENT_TYPE: dict[TicketIntent, str] = {
    "loan_statement_request": "loan_statement",
    "noc_closure_certificate": "noc",
    "bureau_reporting_issue": "closure_letter",
}

_ALLOWED_DOCUMENT_TYPES_BY_INTENT: dict[TicketIntent, frozenset[str]] = {
    "loan_statement_request": frozenset({"loan_statement"}),
    "noc_closure_certificate": frozenset({"noc", "noc_request"}),
    "bureau_reporting_issue": frozenset({"closure_letter", "bureau_closure_letter"}),
}

_MISSING_CONTEXT_SUMMARY = (
    "I could not find the required loan context to create this mock document request."
)
_LOAN_STATEMENT_SUMMARY = (
    "Your mock loan statement request has been created and the document path "
    "has been recorded for the demo."
)
_NOC_SUMMARY = "A mock NOC service request has been created for your closed loan."
_CLOSURE_LETTER_SUMMARY = (
    "A mock closure letter request has been created. This can be used as demo proof "
    "while the bureau reporting issue is reviewed."
)


class DocumentGenerationTool(BaseMockTool):
    """Mock tool to create document service requests and record demo document paths."""

    def __init__(
        self,
        customer_repository: CustomerRepository,
        loan_repository: LoanRepository,
        repayment_schedule_repository: RepaymentScheduleRepository,
        service_request_service: ServiceRequestService | None = None,
        audit_hook: ToolAuditHook | None = None,
    ) -> None:
        super().__init__(audit_hook=audit_hook)
        self._customer_repository = customer_repository
        self._loan_repository = loan_repository
        self._repayment_schedule_repository = repayment_schedule_repository
        self._service_request_service = service_request_service

    @property
    def tool_name(self) -> ToolName:
        return "DocumentGenerationTool"

    def validate_input(self, tool_input: ToolInput) -> None:
        if tool_input.intent not in SUPPORTED_INTENTS:
            raise ToolValidationError(
                f"DocumentGenerationTool does not support intent: {tool_input.intent}"
            )

        document_type = tool_input.parameters.get("document_type")
        if document_type is None:
            return
        if not isinstance(document_type, str) or not document_type.strip():
            raise ToolValidationError("document_type parameter must be a non-empty string")
        allowed = _ALLOWED_DOCUMENT_TYPES_BY_INTENT.get(tool_input.intent)
        if allowed is not None and document_type.strip() not in allowed:
            raise ToolValidationError(
                f"document_type '{document_type}' is not supported for intent {tool_input.intent}"
            )

    async def _run(self, tool_input: ToolInput) -> ToolRunResult:
        customer = await self._customer_repository.find_by_id(tool_input.customer_id)
        if customer is None:
            raise ToolExecutionError(
                "Customer record was not found for this demo profile.",
                code="not_found",
                retryable=False,
            )

        document_type = _resolve_document_type(tool_input.intent, tool_input.parameters)
        request_type = INTENT_TO_REQUEST_TYPE[tool_input.intent]

        loans = await self._loan_repository.find_by_customer(tool_input.customer_id)
        loan = _resolve_loan(
            tool_input.intent,
            loans,
            parameters=tool_input.parameters,
        )
        if loan is None or loan.loan_id is None:
            return _missing_context_result()

        schedule_count = 0
        if tool_input.intent == "loan_statement_request":
            schedules = await self._repayment_schedule_repository.find_by_loan(loan.loan_id)
            schedule_count = len(schedules)
            if schedule_count == 0:
                return _missing_context_result()

        if self._service_request_service is None:
            return _missing_context_result()

        summary = _summary_for_intent(tool_input.intent)
        service_request_id, created_new = await _get_or_create_document_sr(
            self._service_request_service,
            ticket_id=tool_input.ticket_id,
            request_type=request_type,
            loan_id=loan.loan_id,
            customer_safe_summary=summary,
        )
        if service_request_id is None:
            return _missing_context_result()

        document_path = build_mock_document_path(
            tool_input.customer_id,
            document_type,
            service_request_id,
        )
        sr_document = await self._service_request_service.record_mock_document_path(
            service_request_id,
            document_path,
        )

        action_taken = _resolve_action_taken(
            tool_input.intent,
            created_new=created_new,
        )
        data = _build_safe_data(
            document_type=document_type,
            request_type=request_type,
            document_path=document_path,
            status=sr_document.status,
            loan=loan,
            schedule_entry_count=schedule_count if schedule_count > 0 else None,
        )

        return ToolRunResult(
            data=data,
            customer_safe_summary=summary,
            action_taken=action_taken,
            escalation_required=False,
            service_request_id=service_request_id,
        )


def _resolve_document_type(intent: TicketIntent, parameters: dict[str, Any]) -> str:
    override = parameters.get("document_type")
    if isinstance(override, str) and override.strip():
        normalized = override.strip()
        if normalized == "noc_request":
            return "noc"
        if normalized == "bureau_closure_letter":
            return "closure_letter"
        return normalized
    return _INTENT_TO_DOCUMENT_TYPE[intent]


def _resolve_loan(
    intent: TicketIntent,
    loans: list[LoanDocument],
    *,
    parameters: dict[str, Any],
) -> LoanDocument | None:
    loan_id = parameters.get("loan_id")
    if isinstance(loan_id, str) and loan_id.strip():
        return next((loan for loan in loans if loan.loan_id == loan_id.strip()), None)

    if intent == "loan_statement_request":
        active_loans = [loan for loan in loans if loan.status == "active"]
        if active_loans:
            return active_loans[0]
        return loans[0] if loans else None

    closed_loans = [loan for loan in loans if loan.status == "closed"]
    if closed_loans:
        return closed_loans[0]
    return loans[0] if loans else None


def _summary_for_intent(intent: TicketIntent) -> str:
    if intent == "loan_statement_request":
        return _LOAN_STATEMENT_SUMMARY
    if intent == "noc_closure_certificate":
        return _NOC_SUMMARY
    return _CLOSURE_LETTER_SUMMARY


def _resolve_action_taken(intent: TicketIntent, *, created_new: bool) -> str:
    if intent == "loan_statement_request":
        return "loan_statement_requested" if created_new else "loan_statement_generated"
    if intent == "noc_closure_certificate":
        return "noc_request_created" if created_new else "noc_generated"
    return "closure_letter_requested" if created_new else "closure_letter_generated"


def _missing_context_result() -> ToolRunResult:
    return ToolRunResult(
        data={},
        customer_safe_summary=_MISSING_CONTEXT_SUMMARY,
        action_taken="document_generation_context_missing",
        escalation_required=False,
    )


def _build_safe_data(
    *,
    document_type: str,
    request_type: RequestType,
    document_path: str,
    status: str,
    loan: LoanDocument,
    schedule_entry_count: int | None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "document_type": document_type,
        "request_type": request_type,
        "document_path": document_path,
        "status": status,
    }
    if loan.loan_id is not None:
        data["loan_id"] = loan.loan_id
    if loan.loan_account_number:
        data["loan_account_masked"] = mask_loan_account(loan.loan_account_number)
    if schedule_entry_count is not None:
        data["schedule_entry_count"] = schedule_entry_count
    return data


async def _get_or_create_document_sr(
    service_request_service: ServiceRequestService,
    *,
    ticket_id: str,
    request_type: RequestType,
    loan_id: str,
    customer_safe_summary: str,
) -> tuple[str | None, bool]:
    existing = await service_request_service.get_for_ticket(ticket_id)
    if existing is not None:
        if existing.request_type == request_type:
            return existing.service_request_id, False
        return None, False

    try:
        created = await service_request_service.create_for_ticket(
            ticket_id,
            request_type,
            loan_id=loan_id,
            customer_safe_summary=customer_safe_summary,
        )
    except ServiceRequestValidationError:
        return None, False

    return created.service_request_id, True
