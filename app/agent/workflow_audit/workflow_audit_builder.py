"""Build bounded AuditEventCreate payloads from final workflow state."""

from __future__ import annotations

from typing import Any

from app.agent.exceptions import AuditNodeValidationError
from app.agent.state import AgentState
from app.agent.workflow_audit.summary_allowlist import (
    MAX_POLICY_SOURCE_IDS,
    MAX_SUMMARY_FIELD_LENGTH,
    WORKFLOW_COMPLETED_EVENT,
)
from app.audit.schemas import AuditEventCreate
from app.common.masking import mask_sensitive_data


def build_workflow_audit_event(state: AgentState, *, linked_tool_audit_ids: list[str]) -> AuditEventCreate:
    """Construct a consolidated workflow_completed audit create command."""
    _validate_prerequisites(state)

    ticket_update = state.ticket_update
    assert ticket_update is not None
    plan = state.resolution_plan
    assert plan is not None
    response_meta = state.customer_response_metadata
    assert response_meta is not None

    policy_ids = _approved_policy_ids(state)
    trace = state.langsmith_trace_id

    summary = ticket_update.update_summary or "Workflow completed."
    if len(summary) > MAX_SUMMARY_FIELD_LENGTH:
        summary = summary[:MAX_SUMMARY_FIELD_LENGTH]

    service_request_id = ticket_update.service_request_id or plan.service_request_id

    return AuditEventCreate(
        event_type=WORKFLOW_COMPLETED_EVENT,
        workflow_id=state.workflow_id,
        ticket_id=state.ticket_id,
        customer_id=state.customer_id,
        user_id=state.user_id,
        session_id=state.session_id,
        message_id=ticket_update.ai_message_id,
        intent=plan.intent,
        risk_level=plan.risk_level,
        priority=plan.priority,
        confidence=state.intent_classification.confidence if state.intent_classification else None,
        escalation_required=plan.escalation_required,
        retrieved_policy_ids=policy_ids,
        service_request_id=service_request_id,
        langsmith_trace_id=trace,
        action_taken="workflow_completed",
        customer_safe_summary=summary,
        internal_summary=f"workflow {state.workflow_id} completed",
        created_by="system",
        raw_internal_trace=_build_internal_trace(state, linked_tool_audit_ids=linked_tool_audit_ids),
    )


def workflow_audit_fingerprint(state: AgentState, *, linked_tool_audit_ids: list[str]) -> str:
    """Stable fingerprint for idempotent replay detection."""
    ticket_update = state.ticket_update
    assert ticket_update is not None
    parts = [
        state.workflow_id,
        state.ticket_id or "",
        ticket_update.ai_message_id or "",
        ticket_update.ticket_status or "",
        ",".join(linked_tool_audit_ids),
    ]
    return "|".join(parts)


def _validate_prerequisites(state: AgentState) -> None:
    if not state.workflow_id:
        raise AuditNodeValidationError("workflow_id is required")
    if not state.ticket_id:
        raise AuditNodeValidationError("ticket_id is required")
    if not state.customer_id:
        raise AuditNodeValidationError("customer_id is required")
    if not state.message_id:
        raise AuditNodeValidationError("customer message_id is required")
    if not state.customer_response or not state.customer_response.strip():
        raise AuditNodeValidationError("customer_response is required")
    if state.resolution_plan is None:
        raise AuditNodeValidationError("resolution_plan is required")
    if state.customer_response_metadata is None:
        raise AuditNodeValidationError("customer_response_metadata is required")
    if state.ticket_update is None:
        raise AuditNodeValidationError("ticket_update is required")
    if not state.ticket_update.ai_message_id:
        raise AuditNodeValidationError("ticket_update.ai_message_id is required")
    if state.ticket_update.ticket_status is None:
        raise AuditNodeValidationError("ticket_update.ticket_status is required")


def _approved_policy_ids(state: AgentState) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    sources: list[str] = []
    if state.retrieval is not None:
        sources.extend(state.retrieval.source_policy_ids)
    if state.customer_response_metadata is not None:
        sources.extend(state.customer_response_metadata.referenced_source_ids)
    for source_id in sources:
        if not source_id or source_id in seen:
            continue
        if not _looks_like_policy_doc_id(source_id):
            continue
        seen.add(source_id)
        ordered.append(source_id)
        if len(ordered) >= MAX_POLICY_SOURCE_IDS:
            break
    return ordered


