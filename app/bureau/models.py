"""Bureau reporting log persistence models aligned with DATA_MODEL §8.2."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.bureau.constants import BatchStatus
from app.lending.models import CUSTOMER_ID_PATTERN, LOAN_ID_PATTERN

BUREAU_LOG_ID_PATTERN = r"^BRL-\d{4}-\d{4}$"


class BureauReportingLogDocument(BaseModel):
    """MongoDB bureau_reporting_logs collection document."""

    model_config = ConfigDict(str_strip_whitespace=True)

    bureau_log_id: str = Field(..., pattern=BUREAU_LOG_ID_PATTERN)
    customer_id: str = Field(..., pattern=CUSTOMER_ID_PATTERN)
    loan_id: str = Field(..., pattern=LOAN_ID_PATTERN)
    bureau_name: str
    reporting_month: str
    internal_loan_status: str
    reported_status: str
    batch_id: str
    batch_status: BatchStatus
    expected_update_window_days: int
    submitted_at: datetime | str | None = None
    accepted_at: datetime | str | None = None
    created_at: datetime | str

    def to_mongo_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python")
