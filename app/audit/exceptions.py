"""Audit log domain exceptions."""

from app.core.exceptions import AppError


class AuditValidationError(AppError):
    """Raised when audit event data fails business validation beyond Pydantic."""
