"""Lending persistence models aligned with DATA_MODEL §6."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.lending.constants import ApplicationStatus, BureauStatus, LoanStatus, NocStatus

CUSTOMER_ID_PATTERN = r"^CUST-\d{3}$"
APPLICATION_ID_PATTERN = r"^APP-\d{4}-\d{4}$"
LOAN_ID_PATTERN = r"^LN-\d{4}-\d{4}$"


class LoanApplicationDocument(BaseModel):
    """MongoDB loan_applications collection document."""

    model_config = ConfigDict(str_strip_whitespace=True)

    application_id: str = Field(..., pattern=APPLICATION_ID_PATTERN)
    customer_id: str = Field(..., pattern=CUSTOMER_ID_PATTERN)
    product_type: str
    application_date: str
    requested_amount: float
    status: ApplicationStatus
    current_stage: str
    rejection_code: str | None = None
    customer_safe_rejection_reason: str | None = None
    internal_rejection_notes: str | None = None
    last_updated_at: datetime | str
    created_at: datetime | str

    def to_mongo_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python")


class LoanDocument(BaseModel):
    """MongoDB loans collection document."""

    model_config = ConfigDict(str_strip_whitespace=True)

    loan_id: str = Field(..., pattern=LOAN_ID_PATTERN)
    loan_account_number: str
    customer_id: str = Field(..., pattern=CUSTOMER_ID_PATTERN)
    application_id: str | None = Field(default=None, pattern=APPLICATION_ID_PATTERN)
    product_type: str
    principal_amount: float
    disbursed_amount: float
    interest_rate: float
    tenure_months: int
    emi_amount: float
    status: LoanStatus
    bureau_status: BureauStatus
    disbursal_date: str | None = None
    closure_date: str | None = None
    noc_status: NocStatus | None = None
    created_at: datetime | str
    updated_at: datetime | str

    def to_mongo_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python")
