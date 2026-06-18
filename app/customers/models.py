"""Customer persistence models aligned with DATA_MODEL §5."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

CUSTOMER_ID_PATTERN = r"^CUST-\d{3}$"


class CustomerDocument(BaseModel):
    """MongoDB customers collection document."""

    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: str = Field(..., pattern=CUSTOMER_ID_PATTERN)
    full_name: str
    email: str | None = None
    mobile: str | None = None
    pan: str | None = None
    scenario_label: str | None = None
    folder_path: str | None = None
    aadhaar_last4: str | None = None
    date_of_birth: str | None = None
    city: str | None = None
    customer_since: str | None = None
    risk_segment_label: str | None = None
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None

    def to_mongo_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python")
