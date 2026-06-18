"""LangGraph ticket router node implementation (T-055)."""

from __future__ import annotations

import logging
from typing import Any

from app.agent.exceptions import TicketRouterValidationError
from app.agent.nodes.base import NodeCallable
from app.agent.routing.intent_ticket_routing_policy import route_ticket
from app.agent.state import AgentState, RiskRoutingState
from app.tickets.constants import ALL_TICKET_INTENTS

logger = logging.getLogger("samadhan.agent")

_ALL_RISK_LEVELS: frozenset[str] = frozenset({"low", "medium", "high", "critical"})
_ALL_PRIORITIES: frozenset[str] = frozenset({"low", "medium", "high", "critical"})


class TicketRouterNode:
    """Assign deterministic ticket class from classified intent and risk."""

    async def __call__(self, state: AgentState) -> dict[str, Any]:
        if state.ticket_id is None:
            raise TicketRouterValidationError(
                "ticket_id is required before ticket routing",
            )
        if state.intent_classification is None:
            raise TicketRouterValidationError(
                "intent classification is required before ticket routing",
            )
        if state.risk_routing is None:
            raise TicketRouterValidationError(
                "risk routing is required before ticket routing",
            )

        intent_state = state.intent_classification
        risk_state = state.risk_routing

        intent = intent_state.intent
        risk_level = risk_state.risk_level
        priority = risk_state.priority

        if intent not in ALL_TICKET_INTENTS:
            raise TicketRouterValidationError("unsupported intent for ticket routing")
        if risk_level not in _ALL_RISK_LEVELS:
            raise TicketRouterValidationError("unsupported risk level for ticket routing")
        if priority not in _ALL_PRIORITIES:
            raise TicketRouterValidationError("unsupported priority for ticket routing")

        result = route_ticket(
            intent,  # type: ignore[arg-type]
            risk_level=risk_level,  # type: ignore[arg-type]
            priority=priority,  # type: ignore[arg-type]
            confidence=intent_state.confidence,
            source=intent_state.source,
            persisted_ticket_class=state.persisted_ticket_class,
        )

        logger.info(
            "ticket routed workflow_id=%s ticket_id=%s intent=%s risk=%s priority=%s class=%s policy=%s",
            state.workflow_id,
            state.ticket_id,
            intent,
            risk_level,
            priority,
            result.ticket_class,
            result.policy_version,
        )

        return {
            "risk_routing": RiskRoutingState(
                risk_level=risk_state.risk_level,
                priority=risk_state.priority,
                risk_reason=risk_state.risk_reason,
                ticket_class=result.ticket_class,
                routing_reason=result.routing_reason,
            ),
        }


def build_ticket_router_node() -> NodeCallable:
    """Return a ticket router node callable."""
    node = TicketRouterNode()

    async def ticket_router_node(state: AgentState) -> dict[str, Any]:
        return await node(state)

    return ticket_router_node


# Registry stub; build_default_registry replaces with build_ticket_router_node().
from app.agent.nodes.base import passthrough_node as ticket_router_node  # noqa: E402

__all__ = ["TicketRouterNode", "build_ticket_router_node", "ticket_router_node"]
