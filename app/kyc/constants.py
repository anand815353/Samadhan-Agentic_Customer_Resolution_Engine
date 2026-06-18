"""KYC document domain constants aligned with DATA_MODEL §6.3."""

from typing import Literal

KYC_DOCUMENTS_COLLECTION = "kyc_documents"

KycStatus = Literal["pending", "approved", "rejected", "reupload_required"]

ALL_KYC_STATUSES: tuple[KycStatus, ...] = (
    "pending",
    "approved",
    "rejected",
    "reupload_required",
)

ACTION_NEEDED_KYC_STATUSES: frozenset[str] = frozenset(
    {"reupload_required", "rejected", "pending"}
)

KYC_STATUS_PRIORITY: dict[str, int] = {
    "reupload_required": 0,
    "rejected": 1,
    "pending": 2,
    "approved": 3,
}
