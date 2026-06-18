"""Offer domain constants aligned with DATA_MODEL §8.5."""

from typing import Literal

OFFERS_COLLECTION = "offers"

OfferType = Literal["top_up", "fresh_loan"]

ALL_OFFER_TYPES: tuple[OfferType, ...] = ("top_up", "fresh_loan")
