"""Shared duplicate EMI debit detection helpers."""

from __future__ import annotations

from app.repayments.models import PaymentTransactionDocument


def same_calendar_date(transaction_date: object, due_date: str) -> bool:
    return str(transaction_date).startswith(due_date)


def emi_debit_matches(
    transactions: list[PaymentTransactionDocument],
    *,
    loan_id: str,
    due_date: str | None = None,
) -> list[PaymentTransactionDocument]:
    matching = [
        transaction
        for transaction in transactions
        if transaction.loan_id == loan_id
        and transaction.transaction_type == "emi_debit"
        and transaction.status == "success"
        and (due_date is None or same_calendar_date(transaction.transaction_date, due_date))
    ]
    return matching


def detect_duplicate_emi_debits(
    transactions: list[PaymentTransactionDocument],
    *,
    loan_id: str,
    due_date: str | None = None,
) -> tuple[int, bool]:
    matching = emi_debit_matches(transactions, loan_id=loan_id, due_date=due_date)
    paid_entries_found = len(matching)
    duplicate_debit_found = paid_entries_found >= 2 or any(
        transaction.is_duplicate_candidate for transaction in matching
    )
    return paid_entries_found, duplicate_debit_found
