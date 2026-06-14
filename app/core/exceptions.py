"""Application exception types."""


class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str = "Application error") -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""


class ConflictError(AppError):
    """Raised when an operation conflicts with existing state."""

