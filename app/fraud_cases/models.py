"""Fraud case persistence models aligned with DATA_MODEL §8.4."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.fraud_cases.constants import FraudCasePriority, FraudCaseStatus
from app.lending.models import CUSTOMER_ID_PATTERN
from app.repayments.models import TRANSACTION_ID_PATTERN

FRAUD_CASE_ID_PATTERN = r"^FRD-\d{4}-\d{4}$"
TICKET_ID_PATTERN = r"^TKT-\d{4}-\d{4}$"


class FraudCaseDocument(BaseModel):
    """MongoDB fraud_cases collection document."""

    model_config = ConfigDict(str_strip_whitespace=True)

    fraud_case_id: str = Field(..., pattern=FRAUD_CASE_ID_PATTERN)
    ticket_id: str = Field(..., pattern=TICKET_ID_PATTERN)
    customer_id: str = Field(..., pattern=CUSTOMER_ID_PATTERN)
    reported_transaction_id: str | None = Field(default=None, pattern=TRANSACTION_ID_PATTERN)
    freeze_simulated: bool
    freeze_reference: str | None = None
    status: FraudCaseStatus
    priority: FraudCasePriority = "critical"
    created_at: datetime | str
    updated_at: datetime | str

    def to_mongo_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python")
