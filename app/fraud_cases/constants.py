"""Fraud case domain constants aligned with DATA_MODEL §8.4."""

from typing import Literal

FRAUD_CASES_COLLECTION = "fraud_cases"

FraudCaseStatus = Literal["created", "escalated", "under_review", "closed"]

FraudCasePriority = Literal["critical"]

ALL_FRAUD_CASE_STATUSES: tuple[FraudCaseStatus, ...] = (
    "created",
    "escalated",
    "under_review",
    "closed",
)
