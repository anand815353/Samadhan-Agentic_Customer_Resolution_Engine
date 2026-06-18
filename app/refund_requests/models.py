"""Refund request persistence models aligned with DATA_MODEL §7.3."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.lending.models import CUSTOMER_ID_PATTERN, LOAN_ID_PATTERN
from app.refund_requests.constants import RefundRequestStatus
from app.repayments.models import TRANSACTION_ID_PATTERN

REFUND_REQUEST_ID_PATTERN = r"^REF-\d{4}-\d{4}$"
TICKET_ID_PATTERN = r"^TKT-\d{4}-\d{4}$"


class RefundRequestDocument(BaseModel):
    """MongoDB refund_requests collection document."""

    model_config = ConfigDict(str_strip_whitespace=True)

    refund_request_id: str = Field(..., pattern=REFUND_REQUEST_ID_PATTERN)
    customer_id: str = Field(..., pattern=CUSTOMER_ID_PATTERN)
    ticket_id: str = Field(..., pattern=TICKET_ID_PATTERN)
    loan_id: str | None = Field(default=None, pattern=LOAN_ID_PATTERN)
    transaction_id: str | None = Field(default=None, pattern=TRANSACTION_ID_PATTERN)
    reason: str
    amount: float
    status: RefundRequestStatus
    created_at: datetime | str
    updated_at: datetime | str

    def to_mongo_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python")
