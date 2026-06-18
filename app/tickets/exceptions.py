"""Ticket domain exceptions."""

from app.core.exceptions import AppError


class InvalidTicketTransitionError(AppError):
    """Raised when a ticket status transition is not allowed."""

    def __init__(
        self,
        message: str = "Invalid ticket status transition",
        *,
        ticket_id: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
    ) -> None:
        self.ticket_id = ticket_id
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(message)


class TicketAccessDeniedError(AppError):
    """Raised when an actor is not allowed to read ticket detail."""


class StaleTicketUpdateError(AppError):
    """Raised when a ticket was modified externally before workflow persistence."""

    def __init__(
        self,
        message: str = "Ticket state changed before workflow update could apply",
        *,
        ticket_id: str | None = None,
        expected_status: str | None = None,
        actual_status: str | None = None,
    ) -> None:
        self.ticket_id = ticket_id
        self.expected_status = expected_status
        self.actual_status = actual_status
        super().__init__(message)
