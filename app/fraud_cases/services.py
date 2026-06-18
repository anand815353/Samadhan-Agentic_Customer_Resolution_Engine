"""Fraud case business logic for mock security case creation."""

from __future__ import annotations

from datetime import UTC, datetime

from app.common.service import BaseService
from app.fraud_cases.id_generation import (
    allocate_fraud_case_id,
    format_freeze_reference,
    parse_fraud_case_id,
)
from app.fraud_cases.models import FraudCaseDocument
from app.fraud_cases.repositories import FraudCaseRepository
from app.tickets.services import TicketService

_DEFAULT_ESCALATION_REASON = "Fraud/security issue requires human review."


class FraudCaseService(BaseService):
    """Domain service for mock fraud case persistence and ticket escalation."""

    def __init__(
        self,
        repository: FraudCaseRepository,
        ticket_service: TicketService,
    ) -> None:
        self._repository = repository
        self._ticket_service = ticket_service

    async def create_for_ticket(
        self,
        ticket_id: str,
        *,
        customer_id: str,
        reported_transaction_id: str | None,
        escalation_reason: str = _DEFAULT_ESCALATION_REASON,
    ) -> tuple[FraudCaseDocument, bool]:
        existing = await self._repository.find_by_ticket(ticket_id)
        if existing is not None:
            await self._ticket_service.escalate_to_human_review(
                ticket_id,
                reason=escalation_reason,
            )
            return existing, False

        now = datetime.now(UTC)
        fraud_case_id = await allocate_fraud_case_id(self._repository)
        year, sequence = parse_fraud_case_id(fraud_case_id)
        document = FraudCaseDocument(
            fraud_case_id=fraud_case_id,
            ticket_id=ticket_id,
            customer_id=customer_id,
            reported_transaction_id=reported_transaction_id,
            freeze_simulated=True,
            freeze_reference=format_freeze_reference(year=year, sequence=sequence),
            status="escalated",
            priority="critical",
            created_at=now,
            updated_at=now,
        )
        saved = await self._repository.insert(document)
        await self._ticket_service.escalate_to_human_review(
            ticket_id,
            reason=escalation_reason,
        )
        return saved, True
