"""Shared abstractions for repositories and services."""

from app.common.masking import (
    mask_aadhaar,
    mask_audit_event_for_display,
    mask_email,
    mask_loan_account,
    mask_mobile,
    mask_pan,
    mask_sensitive_data,
    mask_transaction_reference,
    mask_value_by_key,
)
from app.common.repository import BaseRepository, Repository
from app.common.service import BaseService, Service

__all__ = [
    "BaseRepository",
    "BaseService",
    "Repository",
    "Service",
    "mask_aadhaar",
    "mask_audit_event_for_display",
    "mask_email",
    "mask_loan_account",
    "mask_mobile",
    "mask_pan",
    "mask_sensitive_data",
    "mask_transaction_reference",
    "mask_value_by_key",
]
