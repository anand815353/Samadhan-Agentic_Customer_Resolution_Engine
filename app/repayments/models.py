"""Repayment persistence models aligned with DATA_MODEL §7.1–7.2."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.lending.models import CUSTOMER_ID_PATTERN, LOAN_ID_PATTERN
from app.repayments.constants import RepaymentStatus, TransactionStatus, TransactionType

SCHEDULE_ID_PATTERN = r"^SCH-\d{4}-\d{4}$"
TRANSACTION_ID_PATTERN = r"^TXN-\d{4}-\d{4}$"


class RepaymentScheduleDocument(BaseModel):
    """MongoDB repayment_schedule collection document."""

    model_config = ConfigDict(str_strip_whitespace=True)

    schedule_id: str = Field(..., pattern=SCHEDULE_ID_PATTERN)
    loan_id: str = Field(..., pattern=LOAN_ID_PATTERN)
    customer_id: str = Field(..., pattern=CUSTOMER_ID_PATTERN)
    emi_number: int
    due_date: str
    emi_amount: float
    principal_component: float
    interest_component: float
    status: RepaymentStatus
    paid_date: str | None = None
    transaction_id: str | None = Field(default=None, pattern=TRANSACTION_ID_PATTERN)
    created_at: datetime | str

    def to_mongo_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python")


class PaymentTransactionDocument(BaseModel):
    """MongoDB payment_transactions collection document."""

    model_config = ConfigDict(str_strip_whitespace=True)

    transaction_id: str = Field(..., pattern=TRANSACTION_ID_PATTERN)
    customer_id: str = Field(..., pattern=CUSTOMER_ID_PATTERN)
    loan_id: str | None = Field(default=None, pattern=LOAN_ID_PATTERN)
    transaction_type: TransactionType
    amount: float
    transaction_date: datetime | str
    status: TransactionStatus
    reference_number: str
    is_duplicate_candidate: bool = False
    remarks: str | None = None
    created_at: datetime | str

    def to_mongo_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python")
