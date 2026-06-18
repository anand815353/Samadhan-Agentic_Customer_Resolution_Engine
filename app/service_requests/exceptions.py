"""Service request domain exceptions."""

from app.core.exceptions import AppError


class InvalidServiceRequestTransitionError(AppError):
    """Raised when a service request status transition is not allowed."""

    def __init__(
        self,
        message: str = "Invalid service request status transition",
        *,
        service_request_id: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
    ) -> None:
        self.service_request_id = service_request_id
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(message)


class ServiceRequestValidationError(AppError):
    """Raised when service request business validation fails."""
