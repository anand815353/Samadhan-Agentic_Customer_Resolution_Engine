"""TransactionTool — inspect payment transactions and create mock reversal reviews."""

from __future__ import annotations

from typing import Any

from app.common.masking import mask_loan_account, mask_transaction_reference
from app.customers.repositories import CustomerRepository
from app.lending.models import LoanDocument
from app.lending.repositories import LoanRepository
from app.refund_requests.services import RefundRequestService
from app.repayments.duplicate_detection import detect_duplicate_emi_debits, same_calendar_date
from app.repayments.models import PaymentTransactionDocument
from app.repayments.repositories import PaymentTransactionRepository
from app.tickets.constants import TicketIntent
from app.tools.audit_hook import ToolAuditHook
from app.tools.base import BaseMockTool
from app.tools.constants import ToolName
from app.tools.exceptions import ToolExecutionError, ToolValidationError
from app.tools.schemas import ToolInput, ToolRunResult

SUPPORTED_INTENTS: frozenset[TicketIntent] = frozenset(
    {
        "charges_refund_reversal",
        "emi_payment_issue",
        "fraud_security_issue",
    }
)

_NO_RECORD_SUMMARY = "I could not find a matching transaction record for this demo customer."
_DUPLICATE_SUMMARY = (
    "I found more than one successful debit entry that may relate to the same payment. "
    "Because this is a financial dispute, this needs human review."
)
_REVERSAL_REVIEW_SUMMARY = (
    "A mock reversal review request has been created for the disputed charge. "
    "This does not mean a real refund or reversal has been completed."
)
_FEE_SUMMARY = (
    "I checked the fee transaction details in our demo records. "
    "If you believe this charge is incorrect, it will need review."
)
_FRAUD_SUMMARY = (
    "I checked recent transaction alerts in our demo records. "
    "A security concern needs human review."
)
_GENERIC_SUMMARY = "Transaction details were retrieved from our demo records."

_DISPUTE_TRANSACTION_TYPES: frozenset[str] = frozenset({"fee", "refund", "reversal"})
_REVERSAL_REVIEW_REASON = "Mock reversal review for disputed charge"


