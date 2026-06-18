"""Message domain exceptions."""

from app.core.exceptions import AppError


class MessageAccessDeniedError(AppError):
    """Raised when an actor is not allowed to create or read a message."""


class MessageValidationError(AppError):
    """Raised when message data fails business validation beyond Pydantic."""
