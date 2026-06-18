"""Refund request business logic for mock reversal review creation."""

from __future__ import annotations

from datetime import UTC, datetime

from app.common.service import BaseService
from app.refund_requests.id_generation import allocate_refund_request_id
from app.refund_requests.models import RefundRequestDocument
from app.refund_requests.repositories import RefundRequestRepository
from app.repayments.models import PaymentTransactionDocument
from app.tickets.services import TicketService


class RefundRequestService(BaseService):
    """Domain service for mock refund/reversal review records."""

    def __init__(
        self,
        repository: RefundRequestRepository,
        ticket_service: TicketService,
    ) -> None:
        self._repository = repository
        self._ticket_service = ticket_service

    async def create_reversal_review_for_ticket(
        self,
        ticket_id: str,
        transaction: PaymentTransactionDocument,
        *,
        reason: str,
    ) -> RefundRequestDocument:
        existing = await self._repository.find_by_ticket(ticket_id)
        if existing is not None:
            return existing

        ticket = await self._ticket_service.get_ticket(ticket_id)
        now = datetime.now(UTC)
        refund_request_id = await allocate_refund_request_id(self._repository)
        document = RefundRequestDocument(
            refund_request_id=refund_request_id,
            customer_id=ticket.customer_id,
            ticket_id=ticket_id,
            loan_id=transaction.loan_id,
            transaction_id=transaction.transaction_id,
            reason=reason,
            amount=transaction.amount,
            status="under_review",
            created_at=now,
            updated_at=now,
        )
        return await self._repository.insert(document)
