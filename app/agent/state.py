"""LangGraph agent workflow state schema (T-050).

Minimum invocation contract:
    workflow_id, user_id, customer_message

Downstream node slices remain optional until populated by T-052+ nodes.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.agent.constants import (
    ClassificationSource,
    GuardrailDecision,
    ToolExecutionStatus,
    WORKFLOW_ID_PATTERN,
    WorkflowErrorCode,
)
from app.agent.resolution.resolution_types import (
    CustomerAction,
    CustomerResponseType,
    SystemAction,
)
from app.audit.id_generation import AUDIT_ID_PATTERN
from app.audit.models import CUSTOMER_ID_PATTERN, USER_ID_PATTERN
from app.lending.models import LOAN_ID_PATTERN
from app.messages.id_generation import MESSAGE_ID_PATTERN
from app.rag.schemas import RetrievalResult
from app.service_requests.id_generation import SERVICE_REQUEST_ID_PATTERN
from app.tickets.constants import (
    Priority,
    RiskLevel,
    TicketClass,
    TicketIntent,
    TicketStatus,
)
from app.tickets.id_generation import TICKET_ID_PATTERN
from app.tickets.risk_rules import validate_risk_priority_rules
from app.tools.constants import ToolName
from app.tools.schemas import ToolInput, ToolOutput


class CustomerContextSnapshot(BaseModel):
    """Lightweight customer profile for workflow nodes (no raw PAN/mobile/Aadhaar)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: str = Field(..., pattern=CUSTOMER_ID_PATTERN)
    display_name: str | None = None
    scenario_label: str | None = None
    loan_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("loan_ids")
    @classmethod
    def validate_loan_ids(cls, value: list[str]) -> list[str]:
        import re

        pattern = re.compile(LOAN_ID_PATTERN)
        for loan_id in value:
            if not pattern.match(loan_id):
                raise ValueError(f"invalid loan_id format: {loan_id}")
        return value


class IntentClassificationState(BaseModel):
    """Intent classifier node output."""

    model_config = ConfigDict(str_strip_whitespace=True)

    intent: TicketIntent
    confidence: float = Field(..., ge=0.0, le=1.0)
    source: ClassificationSource
    reason: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class RiskRoutingState(BaseModel):
    """Risk classifier and ticket router node outputs."""

    model_config = ConfigDict(str_strip_whitespace=True)

    risk_level: RiskLevel
    priority: Priority
    risk_reason: str | None = None
    ticket_class: TicketClass | None = None
    routing_reason: str | None = None


class RetrievalState(BaseModel):
    """Retrieval node output."""

    model_config = ConfigDict(str_strip_whitespace=True)

    retrieval_required: bool | None = None
    result: RetrievalResult | None = None
    source_policy_ids: list[str] = Field(default_factory=list)


class GuardrailState(BaseModel):
    """Guardrail node decision."""

    model_config = ConfigDict(str_strip_whitespace=True)

    decision: GuardrailDecision
    reason: str | None = Field(default=None, max_length=200)
    allowed_actions: list[str] = Field(default_factory=list)
    escalation_required: bool = False
    approved_step_indexes: list[int] = Field(default_factory=list)
    blocked_step_indexes: list[int] = Field(default_factory=list)
    conditional_step_indexes: list[int] = Field(default_factory=list)
    policy_version: str | None = None


class ToolStepState(BaseModel):
    """One ordered tool in a multi-tool workflow."""

    model_config = ConfigDict(str_strip_whitespace=True)

    tool_name: ToolName
    tool_input: ToolInput | None = None
    status: ToolExecutionStatus = "pending"
    planner_condition: str | None = Field(default=None, max_length=200)
    tool_output: ToolOutput | None = None
    audit_id: str | None = Field(default=None, pattern=AUDIT_ID_PATTERN)


class ResolutionPlan(BaseModel):
    """Structured resolution plan from resolution planner node."""

    model_config = ConfigDict(str_strip_whitespace=True)

    intent: TicketIntent
    risk_level: RiskLevel
    priority: Priority
    ticket_class: TicketClass
    customer_action: CustomerAction
    system_action: SystemAction
    tool_actions: list[str] = Field(default_factory=list)
    escalation_required: bool
    escalation_reason: str | None = Field(default=None, max_length=200)
    customer_response_type: CustomerResponseType
    service_request_id: str | None = Field(default=None, pattern=SERVICE_REQUEST_ID_PATTERN)
    ticket_status: TicketStatus | None = None


class TicketUpdateState(BaseModel):
    """Ticket update node result."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ticket_status: TicketStatus | None = None
    service_request_id: str | None = Field(default=None, pattern=SERVICE_REQUEST_ID_PATTERN)
    update_summary: str | None = Field(default=None, max_length=200)
    document_path: str | None = None
    ai_message_id: str | None = Field(default=None, pattern=MESSAGE_ID_PATTERN)
    previous_ticket_class: TicketClass | None = None
    persisted_ticket_class: TicketClass | None = None
    previous_status: TicketStatus | None = None
    human_review_queued: bool = False
    idempotent_replay: bool = False


class WorkflowAuditState(BaseModel):
    """Workflow audit node result (T-063)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    workflow_audit_id: str | None = Field(default=None, pattern=AUDIT_ID_PATTERN)
    event_type: Literal["workflow_completed"] = "workflow_completed"
    linked_tool_audit_ids: list[str] = Field(default_factory=list)
    langsmith_trace_id: str | None = None
    workflow_status: Literal["completed"] = "completed"
    idempotent_replay: bool = False


