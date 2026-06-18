"""KYC document persistence models aligned with DATA_MODEL §6.3."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.kyc.constants import KycStatus
from app.lending.models import APPLICATION_ID_PATTERN, CUSTOMER_ID_PATTERN

KYC_ID_PATTERN = r"^KYC-\d{4}-\d{4}$"


class KycDocumentDocument(BaseModel):
    """MongoDB kyc_documents collection document."""

    model_config = ConfigDict(str_strip_whitespace=True)

    kyc_id: str = Field(..., pattern=KYC_ID_PATTERN)
    customer_id: str = Field(..., pattern=CUSTOMER_ID_PATTERN)
    application_id: str = Field(..., pattern=APPLICATION_ID_PATTERN)
    document_type: str
    status: KycStatus
    rejection_reason_code: str | None = None
    customer_safe_message: str | None = None
    uploaded_at: datetime | str | None = None
    reviewed_at: datetime | str | None = None
    created_at: datetime | str

    def to_mongo_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python")
