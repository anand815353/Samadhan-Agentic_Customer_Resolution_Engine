"""RepaymentTool — check EMI schedule, repayment status, and duplicate EMI scenarios."""

from __future__ import annotations

from typing import Any

from app.common.masking import mask_loan_account
from app.customers.repositories import CustomerRepository
from app.lending.models import LoanDocument
from app.lending.repositories import LoanRepository
from app.repayments.duplicate_detection import detect_duplicate_emi_debits
from app.repayments.models import PaymentTransactionDocument, RepaymentScheduleDocument
from app.repayments.repositories import PaymentTransactionRepository, RepaymentScheduleRepository
from app.tickets.constants import TicketIntent
from app.tools.audit_hook import ToolAuditHook
from app.tools.base import BaseMockTool
from app.tools.constants import ToolName
from app.tools.exceptions import ToolExecutionError, ToolValidationError
from app.tools.schemas import ToolInput, ToolRunResult

SUPPORTED_INTENTS: frozenset[TicketIntent] = frozenset(
    {
        "emi_payment_issue",
        "charges_refund_reversal",
        "loan_statement_request",
    }
)

_NO_RECORD_SUMMARY = "I could not find a repayment schedule record for this demo customer."
_PAID_SUMMARY = "Your EMI for the selected due date is marked paid in our demo records."
_DUE_SUMMARY = "Your EMI is currently marked due in our demo records."
_UNPAID_SUMMARY = (
    "Your EMI is not marked paid in our demo records. "
    "Please check your repayment status or contact support if you believe this is incorrect."
)
_DUPLICATE_SUMMARY = (
    "Two EMI payment entries were found for the same due date. "
    "Because this is a financial dispute, this needs human review."
)
_STATEMENT_SUMMARY = (
    "Repayment schedule context was retrieved from our demo records "
    "for your loan statement request."
)


class RepaymentTool(BaseMockTool):
    """Mock tool to read repayment schedule and detect duplicate EMI debits."""

    def __init__(
        self,
        customer_repository: CustomerRepository,
        repayment_schedule_repository: RepaymentScheduleRepository,
        payment_transaction_repository: PaymentTransactionRepository,
        loan_repository: LoanRepository,
        audit_hook: ToolAuditHook | None = None,
    ) -> None:
        super().__init__(audit_hook=audit_hook)
        self._customer_repository = customer_repository
        self._repayment_schedule_repository = repayment_schedule_repository
        self._payment_transaction_repository = payment_transaction_repository
        self._loan_repository = loan_repository

    @property
    def tool_name(self) -> ToolName:
        return "RepaymentTool"

    def validate_input(self, tool_input: ToolInput) -> None:
        if tool_input.intent not in SUPPORTED_INTENTS:
            raise ToolValidationError(
                f"RepaymentTool does not support intent: {tool_input.intent}"
            )

    async def _run(self, tool_input: ToolInput) -> ToolRunResult:
        customer = await self._customer_repository.find_by_id(tool_input.customer_id)
        if customer is None:
            raise ToolExecutionError(
                "Customer record was not found for this demo profile.",
                code="not_found",
                retryable=False,
            )

        schedules = await self._repayment_schedule_repository.find_by_customer(
            tool_input.customer_id
        )
        transactions = await self._payment_transaction_repository.find_by_customer(
            tool_input.customer_id
        )
        loans = await self._loan_repository.find_by_customer(tool_input.customer_id)
        loans_by_id = {loan.loan_id: loan for loan in loans}

        selected = _select_schedule_entry(
            schedules,
            intent=tool_input.intent,
            parameters=tool_input.parameters,
            loans_by_id=loans_by_id,
            transactions=transactions,
        )
        if selected is None:
            return ToolRunResult(
                data={},
                customer_safe_summary=_NO_RECORD_SUMMARY,
                action_taken="repayment_record_not_found",
                escalation_required=False,
            )

        loan = loans_by_id.get(selected.loan_id)
        paid_entries_found, duplicate_debit_found = _detect_duplicate_emi(
            selected,
            transactions,
        )
        data = _build_safe_data(
            selected,
            loan=loan,
            paid_entries_found=paid_entries_found,
            duplicate_debit_found=duplicate_debit_found,
        )
        summary = _resolve_customer_safe_summary(
            selected,
            intent=tool_input.intent,
            duplicate_debit_found=duplicate_debit_found,
        )
        action_taken = (
            "duplicate_emi_detected" if duplicate_debit_found else "repayment_schedule_checked"
        )
        escalation_required = duplicate_debit_found

        return ToolRunResult(
            data=data,
            customer_safe_summary=summary,
            action_taken=action_taken,
            escalation_required=escalation_required,
        )


