"""Refund request domain constants aligned with DATA_MODEL §7.3."""

from typing import Literal

REFUND_REQUESTS_COLLECTION = "refund_requests"

RefundRequestStatus = Literal[
    "created",
    "under_review",
    "approved_mock",
    "rejected_mock",
    "closed",
]

ALL_REFUND_REQUEST_STATUSES: tuple[RefundRequestStatus, ...] = (
    "created",
    "under_review",
    "approved_mock",
    "rejected_mock",
    "closed",
)