class TransactionTool(BaseMockTool):
    """Mock tool to inspect payment transactions and create reversal reviews."""

    def __init__(
        self,
        customer_repository: CustomerRepository,
        payment_transaction_repository: PaymentTransactionRepository,
        loan_repository: LoanRepository,
        refund_request_service: RefundRequestService | None = None,
        audit_hook: ToolAuditHook | None = None,
    ) -> None:
        super().__init__(audit_hook=audit_hook)
        self._customer_repository = customer_repository
        self._payment_transaction_repository = payment_transaction_repository
        self._loan_repository = loan_repository
        self._refund_request_service = refund_request_service

    @property
    def tool_name(self) -> ToolName:
        return "TransactionTool"

    def validate_input(self, tool_input: ToolInput) -> None:
        if tool_input.intent not in SUPPORTED_INTENTS:
            raise ToolValidationError(
                f"TransactionTool does not support intent: {tool_input.intent}"
            )

    async def _run(self, tool_input: ToolInput) -> ToolRunResult:
        customer = await self._customer_repository.find_by_id(tool_input.customer_id)
        if customer is None:
            raise ToolExecutionError(
                "Customer record was not found for this demo profile.",
                code="not_found",
                retryable=False,
            )

        transactions = await self._payment_transaction_repository.find_by_customer(
            tool_input.customer_id
        )
        loans = await self._loan_repository.find_by_customer(tool_input.customer_id)
        loans_by_id = {loan.loan_id: loan for loan in loans if loan.loan_id is not None}

        selected = _select_transaction(
            transactions,
            intent=tool_input.intent,
            parameters=tool_input.parameters,
        )
        if selected is None:
            return ToolRunResult(
                data={},
                customer_safe_summary=_NO_RECORD_SUMMARY,
                action_taken="transaction_record_not_found",
                escalation_required=False,
            )

        loan = loans_by_id.get(selected.loan_id) if selected.loan_id else None
        duplicate_count, duplicate_found = _duplicate_context_for_transaction(
            selected,
            transactions,
            parameters=tool_input.parameters,
        )
        refund_request_id: str | None = None
        review_status: str | None = None
        action_taken = "transactions_checked"
        escalation_required = False
        summary = _GENERIC_SUMMARY

        if tool_input.intent == "fraud_security_issue":
            action_taken = "recent_transactions_checked"
            escalation_required = selected.transaction_type == "fraud_alert"
            summary = _FRAUD_SUMMARY if escalation_required else _GENERIC_SUMMARY
        elif duplicate_found:
            action_taken = "duplicate_debit_found"
            escalation_required = True
            summary = _DUPLICATE_SUMMARY
            if (
                tool_input.intent == "charges_refund_reversal"
                and self._refund_request_service is not None
            ):
                refund_doc = await self._refund_request_service.create_reversal_review_for_ticket(
                    tool_input.ticket_id,
                    selected,
                    reason=_REVERSAL_REVIEW_REASON,
                )
                refund_request_id = refund_doc.refund_request_id
                review_status = refund_doc.status
                action_taken = "reversal_review_created"
                summary = _REVERSAL_REVIEW_SUMMARY
        elif tool_input.intent == "charges_refund_reversal":
            if selected.transaction_type in _DISPUTE_TRANSACTION_TYPES:
                action_taken = "fee_charge_checked"
                escalation_required = True
                summary = _FEE_SUMMARY
                if self._refund_request_service is not None:
                    refund_doc = await self._refund_request_service.create_reversal_review_for_ticket(
                        tool_input.ticket_id,
                        selected,
                        reason=_REVERSAL_REVIEW_REASON,
                    )
                    refund_request_id = refund_doc.refund_request_id
                    review_status = refund_doc.status
                    action_taken = "reversal_review_created"
                    summary = _REVERSAL_REVIEW_SUMMARY
            else:
                action_taken = "fee_charge_checked"
                escalation_required = True
                summary = _FEE_SUMMARY
        elif tool_input.intent == "emi_payment_issue":
            action_taken = "duplicate_debit_checked"
            escalation_required = False
            summary = _GENERIC_SUMMARY

        data = _build_safe_data(
            selected,
            loan=loan,
            duplicate_debit_found=duplicate_found,
            duplicate_debit_count=duplicate_count,
            refund_request_id=refund_request_id,
            review_status=review_status,
        )

        return ToolRunResult(
            data=data,
            customer_safe_summary=summary,
            action_taken=action_taken,
            escalation_required=escalation_required,
        )


def _select_transaction(
    transactions: list[PaymentTransactionDocument],
    *,
    intent: TicketIntent,
    parameters: dict[str, Any],
) -> PaymentTransactionDocument | None:
    if not transactions:
        return None

    filtered = list(transactions)
    transaction_id = parameters.get("transaction_id")
    if isinstance(transaction_id, str) and transaction_id.strip():
        filtered = [
            transaction
            for transaction in filtered
            if transaction.transaction_id == transaction_id.strip()
        ]

    loan_id = parameters.get("loan_id")
    if isinstance(loan_id, str) and loan_id.strip():
        filtered = [
            transaction
            for transaction in filtered
            if transaction.loan_id == loan_id.strip()
        ]

    transaction_type = parameters.get("transaction_type")
    if isinstance(transaction_type, str) and transaction_type.strip():
        filtered = [
            transaction
            for transaction in filtered
            if transaction.transaction_type == transaction_type.strip()
        ]

    status = parameters.get("status")
    if isinstance(status, str) and status.strip():
        filtered = [
            transaction
            for transaction in filtered
            if transaction.status == status.strip()
        ]

    amount = parameters.get("amount")
    if isinstance(amount, (int, float)):
        filtered = [transaction for transaction in filtered if transaction.amount == float(amount)]

    due_date = parameters.get("due_date")
    if isinstance(due_date, str) and due_date.strip():
        filtered = [
            transaction
            for transaction in filtered
            if same_calendar_date(transaction.transaction_date, due_date.strip())
        ]

    month = parameters.get("month")
    if isinstance(month, str) and month.strip():
        prefix = month.strip()
        filtered = [
            transaction
            for transaction in filtered
            if str(transaction.transaction_date).startswith(prefix)
        ]

    if not filtered:
        return None

    if len(filtered) == 1:
        return filtered[0]

    if intent == "fraud_security_issue":
        fraud_alerts = [
            transaction
            for transaction in filtered
            if transaction.transaction_type == "fraud_alert"
        ]
        if fraud_alerts:
            return sorted(
                fraud_alerts,
                key=lambda transaction: str(transaction.transaction_date),
                reverse=True,
            )[0]

    if intent == "charges_refund_reversal":
        return _select_for_refund_dispute(filtered)

    if intent == "emi_payment_issue":
        return _select_for_emi_duplicate(filtered)

    return sorted(filtered, key=lambda transaction: str(transaction.transaction_date), reverse=True)[0]


