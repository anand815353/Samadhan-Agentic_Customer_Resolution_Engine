"""KYCDocumentTool — check KYC/document status and request re-upload when needed."""

from __future__ import annotations

from typing import Any

from app.customers.repositories import CustomerRepository
from app.kyc.constants import ACTION_NEEDED_KYC_STATUSES, KYC_STATUS_PRIORITY
from app.kyc.models import KycDocumentDocument
from app.kyc.repositories import KycDocumentRepository
from app.lending.repositories import LoanApplicationRepository
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
        "kyc_document_issue",
        "loan_application_status",
    }
)

_NO_RECORD_SUMMARY = "I could not find a KYC document record for this demo customer."
_PENDING_SUMMARY = (
    "Your KYC document is currently under review. "
    "We will update the status once verification is complete."
)
_APPROVED_SUMMARY = "Your KYC document is approved in our demo records."
_REJECTED_FALLBACK_SUMMARY = (
    "Your KYC document could not be verified. Please upload a clear copy of the document."
)
_SR_ACTION_STATUSES: frozenset[str] = frozenset({"reupload_required", "rejected"})


class KYCDocumentTool(BaseMockTool):
    """Mock tool to read KYC document status and create re-upload service requests."""

    def __init__(
        self,
        customer_repository: CustomerRepository,
        kyc_document_repository: KycDocumentRepository,
        loan_application_repository: LoanApplicationRepository,
        service_request_service: ServiceRequestService | None = None,
        audit_hook: ToolAuditHook | None = None,
    ) -> None:
        super().__init__(audit_hook=audit_hook)
        self._customer_repository = customer_repository
        self._kyc_document_repository = kyc_document_repository
        self._loan_application_repository = loan_application_repository
        self._service_request_service = service_request_service

    @property
    def tool_name(self) -> ToolName:
        return "KYCDocumentTool"

    def validate_input(self, tool_input: ToolInput) -> None:
        if tool_input.intent not in SUPPORTED_INTENTS:
            raise ToolValidationError(
                f"KYCDocumentTool does not support intent: {tool_input.intent}"
            )

    async def _run(self, tool_input: ToolInput) -> ToolRunResult:
        customer = await self._customer_repository.find_by_id(tool_input.customer_id)
        if customer is None:
            raise ToolExecutionError(
                "Customer record was not found for this demo profile.",
                code="not_found",
                retryable=False,
            )

        records = await self._kyc_document_repository.find_by_customer(tool_input.customer_id)
        scoped_records = records

        if tool_input.intent == "loan_application_status":
            application_id = await _resolve_pending_kyc_application_id(
                tool_input,
                loan_application_repository=self._loan_application_repository,
            )
            if application_id is None:
                return ToolRunResult(
                    data={},
                    customer_safe_summary=_NO_RECORD_SUMMARY,
                    action_taken="kyc_record_not_found",
                    escalation_required=False,
                )
            scoped_records = [
                record for record in records if record.application_id == application_id
            ]

        selected = _select_kyc_record(scoped_records, parameters=tool_input.parameters)
        if selected is None:
            return ToolRunResult(
                data={},
                customer_safe_summary=_NO_RECORD_SUMMARY,
                action_taken="kyc_record_not_found",
                escalation_required=False,
            )

        summary = _resolve_customer_safe_summary(selected)
        data = _build_safe_data(selected)
        service_request_id: str | None = None
        action_taken = "kyc_status_checked"

        if (
            tool_input.intent == "kyc_document_issue"
            and selected.status in _SR_ACTION_STATUSES
            and self._service_request_service is not None
        ):
            service_request_id = await _maybe_create_kyc_reupload_sr(
                self._service_request_service,
                ticket_id=tool_input.ticket_id,
                customer_safe_summary=summary,
            )
            if service_request_id is not None:
                action_taken = "kyc_reupload_requested"

        return ToolRunResult(
            data=data,
            customer_safe_summary=summary,
            action_taken=action_taken,
            escalation_required=False,
            service_request_id=service_request_id,
        )


