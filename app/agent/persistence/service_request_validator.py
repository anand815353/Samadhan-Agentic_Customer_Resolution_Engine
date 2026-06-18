"""Validate service request linkage for workflow ticket updates."""

from __future__ import annotations

from app.agent.exceptions import TicketUpdateValidationError
from app.service_requests.models import ServiceRequestDocument
from app.service_requests.services import ServiceRequestService


async def validate_service_request_link(
    service_request_service: ServiceRequestService,
    *,
    service_request_id: str,
    ticket_id: str,
    customer_id: str,
) -> ServiceRequestDocument:
    """Ensure the SR exists and belongs to the ticket and customer."""
    try:
        document = await service_request_service.get_service_request(service_request_id)
    except Exception as exc:
        raise TicketUpdateValidationError(
            f"service request not found: {service_request_id}",
        ) from exc

    if document.ticket_id != ticket_id:
        raise TicketUpdateValidationError(
            f"service request {service_request_id} does not belong to ticket {ticket_id}",
        )
    if document.customer_id != customer_id:
        raise TicketUpdateValidationError(
            f"service request {service_request_id} does not belong to customer {customer_id}",
        )
    return document
