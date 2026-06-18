"""Dependency bundle for the agent tool execution node (T-059)."""

from __future__ import annotations

from dataclasses import dataclass

from app.audit.repositories import InMemoryAuditLogRepository
from app.audit.services import AuditService
from app.bureau.models import BureauReportingLogDocument
from app.bureau.repositories import InMemoryBureauReportingLogRepository
from app.core.config import Settings, get_settings
from app.customers.models import CustomerDocument
from app.customers.repositories import InMemoryCustomerRepository
from app.fraud_cases.models import FraudCaseDocument
from app.fraud_cases.repositories import InMemoryFraudCaseRepository
from app.fraud_cases.services import FraudCaseService
from app.kyc.models import KycDocumentDocument
from app.kyc.repositories import InMemoryKycDocumentRepository
from app.lending.models import LoanApplicationDocument, LoanDocument
from app.lending.repositories import InMemoryLoanApplicationRepository, InMemoryLoanRepository
from app.offers.models import OfferDocument
from app.offers.repositories import InMemoryOfferRepository
from app.offers.services import OfferService
from app.rag.retrieval import PolicyRetrievalService, get_policy_retrieval_service
from app.refund_requests.repositories import InMemoryRefundRequestRepository
from app.refund_requests.services import RefundRequestService
from app.repayments.models import PaymentTransactionDocument, RepaymentScheduleDocument
from app.repayments.repositories import (
    InMemoryPaymentTransactionRepository,
    InMemoryRepaymentScheduleRepository,
)
from app.rm_mapping.models import RmMappingDocument
from app.rm_mapping.repositories import InMemoryRmMappingRepository
from app.seed.demo_bureau_offers import (
    demo_bureau_reporting_log_rows,
    demo_fraud_case_rows,
    demo_offer_rows,
    demo_rm_mapping_rows,
)
from app.seed.demo_lending import (
    demo_kyc_document_rows,
    demo_loan_application_rows,
    demo_loan_rows,
    demo_payment_transaction_rows,
    demo_repayment_schedule_rows,
)
from app.seed.demo_personas import demo_customer_rows
from app.seed.demo_tickets import demo_ticket_rows
from app.service_requests.repositories import InMemoryServiceRequestRepository
from app.service_requests.services import ServiceRequestService
from app.tickets.models import TicketDocument
from app.tickets.repositories import InMemoryTicketRepository
from app.tickets.services import TicketService
from app.tools.audit_hook import ToolAuditHook
from app.tools.bureau_reporting_tool import BureauReportingTool
from app.tools.constants import ToolName
from app.tools.document_generation_tool import DocumentGenerationTool
from app.tools.fraud_security_tool import FraudSecurityTool
from app.tools.kyc_document_tool import KYCDocumentTool
from app.tools.loan_status_tool import LoanStatusTool
from app.tools.offer_eligibility_tool import OfferEligibilityTool
from app.tools.policy_rag_tool import PolicyRAGTool
from app.tools.registry import FrozenMockToolRegistry, MockToolRegistry
from app.tools.rejection_reason_tool import RejectionReasonTool
from app.tools.repayment_tool import RepaymentTool
from app.tools.rm_redirect_tool import RMRedirectTool
from app.tools.transaction_tool import TransactionTool
from app.agent.execution.execution_types import TOOL_EXECUTION_POLICY_VERSION

_tool_execution_deps_override: ToolExecutionDeps | None = None


@dataclass(frozen=True)
class ToolExecutionDeps:
    """Injected tool registry and execution settings."""

    registry: MockToolRegistry
    policy_version: str = TOOL_EXECUTION_POLICY_VERSION
    tool_timeout_seconds: float = 30.0


def set_tool_execution_deps_override(deps: ToolExecutionDeps | None) -> None:
    """Override default tool execution dependencies (primarily for tests)."""
    global _tool_execution_deps_override
    _tool_execution_deps_override = deps