class CustomerResponseMetadata(BaseModel):
    """Response generation metadata for audit and evaluation (T-061)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    generation_source: Literal["llm", "deterministic_template"]
    prompt_version: str
    safety_status: Literal["passed", "fallback_used"]
    referenced_ticket_id: str | None = Field(default=None, pattern=TICKET_ID_PATTERN)
    referenced_service_request_ids: list[str] = Field(default_factory=list)
    referenced_source_ids: list[str] = Field(default_factory=list)
    fallback_reason: str | None = Field(default=None, max_length=200)
    mock_disclaimer_included: bool = False


class WorkflowError(BaseModel):
    """Controlled workflow error (safe for logging; no stack traces or secrets)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    code: WorkflowErrorCode
    message: str = Field(..., min_length=1)
    node: str | None = None
    recoverable: bool = False


class AgentState(BaseModel):
    """Canonical shared state passed between LangGraph workflow nodes."""

    model_config = ConfigDict(str_strip_whitespace=True)

    # Workflow identity and request context
    workflow_id: str = Field(..., pattern=WORKFLOW_ID_PATTERN)
    user_id: str = Field(..., pattern=USER_ID_PATTERN)
    customer_message: str = Field(..., min_length=1)
    customer_id: str | None = Field(default=None, pattern=CUSTOMER_ID_PATTERN)
    session_id: str | None = None
    ticket_id: str | None = Field(default=None, pattern=TICKET_ID_PATTERN)
    message_id: str | None = Field(default=None, pattern=MESSAGE_ID_PATTERN)
    normalized_message: str | None = None
    customer_context: CustomerContextSnapshot | None = None
    persisted_ticket_class: TicketClass | None = None

    # Intent classification
    intent_classification: IntentClassificationState | None = None

    # Risk and routing
    risk_routing: RiskRoutingState | None = None

    # Retrieval
    retrieval: RetrievalState | None = None

    # Tool planning and execution
    tool_plan_reason: str | None = None
    tool_steps: list[ToolStepState] = Field(default_factory=list)
    guardrail: GuardrailState | None = None

    # Resolution and response
    resolution_plan: ResolutionPlan | None = None
    customer_response: str | None = None
    customer_response_metadata: CustomerResponseMetadata | None = None
    ticket_update: TicketUpdateState | None = None
    workflow_audit: WorkflowAuditState | None = None

    # Audit and tracing
    audit_event_ids: list[str] = Field(default_factory=list)
    langsmith_trace_id: str | None = None
    workflow_errors: list[WorkflowError] = Field(default_factory=list)

    @field_validator("session_id", "normalized_message", "customer_response", "tool_plan_reason")
    @classmethod
    def validate_non_blank_optional_strings(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("field must be null or non-empty")
        return value

    @field_validator("audit_event_ids")
    @classmethod
    def validate_audit_event_ids(cls, value: list[str]) -> list[str]:
        import re

        pattern = re.compile(AUDIT_ID_PATTERN)
        for audit_id in value:
            if not pattern.match(audit_id):
                raise ValueError(f"invalid audit_id format: {audit_id}")
        return value

    @model_validator(mode="after")
    def validate_risk_routing_consistency(self) -> AgentState:
        if (
            self.intent_classification is None
            or self.risk_routing is None
            or self.risk_routing.ticket_class is None
        ):
            return self
        try:
            validate_risk_priority_rules(
                intent=self.intent_classification.intent,
                ticket_class=self.risk_routing.ticket_class,
                risk_level=self.risk_routing.risk_level,
                priority=self.risk_routing.priority,
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        return self

    @property
    def primary_tool(self) -> ToolName | None:
        if not self.tool_steps:
            return None
        return self.tool_steps[0].tool_name

    @property
    def latest_tool_output(self) -> ToolOutput | None:
        for step in reversed(self.tool_steps):
            if step.tool_output is not None:
                return step.tool_output
        return None

    @classmethod
    def initial(
        cls,
        workflow_id: str,
        user_id: str,
        customer_message: str,
    ) -> AgentState:
        """Build minimum valid state for workflow invocation."""
        return cls(
            workflow_id=workflow_id,
            user_id=user_id,
            customer_message=customer_message,
        )

    def to_graph_dict(self) -> dict[str, Any]:
        """Serialize for LangGraph dict-based state (T-051)."""
        return self.model_dump(mode="json")

    @classmethod
    def from_graph_dict(cls, data: dict[str, Any]) -> AgentState:
        """Restore validated state from LangGraph dict."""
        return cls.model_validate(data)
