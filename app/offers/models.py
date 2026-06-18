"""Offer persistence models aligned with DATA_MODEL §8.5."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.lending.models import CUSTOMER_ID_PATTERN
from app.offers.constants import OfferType

OFFER_ID_PATTERN = r"^OFFER-\d{4}-\d{4}$"


class OfferDocument(BaseModel):
    """MongoDB offers collection document."""

    model_config = ConfigDict(str_strip_whitespace=True)

    offer_id: str = Field(..., pattern=OFFER_ID_PATTERN)
    customer_id: str = Field(..., pattern=CUSTOMER_ID_PATTERN)
    offer_type: OfferType
    is_eligible: bool
    approved_limit: float | int | None = None
    interest_rate: float | int | None = None
    tenure_options: list[int] | None = None
    valid_until: date | str | None = None
    non_eligibility_reason: str | None = None
    lead_created: bool = False
    created_at: datetime | str

    @field_validator("tenure_options", mode="before")
    @classmethod
    def _coerce_tenure_options(cls, value: Any) -> list[int] | None:
        if value is None:
            return None
        if isinstance(value, list):
            return [int(item) for item in value]
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            parsed = json.loads(text)
            if not isinstance(parsed, list):
                raise ValueError("tenure_options must be a JSON array")
            return [int(item) for item in parsed]
        raise ValueError("tenure_options must be a list or JSON array string")

    def to_mongo_dict(self) -> dict[str, Any]:
        payload = self.model_dump(mode="python")
        tenure_options = payload.get("tenure_options")
        if isinstance(tenure_options, list):
            payload["tenure_options"] = json.dumps(tenure_options)
        return payload