def _documents_from_seed() -> dict[str, object]:
    customers = [CustomerDocument.model_validate(row) for row in demo_customer_rows()]
    applications = [
        LoanApplicationDocument.model_validate(row) for row in demo_loan_application_rows()
    ]
    loans = [LoanDocument.model_validate(row) for row in demo_loan_rows()]
    kyc_documents = [KycDocumentDocument.model_validate(row) for row in demo_kyc_document_rows()]
    transactions = [
        PaymentTransactionDocument.model_validate(row)
        for row in demo_payment_transaction_rows()
    ]
    schedules = [
        RepaymentScheduleDocument.model_validate(row)
        for row in demo_repayment_schedule_rows()
    ]
    bureau_logs = [
        BureauReportingLogDocument.model_validate(row)
        for row in demo_bureau_reporting_log_rows()
    ]
    offers = [OfferDocument.model_validate(row) for row in demo_offer_rows()]
    rm_mappings = [RmMappingDocument.model_validate(row) for row in demo_rm_mapping_rows()]
    fraud_cases = [FraudCaseDocument.model_validate(row) for row in demo_fraud_case_rows()]
    tickets = [TicketDocument.model_validate(row) for row in demo_ticket_rows()]
    return {
        "customers": customers,
        "applications": applications,
        "loans": loans,
        "kyc_documents": kyc_documents,
        "transactions": transactions,
        "schedules": schedules,
        "bureau_logs": bureau_logs,
        "offers": offers,
        "rm_mappings": rm_mappings,
        "fraud_cases": fraud_cases,
        "tickets": tickets,
    }


