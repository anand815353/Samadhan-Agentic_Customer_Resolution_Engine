"""Mock tool domain exceptions."""

from app.core.exceptions import AppError
from app.tools.constants import ToolErrorCode


class ToolValidationError(AppError):
    """Raised when tool input or pre-execution validation fails."""


class ToolExecutionError(AppError):
    """Raised when a tool fails in a controlled, expected way."""

    def __init__(
        self,
        message: str = "Tool execution failed",
        *,
        code: ToolErrorCode = "execution_failed",
        retryable: bool = False,
        details: dict | None = None,
    ) -> None:
        self.code = code
        self.retryable = retryable
        self.details = details
        super().__init__(message)
