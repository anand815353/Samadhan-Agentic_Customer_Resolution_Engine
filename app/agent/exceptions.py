"""Agent workflow exceptions."""

from app.core.exceptions import AppError


class AgentWorkflowError(AppError):
    """Base error for agent workflow invocation."""


class AgentWorkflowValidationError(AgentWorkflowError):
    """Raised when workflow input state fails validation."""


class AgentWorkflowExecutionError(AgentWorkflowError):
    """Raised when graph execution fails in a controlled way."""


class IntakeError(AgentWorkflowError):
    """Base error for intake node validation and persistence."""


class IntakeAccessDeniedError(IntakeError):
    """Raised when intake rejects unauthorized or cross-customer access."""


class IntakeValidationError(IntakeError):
    """Raised when intake input or linkage validation fails."""


class IntakePersistenceError(IntakeError):
    """Raised when intake cannot persist the customer message."""


class RiskClassifierError(AgentWorkflowError):
    """Base error for risk classifier node validation."""


class RiskClassifierValidationError(RiskClassifierError):
    """Raised when risk classification input validation fails."""


class TicketRouterError(AgentWorkflowError):
    """Base error for ticket router node validation."""


class TicketRouterValidationError(TicketRouterError):
    """Raised when ticket routing input validation fails."""


class RetrievalError(AgentWorkflowError):
    """Base error for retrieval node validation."""


class RetrievalValidationError(RetrievalError):
    """Raised when retrieval input validation fails."""


class ToolPlannerError(AgentWorkflowError):
    """Base error for tool planner node validation."""


class ToolPlannerValidationError(ToolPlannerError):
    """Raised when tool planning input validation fails."""


class GuardrailError(AgentWorkflowError):
    """Base error for guardrail node validation."""


class GuardrailValidationError(GuardrailError):
    """Raised when guardrail input validation fails."""


class ToolExecutionError(AgentWorkflowError):
    """Base error for tool execution node validation."""


class ToolExecutionValidationError(ToolExecutionError):
    """Raised when tool execution input or authorization validation fails."""


class ResolutionPlannerError(AgentWorkflowError):
    """Base error for resolution planner node validation."""


class ResolutionPlannerValidationError(ResolutionPlannerError):
    """Raised when resolution planning input validation fails."""


class ResponseError(AgentWorkflowError):
    """Base error for response node validation."""


class ResponseValidationError(ResponseError):
    """Raised when response generation input validation fails."""


class TicketUpdateError(AgentWorkflowError):
    """Base error for ticket update node validation and persistence."""


class TicketUpdateValidationError(TicketUpdateError):
    """Raised when ticket update input validation fails."""


class TicketUpdatePersistenceError(TicketUpdateError):
    """Raised when ticket update persistence fails."""


class AuditNodeError(AgentWorkflowError):
    """Base error for audit node validation and persistence."""


class AuditNodeValidationError(AuditNodeError):
    """Raised when audit node input validation fails."""


class AuditNodePersistenceError(AuditNodeError):
    """Raised when workflow audit persistence fails."""
