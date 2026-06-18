"""LangGraph risk classifier node implementation (T-054)."""

from __future__ import annotations

import logging
from typing import Any

from app.agent.constants import NODE_RISK_CLASSIFIER
from app.agent.exceptions import RiskClassifierValidationError
from app.agent.nodes.base import NodeCallable
from app.agent.risk.intent_risk_policy import classify_intent_risk
from app.agent.state import AgentState, RiskRoutingState

logger = logging.getLogger("samadhan.agent")


class RiskClassifierNode:
    """Assign deterministic risk level and priority from classified intent."""

    async def __call__(self, state: AgentState) -> dict[str, Any]:
        if state.intent_classification is None:
            raise RiskClassifierValidationError(
                "intent classification is required before risk classification",
            )

        intent_state = state.intent_classification
        result = classify_intent_risk(
            intent_state.intent,
            confidence=intent_state.confidence,
            source=intent_state.source,
        )

        logger.info(
            "risk classified workflow_id=%s intent=%s risk=%s priority=%s policy=%s",
            state.workflow_id,
            intent_state.intent,
            result.risk_level,
            result.priority,
            result.policy_version,
        )

        return {
            "risk_routing": RiskRoutingState(
                risk_level=result.risk_level,
                priority=result.priority,
                risk_reason=result.risk_reason,
            ),
        }


def build_risk_classifier_node() -> NodeCallable:
    """Return a risk classifier node callable."""
    node = RiskClassifierNode()

    async def risk_classifier_node(state: AgentState) -> dict[str, Any]:
        return await node(state)

    return risk_classifier_node


# Registry stub; build_default_registry replaces with build_risk_classifier_node().
from app.agent.nodes.base import passthrough_node as risk_classifier_node  # noqa: E402

__all__ = ["RiskClassifierNode", "build_risk_classifier_node", "risk_classifier_node"]
