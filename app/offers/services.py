"""Offer business logic for mock lead interest recording."""

from __future__ import annotations

from app.common.service import BaseService
from app.core.exceptions import NotFoundError
from app.offers.models import OfferDocument
from app.offers.repositories import OfferRepository


class OfferService(BaseService):
    """Domain service for mock offer lead persistence."""

    def __init__(self, repository: OfferRepository) -> None:
        self._repository = repository

    async def record_mock_lead(self, offer_id: str) -> tuple[OfferDocument, bool]:
        offer = await self._repository.find_by_id(offer_id)
        if offer is None:
            raise NotFoundError(f"offer not found: {offer_id}")
        if offer.lead_created:
            return offer, False

        updated = offer.model_copy(update={"lead_created": True})
        saved = await self._repository.update(updated)
        return saved, True
