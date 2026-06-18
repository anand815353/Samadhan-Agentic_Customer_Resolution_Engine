"""Repayment domain constants aligned with DATA_MODEL §7."""

from typing import Literal

REPAYMENT_SCHEDULE_COLLECTION = "repayment_schedule"
PAYMENT_TRANSACTIONS_COLLECTION = "payment_transactions"

RepaymentStatus = Literal["due", "paid", "overdue", "failed"]

TransactionType = Literal["emi_debit", "fee", "refund", "reversal", "fraud_alert"]

TransactionStatus = Literal["success", "failed", "pending", "reversed"]

ALL_REPAYMENT_STATUSES: tuple[RepaymentStatus, ...] = (
    "due",
    "paid",
    "overdue",
    "failed",
)
