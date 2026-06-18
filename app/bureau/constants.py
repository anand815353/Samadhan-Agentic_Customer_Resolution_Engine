"""Bureau reporting log domain constants aligned with DATA_MODEL §8.2."""

from typing import Literal

BUREAU_REPORTING_LOGS_COLLECTION = "bureau_reporting_logs"

BatchStatus = Literal["pending", "submitted", "accepted", "failed"]

ALL_BATCH_STATUSES: tuple[BatchStatus, ...] = (
    "pending",
    "submitted",
    "accepted",
    "failed",
)