def _select_schedule_entry(
    schedules: list[RepaymentScheduleDocument],
    *,
    intent: TicketIntent,
    parameters: dict[str, Any],
    loans_by_id: dict[str, LoanDocument],
    transactions: list[PaymentTransactionDocument],
) -> RepaymentScheduleDocument | None:
    if not schedules:
        return None

    filtered = list(schedules)
    loan_id = parameters.get("loan_id")
    if isinstance(loan_id, str) and loan_id.strip():
        filtered = [entry for entry in filtered if entry.loan_id == loan_id.strip()]

    due_date = parameters.get("due_date")
    if isinstance(due_date, str) and due_date.strip():
        filtered = [entry for entry in filtered if entry.due_date == due_date.strip()]

    emi_number = parameters.get("emi_number")
    if isinstance(emi_number, int):
        filtered = [entry for entry in filtered if entry.emi_number == emi_number]
    elif isinstance(emi_number, str) and emi_number.strip().isdigit():
        value = int(emi_number.strip())
        filtered = [entry for entry in filtered if entry.emi_number == value]

    month = parameters.get("month")
    if isinstance(month, str) and month.strip():
        prefix = month.strip()
        filtered = [entry for entry in filtered if entry.due_date.startswith(prefix)]

    if not filtered:
        return None

    if len(filtered) == 1:
        return filtered[0]

    if intent == "loan_statement_request":
        return _select_for_statement_request(filtered, loans_by_id=loans_by_id)

    return _select_for_payment_issue(filtered, loans_by_id=loans_by_id, transactions=transactions)


def _select_for_statement_request(
    schedules: list[RepaymentScheduleDocument],
    *,
    loans_by_id: dict[str, LoanDocument],
) -> RepaymentScheduleDocument:
    active_entries = [
        entry
        for entry in schedules
        if loans_by_id.get(entry.loan_id) is not None
        and loans_by_id[entry.loan_id].status == "active"
    ]
    pool = active_entries or schedules
    return sorted(pool, key=lambda entry: entry.due_date, reverse=True)[0]


def _select_for_payment_issue(
    schedules: list[RepaymentScheduleDocument],
    *,
    loans_by_id: dict[str, LoanDocument],
    transactions: list[PaymentTransactionDocument],
) -> RepaymentScheduleDocument:
    duplicate_candidates = [
        entry
        for entry in schedules
        if _detect_duplicate_emi(entry, transactions)[1]
    ]
    if duplicate_candidates:
        return sorted(duplicate_candidates, key=lambda entry: entry.due_date, reverse=True)[0]

    active_entries = [
        entry
        for entry in schedules
        if loans_by_id.get(entry.loan_id) is not None
        and loans_by_id[entry.loan_id].status == "active"
    ]
    pool = active_entries or schedules
    return sorted(pool, key=lambda entry: entry.due_date, reverse=True)[0]


def _detect_duplicate_emi(
    schedule: RepaymentScheduleDocument,
    transactions: list[PaymentTransactionDocument],
) -> tuple[int, bool]:
    return detect_duplicate_emi_debits(
        transactions,
        loan_id=schedule.loan_id,
        due_date=schedule.due_date,
    )


def _build_safe_data(
    schedule: RepaymentScheduleDocument,
    *,
    loan: LoanDocument | None,
    paid_entries_found: int,
    duplicate_debit_found: bool,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "loan_id": schedule.loan_id,
        "emi_due_date": schedule.due_date,
        "expected_emi_amount": schedule.emi_amount,
        "repayment_status": schedule.status,
        "paid_entries_found": paid_entries_found,
        "duplicate_debit_found": duplicate_debit_found,
    }
    if loan is not None:
        data["loan_account_masked"] = mask_loan_account(loan.loan_account_number)
    return data


def _resolve_customer_safe_summary(
    schedule: RepaymentScheduleDocument,
    *,
    intent: TicketIntent,
    duplicate_debit_found: bool,
) -> str:
    if duplicate_debit_found:
        return _DUPLICATE_SUMMARY
    if intent == "loan_statement_request":
        return _STATEMENT_SUMMARY
    if schedule.status == "paid":
        return _PAID_SUMMARY
    if schedule.status == "due":
        return _DUE_SUMMARY
    if schedule.status in {"overdue", "failed"}:
        return _UNPAID_SUMMARY
    return "Your repayment schedule status was retrieved from our demo records."
