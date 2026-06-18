"""OfferEligibilityTool — check mock top-up offer eligibility and record demo lead interest."""

from __future__ import annotations

from typing import Any

from app.customers.repositories import CustomerRepository
from app.offers.constants import OfferType
from app.offers.models import OfferDocument
from app.offers.repositories import OfferRepository
from app.offers.services import OfferService
from app.tickets.constants import TicketIntent
from app.tools.audit_hook import ToolAuditHook
from app.tools.base import BaseMockTool
from app.tools.constants import ToolName
from app.tools.exceptions import ToolExecutionError, ToolValidationError
from app.tools.schemas import ToolInput, ToolRunResult

SUPPORTED_INTENTS: frozenset[TicketIntent] = frozenset({"topup_offer"})

_DEFAULT_OFFER_TYPE: OfferType = "top_up"

_NO_OFFER_SUMMARY = (
    "I could not find an active offer record for this demo customer."
)
_ELIGIBLE_SUMMARY = (
    "You have a mock pre-approved top-up offer available in the demo records. "
    "This is only an eligibility display and does not create or disburse a loan."
)
_INELIGIBLE_SUMMARY = (
    "There is no active pre-approved top-up offer available for you in the demo "
    "records right now."
)
_LEAD_CREATED_SUMMARY = (
    "I have recorded your interest in this mock top-up offer. "
    "This is not a loan disbursement or final approval."
)
_LEAD_REUSED_SUMMARY = (
    "Your interest in this mock top-up offer is already on record. "
    "This is not a loan disbursement or final approval."
)


class OfferEligibilityTool(BaseMockTool):
    """Mock tool to read seeded offer eligibility and optionally record demo lead interest."""

    def __init__(
        self,
        customer_repository: CustomerRepository,
        offer_repository: OfferRepository,
        offer_service: OfferService | None = None,
        audit_hook: ToolAuditHook | None = None,
    ) -> None:
        super().__init__(audit_hook=audit_hook)
        self._customer_repository = customer_repository
        self._offer_repository = offer_repository
        self._offer_service = offer_service

    @property
    def tool_name(self) -> ToolName:
        return "OfferEligibilityTool"

    def validate_input(self, tool_input: ToolInput) -> None:
        if tool_input.intent not in SUPPORTED_INTENTS:
            raise ToolValidationError(
                f"OfferEligibilityTool does not support intent: {tool_input.intent}"
            )

    async def _run(self, tool_input: ToolInput) -> ToolRunResult:
        customer = await self._customer_repository.find_by_id(tool_input.customer_id)
        if customer is None:
            raise ToolExecutionError(
                "Customer record was not found for this demo profile.",
                code="not_found",
                retryable=False,
            )

        offers = await self._offer_repository.find_by_customer(tool_input.customer_id)
        offer = _select_offer(offers, parameters=tool_input.parameters)
        if offer is None:
            return ToolRunResult(
                data={},
                customer_safe_summary=_NO_OFFER_SUMMARY,
                action_taken="offer_record_not_found",
                escalation_required=False,
            )

        proceed = _parse_proceed(tool_input.parameters)
        offer, lead_recorded = await _maybe_record_lead(
            offer,
            proceed=proceed,
            offer_service=self._offer_service,
        )

        action_taken, summary = _resolve_action_and_summary(
            offer=offer,
            proceed=proceed,
            lead_recorded=lead_recorded,
        )
        return ToolRunResult(
            data=_build_safe_data(offer),
            customer_safe_summary=summary,
            action_taken=action_taken,
            escalation_required=False,
        )


def _select_offer(
    offers: list[OfferDocument],
    *,
    parameters: dict[str, Any],
) -> OfferDocument | None:
    offer_type = parameters.get("offer_type")
    if not isinstance(offer_type, str) or not offer_type.strip():
        offer_type = _DEFAULT_OFFER_TYPE
    else:
        offer_type = offer_type.strip()

    matches = [offer for offer in offers if offer.offer_type == offer_type]
    if not matches:
        return None

    return sorted(
        matches,
        key=lambda offer: (str(offer.created_at), offer.offer_id),
        reverse=True,
    )[0]


def _parse_proceed(parameters: dict[str, Any]) -> bool:
    value = parameters.get("proceed")
    if value is True:
        return True
    if isinstance(value, str) and value.strip().lower() in {"true", "1", "yes"}:
        return True
    if value == 1:
        return True
    return False


async def _maybe_record_lead(
    offer: OfferDocument,
    *,
    proceed: bool,
    offer_service: OfferService | None,
) -> tuple[OfferDocument, bool | None]:
    if not proceed or not offer.is_eligible or offer_service is None:
        return offer, None
    updated, created_new = await offer_service.record_mock_lead(offer.offer_id)
    return updated, created_new


def _resolve_action_and_summary(
    *,
    offer: OfferDocument,
    proceed: bool,
    lead_recorded: bool | None,
) -> tuple[str, str]:
    if proceed and offer.is_eligible and lead_recorded is not None:
        if lead_recorded:
            return "mock_offer_lead_created", _LEAD_CREATED_SUMMARY
        return "mock_offer_lead_created", _LEAD_REUSED_SUMMARY

    if offer.is_eligible:
        return "offer_eligibility_checked", _ELIGIBLE_SUMMARY

    if offer.non_eligibility_reason:
        return "offer_eligibility_checked", offer.non_eligibility_reason
    return "offer_eligibility_checked", _INELIGIBLE_SUMMARY


def _build_safe_data(offer: OfferDocument) -> dict[str, Any]:
    data: dict[str, Any] = {
        "offer_id": offer.offer_id,
        "offer_type": offer.offer_type,
        "is_eligible": offer.is_eligible,
        "lead_created": offer.lead_created,
    }
    if offer.is_eligible:
        if offer.approved_limit is not None:
            data["approved_limit"] = offer.approved_limit
        if offer.interest_rate is not None:
            data["interest_rate"] = offer.interest_rate
        if offer.tenure_options is not None:
            data["tenure_options"] = offer.tenure_options
        if offer.valid_until is not None:
            data["valid_until"] = str(offer.valid_until)
    elif offer.non_eligibility_reason is not None:
        data["non_eligibility_reason"] = offer.non_eligibility_reason
    return data