def build_in_memory_tool_registry(
    *,
    with_audit: bool = True,
    policy_retrieval_service: PolicyRetrievalService | None = None,
) -> FrozenMockToolRegistry:
    """Build a frozen registry of all mock tools backed by in-memory demo repositories."""
    seed = _documents_from_seed()
    customers = seed["customers"]
    assert isinstance(customers, list)

    audit_hook = None
    if with_audit:
        audit_hook = ToolAuditHook(AuditService(InMemoryAuditLogRepository()))

    ticket_repository = InMemoryTicketRepository(seed["tickets"])  # type: ignore[arg-type]
    ticket_service = TicketService(ticket_repository)
    service_request_service = ServiceRequestService(
        InMemoryServiceRequestRepository(),
        ticket_service,
    )
    refund_request_service = RefundRequestService(
        InMemoryRefundRequestRepository(),
        ticket_service,
    )
    fraud_case_service = FraudCaseService(
        InMemoryFraudCaseRepository(seed["fraud_cases"]),  # type: ignore[arg-type]
        ticket_service,
    )
    offer_service = OfferService(InMemoryOfferRepository(seed["offers"]))  # type: ignore[arg-type]

    customer_repository = InMemoryCustomerRepository(customers)
    tools: dict[ToolName, object] = {
        "LoanStatusTool": LoanStatusTool(
            customer_repository=customer_repository,
            loan_application_repository=InMemoryLoanApplicationRepository(
                seed["applications"],  # type: ignore[arg-type]
            ),
            loan_repository=InMemoryLoanRepository(seed["loans"]),  # type: ignore[arg-type]
            audit_hook=audit_hook,
        ),
        "RejectionReasonTool": RejectionReasonTool(
            customer_repository=customer_repository,
            loan_application_repository=InMemoryLoanApplicationRepository(
                seed["applications"],  # type: ignore[arg-type]
            ),
            audit_hook=audit_hook,
        ),
        "KYCDocumentTool": KYCDocumentTool(
            customer_repository=customer_repository,
            kyc_document_repository=InMemoryKycDocumentRepository(
                seed["kyc_documents"],  # type: ignore[arg-type]
            ),
            loan_application_repository=InMemoryLoanApplicationRepository(
                seed["applications"],  # type: ignore[arg-type]
            ),
            service_request_service=service_request_service,
            audit_hook=audit_hook,
        ),
        "RepaymentTool": RepaymentTool(
            customer_repository=customer_repository,
            repayment_schedule_repository=InMemoryRepaymentScheduleRepository(
                seed["schedules"],  # type: ignore[arg-type]
            ),
            payment_transaction_repository=InMemoryPaymentTransactionRepository(
                seed["transactions"],  # type: ignore[arg-type]
            ),
            loan_repository=InMemoryLoanRepository(seed["loans"]),  # type: ignore[arg-type]
            audit_hook=audit_hook,
        ),
        "TransactionTool": TransactionTool(
            customer_repository=customer_repository,
            payment_transaction_repository=InMemoryPaymentTransactionRepository(
                seed["transactions"],  # type: ignore[arg-type]
            ),
            loan_repository=InMemoryLoanRepository(seed["loans"]),  # type: ignore[arg-type]
            refund_request_service=refund_request_service,
            audit_hook=audit_hook,
        ),
        "DocumentGenerationTool": DocumentGenerationTool(
            customer_repository=customer_repository,
            loan_repository=InMemoryLoanRepository(seed["loans"]),  # type: ignore[arg-type]
            repayment_schedule_repository=InMemoryRepaymentScheduleRepository(
                seed["schedules"],  # type: ignore[arg-type]
            ),
            service_request_service=service_request_service,
            audit_hook=audit_hook,
        ),
        "BureauReportingTool": BureauReportingTool(
            customer_repository=customer_repository,
            loan_repository=InMemoryLoanRepository(seed["loans"]),  # type: ignore[arg-type]
            bureau_reporting_log_repository=InMemoryBureauReportingLogRepository(
                seed["bureau_logs"],  # type: ignore[arg-type]
            ),
            service_request_service=service_request_service,
            audit_hook=audit_hook,
        ),
        "FraudSecurityTool": FraudSecurityTool(
            customer_repository=customer_repository,
            payment_transaction_repository=InMemoryPaymentTransactionRepository(
                seed["transactions"],  # type: ignore[arg-type]
            ),
            fraud_case_service=fraud_case_service,
            audit_hook=audit_hook,
        ),
        "OfferEligibilityTool": OfferEligibilityTool(
            customer_repository=customer_repository,
            offer_repository=InMemoryOfferRepository(seed["offers"]),  # type: ignore[arg-type]
            offer_service=offer_service,
            audit_hook=audit_hook,
        ),
        "RMRedirectTool": RMRedirectTool(
            customer_repository=customer_repository,
            rm_mapping_repository=InMemoryRmMappingRepository(
                seed["rm_mappings"],  # type: ignore[arg-type]
            ),
            service_request_service=service_request_service,
            audit_hook=audit_hook,
        ),
        "PolicyRAGTool": PolicyRAGTool(
            customer_repository=customer_repository,
            policy_retrieval_service=policy_retrieval_service,
            audit_hook=audit_hook,
        ),
    }
    return FrozenMockToolRegistry(tools)  # type: ignore[arg-type]


def build_in_memory_tool_execution_deps(
    *,
    with_audit: bool = True,
    policy_retrieval_service: PolicyRetrievalService | None = None,
    tool_timeout_seconds: float = 30.0,
) -> ToolExecutionDeps:
    """Build tool execution dependencies with in-memory demo repositories."""
    registry = build_in_memory_tool_registry(
        with_audit=with_audit,
        policy_retrieval_service=policy_retrieval_service,
    )
    return ToolExecutionDeps(
        registry=registry,
        tool_timeout_seconds=tool_timeout_seconds,
    )


def get_default_tool_execution_deps(settings: Settings | None = None) -> ToolExecutionDeps:
    """Return tool execution dependencies for local workflow execution."""
    if _tool_execution_deps_override is not None:
        return _tool_execution_deps_override

    resolved = settings or get_settings()
    retrieval = get_policy_retrieval_service(resolved)
    return build_in_memory_tool_execution_deps(policy_retrieval_service=retrieval)
