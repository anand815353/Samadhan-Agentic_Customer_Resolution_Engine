"""RM mapping persistence models aligned with DATA_MODEL §8.3."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.lending.models import CUSTOMER_ID_PATTERN

RM_MAPPING_ID_PATTERN = r"^RM-\d{4}-\d{4}$"


class RmMappingDocument(BaseModel):
    """MongoDB rm_mapping collection document."""

    model_config = ConfigDict(str_strip_whitespace=True)

    rm_mapping_id: str = Field(..., pattern=RM_MAPPING_ID_PATTERN)
    customer_id: str = Field(..., pattern=CUSTOMER_ID_PATTERN)
    rm_name: str
    rm_email: str
    rm_phone: str
    branch: str
    callback_available: bool = True
    created_at: datetime | str

    def to_mongo_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python")
