"""FraudSecurityTool — create mock fraud cases and record protective freeze references."""

from __future__ import annotations

from typing import Any

from app.common.masking import mask_transaction_reference
from app.customers.repositories import CustomerRepository
from app.fraud_cases.models import FraudCaseDocument
from app.fraud_cases.services import FraudCaseService
from app.repayments.models import PaymentTransactionDocument
from app.repayments.repositories import PaymentTransactionRepository
from app.tickets.constants import TicketIntent
from app.tools.audit_hook import ToolAuditHook
from app.tools.base import BaseMockTool
from app.tools.constants import ToolName
from app.tools.exceptions import ToolExecutionError, ToolValidationError
from app.tools.schemas import ToolInput, ToolRunResult

SUPPORTED_INTENTS: frozenset[TicketIntent] = frozenset({"fraud_security_issue"})

_CREATED_SUMMARY = (
    "A protective mock freeze action has been recorded for this demo case, and your "
    "issue has been escalated to the security review queue."
)
_REUSED_SUMMARY = (
    "Your demo fraud security case is already on record and remains escalated for "
    "human review. This is a mock protective action only."
)
_NO_TXN_SUMMARY = (
    "I could not find a matching transaction in the demo records, but because this "
    "is a security concern, I have created a critical fraud review case."
)
_ESCALATION_REASON = "Fraud/security issue requires human review."


class FraudSecurityTool(BaseMockTool):
    """Mock tool to create fraud cases and record demo protective freeze references."""

    def __init__(
        self,
        customer_repository: CustomerRepository,
        payment_transaction_repository: PaymentTransactionRepository,
        fraud_case_service: FraudCaseService | None = None,
        audit_hook: ToolAuditHook | None = None,
    ) -> None:
        super().__init__(audit_hook=audit_hook)
        self._customer_repository = customer_repository
        self._payment_transaction_repository = payment_transaction_repository
        self._fraud_case_service = fraud_case_service

    @property
    def tool_name(self) -> ToolName:
        return "FraudSecurityTool"

    def validate_input(self, tool_input: ToolInput) -> None:
        if tool_input.intent not in SUPPORTED_INTENTS:
            raise ToolValidationError(
                f"FraudSecurityTool does not support intent: {tool_input.intent}"
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
        selected = _resolve_reported_transaction(transactions, parameters=tool_input.parameters)
        fraud_alert_found = any(
            transaction.transaction_type == "fraud_alert" for transaction in transactions
        )

        if self._fraud_case_service is None:
            return ToolRunResult(
                data=_build_safe_data(
                    fraud_case=None,
                    selected_transaction=selected,
                    recent_transaction_count=len(transactions),
                    fraud_alert_found=fraud_alert_found,
                ),
                customer_safe_summary=_NO_TXN_SUMMARY,
                action_taken="fraud_case_created",
                escalation_required=True,
            )

        reported_transaction_id = (
            selected.transaction_id if selected is not None else None
        )
        fraud_case, created_new = await self._fraud_case_service.create_for_ticket(
            tool_input.ticket_id,
            customer_id=tool_input.customer_id,
            reported_transaction_id=reported_transaction_id,
            escalation_reason=_ESCALATION_REASON,
        )

        action_taken, summary = _resolve_action_and_summary(
            created_new=created_new,
            has_transaction=selected is not None,
        )

        return ToolRunResult(
            data=_build_safe_data(
                fraud_case=fraud_case,
                selected_transaction=selected,
                recent_transaction_count=len(transactions),
                fraud_alert_found=fraud_alert_found,
            ),
            customer_safe_summary=summary,
            action_taken=action_taken,
            escalation_required=True,
        )


def _resolve_reported_transaction(
    transactions: list[PaymentTransactionDocument],
    *,
    parameters: dict[str, Any],
) -> PaymentTransactionDocument | None:
    transaction_id = parameters.get("transaction_id")
    if not isinstance(transaction_id, str) or not transaction_id.strip():
        transaction_id = parameters.get("reported_transaction_id")
    if isinstance(transaction_id, str) and transaction_id.strip():
        return next(
            (
                transaction
                for transaction in transactions
                if transaction.transaction_id == transaction_id.strip()
            ),
            None,
        )

    fraud_alerts = [
        transaction
        for transaction in transactions
        if transaction.transaction_type == "fraud_alert"
    ]
    if fraud_alerts:
        return sorted(
            fraud_alerts,
            key=lambda transaction: str(transaction.transaction_date),
            reverse=True,
        )[0]
    return None


def _resolve_action_and_summary(
    *,
    created_new: bool,
    has_transaction: bool,
) -> tuple[str, str]:
    if created_new and has_transaction:
        return "mock_freeze_recorded_and_fraud_case_created", _CREATED_SUMMARY
    if created_new:
        return "fraud_case_created", _NO_TXN_SUMMARY
    return "fraud_case_reused", _REUSED_SUMMARY


def _build_safe_data(
    *,
    fraud_case: FraudCaseDocument | None,
    selected_transaction: PaymentTransactionDocument | None,
    recent_transaction_count: int,
    fraud_alert_found: bool,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "recent_transaction_count": recent_transaction_count,
        "fraud_alert_found": fraud_alert_found,
        "recent_transactions_checked": True,
    }
    if fraud_case is not None:
        data.update(
            {
                "fraud_case_id": fraud_case.fraud_case_id,
                "freeze_simulated": fraud_case.freeze_simulated,
                "freeze_reference": fraud_case.freeze_reference,
                "status": fraud_case.status,
                "priority": fraud_case.priority,
            }
        )
        if fraud_case.reported_transaction_id is not None:
            data["reported_transaction_id"] = fraud_case.reported_transaction_id
    if selected_transaction is not None:
        if selected_transaction.transaction_id is not None:
            data["reported_transaction_id"] = selected_transaction.transaction_id
        data["reference_number_masked"] = mask_transaction_reference(
            selected_transaction.reference_number
        )
    return data