async def _resolve_pending_kyc_application_id(
    tool_input: ToolInput,
    *,
    loan_application_repository: LoanApplicationRepository,
) -> str | None:
    application_id = tool_input.parameters.get("application_id")
    if isinstance(application_id, str) and application_id.strip():
        application = await loan_application_repository.find_by_id(application_id.strip())
        if application is None:
            return None
        if application.customer_id != tool_input.customer_id:
            return None
        if application.status == "pending" and application.current_stage == "kyc_review":
            return application.application_id
        return None

    applications = await loan_application_repository.find_by_customer(tool_input.customer_id)
    for application in applications:
        if application.status == "pending" and application.current_stage == "kyc_review":
            return application.application_id
    return None


def _select_kyc_record(
    records: list[KycDocumentDocument],
    *,
    parameters: dict[str, Any],
) -> KycDocumentDocument | None:
    if not records:
        return None

    application_id = parameters.get("application_id")
    document_type = parameters.get("document_type")

    if isinstance(application_id, str) and application_id.strip():
        filtered = [record for record in records if record.application_id == application_id.strip()]
        if isinstance(document_type, str) and document_type.strip():
            filtered = [
                record
                for record in filtered
                if record.document_type == document_type.strip()
            ]
        if filtered:
            return _most_recent(filtered)
        return None

    if isinstance(document_type, str) and document_type.strip():
        filtered = [
            record for record in records if record.document_type == document_type.strip()
        ]
        if filtered:
            return _select_by_status_priority(filtered)
        return None

    return _select_by_status_priority(records)


def _select_by_status_priority(records: list[KycDocumentDocument]) -> KycDocumentDocument | None:
    action_needed = [record for record in records if record.status in ACTION_NEEDED_KYC_STATUSES]
    if action_needed:
        return _most_recent_by_status_priority(action_needed)
    approved = [record for record in records if record.status == "approved"]
    if approved:
        return _most_recent(approved)
    return None


def _most_recent_by_status_priority(
    records: list[KycDocumentDocument],
) -> KycDocumentDocument:
    return sorted(
        records,
        key=lambda record: (
            KYC_STATUS_PRIORITY.get(record.status, 99),
            *_kyc_recency_tuple(record),
        ),
    )[0]


def _most_recent(records: list[KycDocumentDocument]) -> KycDocumentDocument:
    return sorted(records, key=_kyc_recency_tuple, reverse=True)[0]


def _kyc_recency_tuple(record: KycDocumentDocument) -> tuple[str, str, str]:
    return (
        _datetime_sort_key(record.reviewed_at),
        _datetime_sort_key(record.uploaded_at),
        _datetime_sort_key(record.created_at),
    )


def _datetime_sort_key(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _build_safe_data(record: KycDocumentDocument) -> dict[str, Any]:
    data: dict[str, Any] = {
        "kyc_id": record.kyc_id,
        "application_id": record.application_id,
        "document_type": record.document_type,
        "status": record.status,
    }
    reason = _resolve_customer_safe_summary(record)
    if reason:
        data["reason"] = reason
    return data


def _resolve_customer_safe_summary(record: KycDocumentDocument) -> str:
    message = (record.customer_safe_message or "").strip()
    if message:
        return message
    if record.status == "pending":
        return _PENDING_SUMMARY
    if record.status == "approved":
        return _APPROVED_SUMMARY
    if record.status in {"rejected", "reupload_required"}:
        return _REJECTED_FALLBACK_SUMMARY
    return "Your KYC document status was retrieved from our demo records."


async def _maybe_create_kyc_reupload_sr(
    service_request_service: ServiceRequestService,
    *,
    ticket_id: str,
    customer_safe_summary: str,
) -> str | None:
    existing = await service_request_service.get_for_ticket(ticket_id)
    if existing is not None:
        if existing.request_type == "kyc_reupload":
            return existing.service_request_id
        return None

    try:
        created = await service_request_service.create_for_ticket(
            ticket_id,
            "kyc_reupload",
            customer_safe_summary=customer_safe_summary,
        )
    except ServiceRequestValidationError:
        return None

    return created.service_request_id
