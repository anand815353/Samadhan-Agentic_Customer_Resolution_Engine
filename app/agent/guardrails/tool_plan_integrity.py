"""Tool-plan integrity validation for guardrail evaluation (T-058)."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.planning.intent_tool_policy import plan_tools
from app.agent.state import AgentState
from app.tickets.constants import TicketIntent
from app.tools.constants import ALL_TOOL_NAMES, FORBIDDEN_ACTION_TOKENS, ToolName
from app.tools.bureau_reporting_tool import SUPPORTED_INTENTS as BUREAU_SUPPORTED
from app.tools.document_generation_tool import SUPPORTED_INTENTS as DOCGEN_SUPPORTED
from app.tools.fraud_security_tool import SUPPORTED_INTENTS as FRAUD_SUPPORTED
from app.tools.kyc_document_tool import SUPPORTED_INTENTS as KYC_SUPPORTED
from app.tools.loan_status_tool import SUPPORTED_INTENTS as LOAN_STATUS_SUPPORTED
from app.tools.offer_eligibility_tool import SUPPORTED_INTENTS as OFFER_SUPPORTED
from app.tools.policy_rag_tool import SUPPORTED_INTENTS as POLICY_RAG_SUPPORTED
from app.tools.rejection_reason_tool import SUPPORTED_INTENTS as REJECTION_SUPPORTED
from app.tools.repayment_tool import SUPPORTED_INTENTS as REPAYMENT_SUPPORTED
from app.tools.rm_redirect_tool import SUPPORTED_INTENTS as RM_SUPPORTED
from app.tools.transaction_tool import SUPPORTED_INTENTS as TRANSACTION_SUPPORTED

_ALLOWED_DOCUMENT_TYPES_BY_INTENT: dict[TicketIntent, frozenset[str]] = {
    "loan_statement_request": frozenset({"loan_statement"}),
    "noc_closure_certificate": frozenset({"noc", "noc_request"}),
    "bureau_reporting_issue": frozenset({"closure_letter", "bureau_closure_letter"}),
}

_TOOL_SUPPORTED_INTENTS: dict[ToolName, frozenset[TicketIntent]] = {
    "LoanStatusTool": LOAN_STATUS_SUPPORTED,
    "KYCDocumentTool": KYC_SUPPORTED,
    "RejectionReasonTool": REJECTION_SUPPORTED,
    "RepaymentTool": REPAYMENT_SUPPORTED,
    "TransactionTool": TRANSACTION_SUPPORTED,
    "FraudSecurityTool": FRAUD_SUPPORTED,
    "PolicyRAGTool": POLICY_RAG_SUPPORTED,
    "RMRedirectTool": RM_SUPPORTED,
    "DocumentGenerationTool": DOCGEN_SUPPORTED,
    "BureauReportingTool": BUREAU_SUPPORTED,
    "OfferEligibilityTool": OFFER_SUPPORTED,
}

_PROHIBITED_PARAMETER_KEYS: frozenset[str] = frozenset(
    {
        "dispute_escalation",
        "bureau_updated",
        "refund_completed",
        "reversal_completed",
        "account_frozen",
        "kyc_approved",
        "disburse",
        "disbursement",
        "approve_refund",
        "complete_refund",
        "complete_reversal",
        "freeze_account",
        "permanent_block",
    }
)

_TOPUP_CONSENT_PHRASES: tuple[str, ...] = (
    "proceed",
    "yes apply",
    "accept offer",
    "want to apply",
    "apply for",
)


@dataclass(frozen=True)
class PlanIntegrityResult:
    """Integrity scan outcome before authorization."""

    prohibited_step_indexes: tuple[int, ...] = ()
    plan_replay_valid: bool = True


def _normalize_text(value: object) -> str:
    if not isinstance(value, str):
        return str(value).lower()
    return value.lower().replace("-", "_")


def _parameters_contain_forbidden_token(parameters: dict[object, object]) -> bool:
    serialized = _normalize_text(str(parameters))
    return any(token in serialized for token in FORBIDDEN_ACTION_TOKENS)


def _parameters_contain_prohibited_key(parameters: dict[object, object]) -> bool:
    for key in parameters:
        if str(key).lower() in _PROHIBITED_PARAMETER_KEYS:
            return True
    return False


def _topup_proceed_without_consent(
    intent: TicketIntent,
    parameters: dict[object, object],
    message: str,
) -> bool:
    if intent != "topup_offer":
        return False
    proceed = parameters.get("proceed")
    if proceed not in (True, "true", "1", "yes"):
        return False
    normalized = message.lower()
    return not any(phrase in normalized for phrase in _TOPUP_CONSENT_PHRASES)


def _document_type_invalid(intent: TicketIntent, parameters: dict[object, object]) -> bool:
    if intent not in _ALLOWED_DOCUMENT_TYPES_BY_INTENT:
        return False
    document_type = parameters.get("document_type")
    if document_type is None:
        return False
    if not isinstance(document_type, str):
        return True
    allowed = _ALLOWED_DOCUMENT_TYPES_BY_INTENT[intent]
    return document_type.strip() not in allowed


def _path_like_value(parameters: dict[object, object]) -> bool:
    for value in parameters.values():
        if not isinstance(value, str):
            continue
        if ".." in value or value.startswith(("/", "\\")):
            return True
    return False


def validate_tool_plan_prerequisites(state: AgentState) -> None:
    """Raise ValueError when required upstream state is missing."""
    if state.customer_id is None:
        raise ValueError("customer_id is required before guardrail evaluation")
    if state.ticket_id is None:
        raise ValueError("ticket_id is required before guardrail evaluation")
    if not state.workflow_id:
        raise ValueError("workflow_id is required before guardrail evaluation")
    if state.intent_classification is None:
        raise ValueError("intent classification is required before guardrail evaluation")
    if state.risk_routing is None:
        raise ValueError("risk routing is required before guardrail evaluation")
    if state.risk_routing.ticket_class is None:
        raise ValueError("ticket class is required before guardrail evaluation")


def _validate_step_identity(state: AgentState, index: int) -> None:
    step = state.tool_steps[index]
    if step.tool_input is None:
        raise ValueError(f"tool step {index} is missing structured tool input")
    tool_input = step.tool_input
    if tool_input.customer_id != state.customer_id:
        raise ValueError("tool input customer_id does not match workflow state")
    if tool_input.ticket_id != state.ticket_id:
        raise ValueError("tool input ticket_id does not match workflow state")
    if tool_input.request_id != state.workflow_id:
        raise ValueError("tool input request_id does not match workflow state")
    if tool_input.intent != state.intent_classification.intent:
        raise ValueError("tool input intent does not match classified intent")
    if tool_input.actor != "system":
        raise ValueError("tool input actor must be system for planned workflow steps")


def validate_plan_replay(state: AgentState) -> None:
    """Ensure stored tool plan matches deterministic replay from T-057 policy."""
    expected = plan_tools(state)
    if len(state.tool_steps) != len(expected.steps):
        raise ValueError("tool plan does not match policy replay length")
    for index, (stored, policy_step) in enumerate(zip(state.tool_steps, expected.steps, strict=True)):
        if stored.tool_name != policy_step.tool_name:
            raise ValueError(f"tool plan step {index} name does not match policy replay")
        if stored.planner_condition != policy_step.planner_condition:
            raise ValueError(f"tool plan step {index} condition does not match policy replay")


def scan_tool_plan_integrity(state: AgentState) -> PlanIntegrityResult:
    """Validate identity, registry, intent support, and prohibited parameters."""
    intent = state.intent_classification.intent  # type: ignore[union-attr]
    message = (state.normalized_message or state.customer_message).strip()
    prohibited: list[int] = []

    validate_plan_replay(state)

    for index, step in enumerate(state.tool_steps):
        _validate_step_identity(state, index)
        if step.tool_name not in ALL_TOOL_NAMES:
            raise ValueError(f"unregistered tool at step {index}")
        supported = _TOOL_SUPPORTED_INTENTS.get(step.tool_name)
        if supported is None or intent not in supported:
            raise ValueError(f"tool {step.tool_name} does not support intent {intent}")

        assert step.tool_input is not None
        parameters = step.tool_input.parameters

        if _parameters_contain_forbidden_token(parameters):
            prohibited.append(index)
            continue
        if _parameters_contain_prohibited_key(parameters):
            prohibited.append(index)
            continue
        if _topup_proceed_without_consent(intent, parameters, message):
            prohibited.append(index)
            continue
        if step.tool_name == "DocumentGenerationTool" and _document_type_invalid(intent, parameters):
            prohibited.append(index)
            continue
        if _path_like_value(parameters):
            prohibited.append(index)
            continue
        if parameters.get("dispute_escalation") is True:
            prohibited.append(index)

    return PlanIntegrityResult(prohibited_step_indexes=tuple(prohibited))
