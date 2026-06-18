"""Agent workflow constants aligned with AGENT_WORKFLOW and evaluation seed."""

from typing import Literal

WORKFLOW_ID_PATTERN = r"^WF-\d{4}-\d{4}$"

GuardrailDecision = Literal[
    "allow",
    "allow_with_audit",
    "escalate",
    "ask_follow_up",
    "block",
]

ClassificationSource = Literal["rule", "llm", "hybrid"]

ToolExecutionStatus = Literal["pending", "running", "completed", "failed", "skipped"]

WorkflowErrorCode = Literal[
    "llm_unavailable",
    "retrieval_unavailable",
    "tool_failed",
    "validation_failed",
    "missing_context",
    "db_error",
    "unknown",
]

ALL_GUARDRAIL_DECISIONS: tuple[GuardrailDecision, ...] = (
    "allow",
    "allow_with_audit",
    "escalate",
    "ask_follow_up",
    "block",
)

ALL_CLASSIFICATION_SOURCES: tuple[ClassificationSource, ...] = ("rule", "llm", "hybrid")

ALL_TOOL_EXECUTION_STATUSES: tuple[ToolExecutionStatus, ...] = (
    "pending",
    "running",
    "completed",
    "failed",
    "skipped",
)

ALL_WORKFLOW_ERROR_CODES: tuple[WorkflowErrorCode, ...] = (
    "llm_unavailable",
    "retrieval_unavailable",
    "tool_failed",
    "validation_failed",
    "missing_context",
    "db_error",
    "unknown",
)

NODE_INTAKE = "intake"
NODE_INTENT_CLASSIFIER = "intent_classifier"
NODE_RISK_CLASSIFIER = "risk_classifier"
NODE_TICKET_ROUTER = "ticket_router"
NODE_RETRIEVAL = "retrieval"
NODE_TOOL_PLANNER = "tool_planner"
NODE_GUARDRAIL = "guardrail"
NODE_TOOL_EXECUTION = "tool_execution"
NODE_RESOLUTION_PLANNER = "resolution_planner"
NODE_RESPONSE = "response"
NODE_TICKET_UPDATE = "ticket_update"
NODE_AUDIT = "audit"

ORDERED_WORKFLOW_NODES: tuple[str, ...] = (
    NODE_INTAKE,
    NODE_INTENT_CLASSIFIER,
    NODE_RISK_CLASSIFIER,
    NODE_TICKET_ROUTER,
    NODE_RETRIEVAL,
    NODE_TOOL_PLANNER,
    NODE_GUARDRAIL,
    NODE_TOOL_EXECUTION,
    NODE_RESOLUTION_PLANNER,
    NODE_RESPONSE,
    NODE_TICKET_UPDATE,
    NODE_AUDIT,
)

ALL_WORKFLOW_NODES: tuple[str, ...] = ORDERED_WORKFLOW_NODES