def _looks_like_policy_doc_id(source_id: str) -> bool:
    return source_id.startswith("POL-") or source_id.startswith("DOC-")


def _build_internal_trace(
    state: AgentState,
    *,
    linked_tool_audit_ids: list[str],
) -> dict[str, Any]:
    plan = state.resolution_plan
    ticket_update = state.ticket_update
    assert plan is not None and ticket_update is not None

    retrieval = state.retrieval
    guardrail = state.guardrail
    response_meta = state.customer_response_metadata
    intent_cls = state.intent_classification
    risk = state.risk_routing

    trace: dict[str, Any] = {
        "workflow_status": "completed",
        "customer_message_id": state.message_id,
        "classification": {
            "intent": plan.intent,
            "confidence": intent_cls.confidence if intent_cls else None,
            "source": intent_cls.source if intent_cls else None,
            "reason": _bound(intent_cls.reason if intent_cls else None),
        },
        "risk": {
            "risk_level": plan.risk_level,
            "priority": plan.priority,
            "risk_reason": _bound(risk.risk_reason if risk else None),
        },
        "routing": {
            "ticket_class": plan.ticket_class,
            "routing_reason": _bound(risk.routing_reason if risk else None),
        },
        "retrieval": {
            "required": retrieval.retrieval_required if retrieval else None,
            "status": (
                "unavailable"
                if retrieval and retrieval.result and retrieval.result.unavailable
                else (
                    "no_results"
                    if retrieval and retrieval.result and retrieval.result.total_results == 0
                    else "ok"
                    if retrieval and retrieval.result
                    else None
                )
            ),
            "source_policy_ids": list(
                retrieval.source_policy_ids if retrieval else [],
            )[:MAX_POLICY_SOURCE_IDS],
            "result_count": len(retrieval.source_policy_ids) if retrieval else 0,
        },
        "tool_plan": [
            {
                "tool_name": step.tool_name,
                "planner_condition": _bound(step.planner_condition),
            }
            for step in state.tool_steps
        ],
        "guardrail": {
            "decision": guardrail.decision if guardrail else None,
            "reason": _bound(guardrail.reason if guardrail else None),
            "escalation_required": guardrail.escalation_required if guardrail else None,
            "approved_indexes": list(guardrail.approved_step_indexes) if guardrail else [],
            "blocked_indexes": list(guardrail.blocked_step_indexes) if guardrail else [],
        },
        "tool_execution": [
            {
                "tool_name": step.tool_name,
                "status": step.status,
                "audit_id": step.audit_id,
                "action_taken": _bound(
                    step.tool_output.action_taken if step.tool_output else None,
                ),
                "escalation_required": (
                    step.tool_output.escalation_required if step.tool_output else None
                ),
            }
            for step in state.tool_steps
        ],
        "resolution": {
            "system_action": plan.system_action,
            "customer_action": plan.customer_action,
            "ticket_status": plan.ticket_status,
            "escalation_reason": _bound(plan.escalation_reason),
        },
        "response": {
            "generation_source": response_meta.generation_source if response_meta else None,
            "safety_status": response_meta.safety_status if response_meta else None,
            "prompt_version": response_meta.prompt_version if response_meta else None,
            "fallback_reason": _bound(response_meta.fallback_reason if response_meta else None),
            "response_length": len(state.customer_response or ""),
            "mock_disclaimer_included": (
                response_meta.mock_disclaimer_included if response_meta else False
            ),
        },
        "persistence": {
            "ticket_status": ticket_update.ticket_status,
            "persisted_ticket_class": ticket_update.persisted_ticket_class,
            "human_review_queued": ticket_update.human_review_queued,
            "idempotent_replay": ticket_update.idempotent_replay,
            "ai_message_id": ticket_update.ai_message_id,
            "service_request_id": ticket_update.service_request_id,
        },
        "linked_tool_audit_ids": list(linked_tool_audit_ids),
        "idempotency_fingerprint": workflow_audit_fingerprint(
            state,
            linked_tool_audit_ids=linked_tool_audit_ids,
        ),
    }
    masked = mask_sensitive_data(trace)
    if not isinstance(masked, dict):
        return {"workflow_status": "completed"}
    return masked


def _bound(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    return text[:MAX_SUMMARY_FIELD_LENGTH]