def _select_for_refund_dispute(
    transactions: list[PaymentTransactionDocument],
) -> PaymentTransactionDocument:
    for txn_type in ("fee", "refund", "reversal"):
        matches = [transaction for transaction in transactions if transaction.transaction_type == txn_type]
        if matches:
            return sorted(matches, key=lambda transaction: str(transaction.transaction_date), reverse=True)[0]

    duplicate_candidates = [
        transaction
        for transaction in transactions
        if transaction.transaction_type == "emi_debit" and transaction.is_duplicate_candidate
    ]
    if duplicate_candidates:
        return duplicate_candidates[0]

    return sorted(transactions, key=lambda transaction: str(transaction.transaction_date), reverse=True)[0]


def _select_for_emi_duplicate(
    transactions: list[PaymentTransactionDocument],
) -> PaymentTransactionDocument:
    duplicate_candidates = [
        transaction
        for transaction in transactions
        if transaction.transaction_type == "emi_debit" and transaction.is_duplicate_candidate
    ]
    if duplicate_candidates:
        return duplicate_candidates[0]

    emi_debits = [
        transaction
        for transaction in transactions
        if transaction.transaction_type == "emi_debit" and transaction.status == "success"
    ]
    if emi_debits:
        return sorted(emi_debits, key=lambda transaction: str(transaction.transaction_date), reverse=True)[0]

    return sorted(transactions, key=lambda transaction: str(transaction.transaction_date), reverse=True)[0]


def _duplicate_context_for_transaction(
    selected: PaymentTransactionDocument,
    transactions: list[PaymentTransactionDocument],
    *,
    parameters: dict[str, Any],
) -> tuple[int, bool]:
    if selected.transaction_type != "emi_debit" or selected.loan_id is None:
        return 0, False

    due_date = parameters.get("due_date")
    due_date_value = due_date.strip() if isinstance(due_date, str) and due_date.strip() else None
    if due_date_value is None:
        due_date_value = str(selected.transaction_date)[:10]

    return detect_duplicate_emi_debits(
        transactions,
        loan_id=selected.loan_id,
        due_date=due_date_value,
    )


def _build_safe_data(
    transaction: PaymentTransactionDocument,
    *,
    loan: LoanDocument | None,
    duplicate_debit_found: bool,
    duplicate_debit_count: int,
    refund_request_id: str | None,
    review_status: str | None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "transaction_id": transaction.transaction_id,
        "transaction_type": transaction.transaction_type,
        "amount": transaction.amount,
        "status": transaction.status,
        "transaction_date": str(transaction.transaction_date),
        "reference_number_masked": mask_transaction_reference(transaction.reference_number),
        "duplicate_debit_found": duplicate_debit_found,
    }
    if duplicate_debit_count > 0:
        data["duplicate_debit_count"] = duplicate_debit_count
    if transaction.loan_id is not None:
        data["loan_id"] = transaction.loan_id
    if loan is not None:
        data["loan_account_masked"] = mask_loan_account(loan.loan_account_number)
    if refund_request_id is not None:
        data["refund_request_id"] = refund_request_id
    if review_status is not None:
        data["review_status"] = review_status
    return data
