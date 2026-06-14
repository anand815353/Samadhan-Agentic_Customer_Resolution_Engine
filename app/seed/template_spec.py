"""Machine-readable Excel seed workbook contract for Samadhan demo data (T-013).

T-014 validate-only mode imports this module to check required sheets and columns.
Passwords in the users sheet are plaintext demo seed input; T-015/T-016 hash via T-007.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

SeedPhase = Literal[
    "initial",
    "lending",
    "bureau_offers",
    "policies",
    "evaluations",
    "ticketing",
    "runtime",
]

WORKBOOK_RELATIVE_PATH = "data/seed/master_excel/samadhan_demo_seed_data.xlsx"
WORKBOOK_FILENAME = "samadhan_demo_seed_data.xlsx"
TEMPLATE_SPEC_VERSION = "1.0.0"
DEFAULT_DEMO_PASSWORD = "Demo@123"

# DATA_MODEL.md §12 aliases (Excel tab name -> legacy name in docs)
SHEET_NAME_ALIASES: dict[str, str] = {
    "knowledge_documents": "policy_documents",
    "evaluation_cases": "golden_eval_cases",
}


@dataclass(frozen=True)
class SheetSpec:
    """Definition of one Excel worksheet tab and its MongoDB mapping."""

    sheet_name: str
    collection_target: str
    stable_id_column: str
    required_columns: tuple[str, ...]
    optional_columns: tuple[str, ...] = ()
    foreign_keys: dict[str, str] = field(default_factory=dict)
    allowed_enums: dict[str, tuple[str, ...]] = field(default_factory=dict)
    seed_phase: SeedPhase = "runtime"
    required_for_validate: bool = True
    json_columns: tuple[str, ...] = ()


def _spec(
    sheet_name: str,
    collection_target: str,
    stable_id_column: str,
    required_columns: tuple[str, ...],
    *,
    optional_columns: tuple[str, ...] = (),
    foreign_keys: dict[str, str] | None = None,
    allowed_enums: dict[str, tuple[str, ...]] | None = None,
    seed_phase: SeedPhase = "runtime",
    required_for_validate: bool = True,
    json_columns: tuple[str, ...] = (),
) -> SheetSpec:
    return SheetSpec(
        sheet_name=sheet_name,
        collection_target=collection_target,
        stable_id_column=stable_id_column,
        required_columns=required_columns,
        optional_columns=optional_columns,
        foreign_keys=foreign_keys or {},
        allowed_enums=allowed_enums or {},
        seed_phase=seed_phase,
        required_for_validate=required_for_validate,
        json_columns=json_columns,
    )


SHEET_SPECS: tuple[SheetSpec, ...] = (
    _spec(
        "users",
        "users",
        "user_id",
        (
            "user_id",
            "email",
            "password",
            "role",
            "display_name",
            "is_demo_user",
            "is_active",
        ),
        optional_columns=("customer_id",),
        allowed_enums={
            "role": ("customer", "support_agent", "admin"),
        },
        seed_phase="initial",
    ),
    _spec(
        "customers",
        "customers",
        "customer_id",
        (
            "customer_id",
            "full_name",
            "email",
            "mobile",
            "pan",
            "scenario_label",
            "folder_path",
        ),
        optional_columns=(
            "aadhaar_last4",
            "date_of_birth",
            "city",
            "customer_since",
            "risk_segment_label",
            "created_at",
            "updated_at",
        ),
        seed_phase="initial",
    ),
    _spec(
        "loan_applications",
        "loan_applications",
        "application_id",
        (
            "application_id",
            "customer_id",
            "product_type",
            "application_date",
            "requested_amount",
            "status",
            "current_stage",
        ),
        optional_columns=(
            "rejection_code",
            "customer_safe_rejection_reason",
            "internal_rejection_notes",
            "last_updated_at",
            "created_at",
        ),
        foreign_keys={"customer_id": "customers.customer_id"},
        allowed_enums={
            "status": ("pending", "approved", "rejected", "cancelled"),
        },
        seed_phase="lending",
    ),
    _spec(
        "loans",
        "loans",
        "loan_id",
        (
            "loan_id",
            "loan_account_number",
            "customer_id",
            "product_type",
            "principal_amount",
            "disbursed_amount",
            "interest_rate",
            "tenure_months",
            "emi_amount",
            "status",
            "bureau_status",
        ),
        optional_columns=(
            "application_id",
            "disbursal_date",
            "closure_date",
            "noc_status",
            "created_at",
            "updated_at",
        ),
        foreign_keys={
            "customer_id": "customers.customer_id",
            "application_id": "loan_applications.application_id",
        },
        allowed_enums={
            "status": ("active", "closed", "pending_disbursal", "written_off"),
            "noc_status": ("not_applicable", "pending", "generated", "delivered"),
            "bureau_status": ("reported_active", "reported_closed", "pending_update"),
        },
        seed_phase="lending",
    ),
    _spec(
        "kyc_documents",
        "kyc_documents",
        "kyc_id",
        (
            "kyc_id",
            "customer_id",
            "application_id",
            "document_type",
            "status",
        ),
        optional_columns=(
            "rejection_reason_code",
            "customer_safe_message",
            "uploaded_at",
            "reviewed_at",
            "created_at",
        ),
        foreign_keys={
            "customer_id": "customers.customer_id",
            "application_id": "loan_applications.application_id",
        },
        allowed_enums={
            "status": ("pending", "approved", "rejected", "reupload_required"),
        },
        seed_phase="lending",
    ),
    _spec(
        "repayment_schedule",
        "repayment_schedule",
        "schedule_id",
        (
            "schedule_id",
            "loan_id",
            "customer_id",
            "emi_number",
            "due_date",
            "emi_amount",
            "principal_component",
            "interest_component",
            "status",
        ),
        optional_columns=("paid_date", "transaction_id", "created_at"),
        foreign_keys={
            "loan_id": "loans.loan_id",
            "customer_id": "customers.customer_id",
            "transaction_id": "payment_transactions.transaction_id",
        },
        allowed_enums={
            "status": ("due", "paid", "overdue", "failed"),
        },
        seed_phase="lending",
    ),
    _spec(
        "payment_transactions",
        "payment_transactions",
        "transaction_id",
        (
            "transaction_id",
            "customer_id",
            "transaction_type",
            "amount",
            "transaction_date",
            "status",
            "reference_number",
            "is_duplicate_candidate",
            "remarks",
        ),
        optional_columns=("loan_id", "created_at"),
        foreign_keys={
            "customer_id": "customers.customer_id",
            "loan_id": "loans.loan_id",
        },
        allowed_enums={
            "transaction_type": (
                "emi_debit",
                "fee",
                "refund",
                "reversal",
                "fraud_alert",
            ),
            "status": ("success", "failed", "pending", "reversed"),
        },
        seed_phase="lending",
    ),
    _spec(
        "refund_requests",
        "refund_requests",
        "refund_request_id",
        (
            "refund_request_id",
            "customer_id",
            "ticket_id",
            "reason",
            "amount",
            "status",
        ),
        optional_columns=("loan_id", "transaction_id", "created_at", "updated_at"),
        foreign_keys={
            "customer_id": "customers.customer_id",
            "loan_id": "loans.loan_id",
            "ticket_id": "tickets.ticket_id",
            "transaction_id": "payment_transactions.transaction_id",
        },
        allowed_enums={
            "status": (
                "created",
                "under_review",
                "approved_mock",
                "rejected_mock",
                "closed",
            ),
        },
        seed_phase="ticketing",
    ),
    _spec(
        "service_requests",
        "service_requests",
        "service_request_id",
        (
            "service_request_id",
            "ticket_id",
            "customer_id",
            "request_type",
            "status",
            "customer_safe_summary",
            "created_by",
        ),
        optional_columns=(
            "loan_id",
            "document_path",
            "created_at",
            "updated_at",
            "completed_at",
        ),
        foreign_keys={
            "ticket_id": "tickets.ticket_id",
            "customer_id": "customers.customer_id",
            "loan_id": "loans.loan_id",
        },
        allowed_enums={
            "request_type": (
                "loan_statement",
                "noc_request",
                "closure_letter",
                "rm_callback",
                "kyc_reupload",
                "bureau_closure_letter",
            ),
            "status": (
                "created",
                "in_progress",
                "completed",
                "failed",
                "cancelled",
            ),
            "created_by": ("system", "customer", "agent", "admin"),
        },
        seed_phase="ticketing",
    ),
    _spec(
        "bureau_reporting_logs",
        "bureau_reporting_logs",
        "bureau_log_id",
        (
            "bureau_log_id",
            "customer_id",
            "loan_id",
            "bureau_name",
            "reporting_month",
            "internal_loan_status",
            "reported_status",
            "batch_id",
            "batch_status",
            "expected_update_window_days",
        ),
        optional_columns=("submitted_at", "accepted_at", "created_at"),
        foreign_keys={
            "customer_id": "customers.customer_id",
            "loan_id": "loans.loan_id",
        },
        allowed_enums={
            "batch_status": ("pending", "submitted", "accepted", "failed"),
        },
        seed_phase="bureau_offers",
    ),
    _spec(
        "rm_mapping",
        "rm_mapping",
        "rm_mapping_id",
        ("rm_mapping_id", "customer_id", "rm_name", "rm_email", "rm_phone", "branch"),
        optional_columns=("callback_available", "created_at"),
        foreign_keys={"customer_id": "customers.customer_id"},
        seed_phase="bureau_offers",
    ),
    _spec(
        "fraud_cases",
        "fraud_cases",
        "fraud_case_id",
        (
            "fraud_case_id",
            "ticket_id",
            "customer_id",
            "freeze_simulated",
            "status",
            "priority",
        ),
        optional_columns=(
            "reported_transaction_id",
            "freeze_reference",
            "created_at",
            "updated_at",
        ),
        foreign_keys={
            "ticket_id": "tickets.ticket_id",
            "customer_id": "customers.customer_id",
            "reported_transaction_id": "payment_transactions.transaction_id",
        },
        allowed_enums={
            "status": ("created", "escalated", "under_review", "closed"),
            "priority": ("critical",),
        },
        seed_phase="bureau_offers",
    ),
    _spec(
        "offers",
        "offers",
        "offer_id",
        (
            "offer_id",
            "customer_id",
            "offer_type",
            "is_eligible",
            "lead_created",
        ),
        optional_columns=(
            "approved_limit",
            "interest_rate",
            "tenure_options",
            "valid_until",
            "non_eligibility_reason",
            "created_at",
        ),
        foreign_keys={"customer_id": "customers.customer_id"},
        allowed_enums={"offer_type": ("top_up", "fresh_loan")},
        json_columns=("tenure_options",),
        seed_phase="bureau_offers",
    ),
    _spec(
        "tickets",
        "tickets",
        "ticket_id",
        (
            "ticket_id",
            "customer_id",
            "user_id",
            "session_id",
            "ticket_class",
            "intent",
            "risk_level",
            "priority",
            "status",
            "subject",
            "description",
            "source_channel",
            "last_customer_message",
            "last_ai_response",
        ),
        optional_columns=(
            "service_request_id",
            "assigned_agent_id",
            "escalation_reason",
            "closure_reason",
            "created_at",
            "updated_at",
            "closed_at",
        ),
        foreign_keys={
            "customer_id": "customers.customer_id",
            "user_id": "users.user_id",
            "service_request_id": "service_requests.service_request_id",
            "assigned_agent_id": "users.user_id",
        },
        allowed_enums={
            "ticket_class": (
                "tier_2_conversation",
                "tier_1_service_request",
                "human_review",
            ),
            "risk_level": ("low", "medium", "high", "critical"),
            "priority": ("low", "medium", "high", "critical"),
            "source_channel": ("web_chat",),
        },
        seed_phase="ticketing",
    ),
    _spec(
        "messages",
        "messages",
        "message_id",
        (
            "message_id",
            "ticket_id",
            "session_id",
            "customer_id",
            "sender_type",
            "message_text",
        ),
        optional_columns=("sender_id", "message_metadata", "created_at"),
        foreign_keys={
            "ticket_id": "tickets.ticket_id",
            "customer_id": "customers.customer_id",
            "sender_id": "users.user_id",
        },
        allowed_enums={
            "sender_type": ("customer", "ai", "support_agent", "system"),
        },
        json_columns=("message_metadata",),
        seed_phase="ticketing",
    ),
    _spec(
        "audit_logs",
        "audit_logs",
        "audit_id",
        ("audit_id", "event_type", "created_at"),
        optional_columns=(
            "ticket_id",
            "message_id",
            "customer_id",
            "intent",
            "risk_level",
            "priority",
            "tool_called",
            "tool_input_masked",
            "tool_output_summary",
            "retrieved_policy_ids",
            "confidence",
            "action_taken",
            "customer_safe_summary",
            "raw_internal_trace",
            "langsmith_trace_id",
        ),
        foreign_keys={
            "ticket_id": "tickets.ticket_id",
            "message_id": "messages.message_id",
            "customer_id": "customers.customer_id",
        },
        json_columns=(
            "tool_input_masked",
            "tool_output_summary",
            "retrieved_policy_ids",
            "raw_internal_trace",
        ),
        seed_phase="runtime",
        required_for_validate=True,
    ),
    _spec(
        "knowledge_documents",
        "knowledge_documents",
        "document_id",
        (
            "document_id",
            "title",
            "document_type",
            "domain",
            "version",
            "effective_date",
            "approval_status",
            "source_filename",
            "storage_path",
            "indexed_status",
        ),
        optional_columns=(
            "chunk_count",
            "uploaded_by",
            "uploaded_at",
            "indexed_at",
        ),
        foreign_keys={"uploaded_by": "users.user_id"},
        allowed_enums={
            "document_type": ("policy", "sop", "faq", "script"),
            "approval_status": ("draft", "approved", "archived"),
            "indexed_status": ("not_indexed", "indexed", "failed"),
        },
        seed_phase="policies",
    ),
    _spec(
        "evaluation_cases",
        "evaluation_cases",
        "eval_case_id",
        (
            "eval_case_id",
            "customer_id",
            "input_message",
            "expected_intent",
            "expected_risk_level",
            "expected_priority",
            "expected_ticket_class",
            "expected_guardrail",
            "expected_escalation",
            "active",
        ),
        optional_columns=(
            "expected_tools",
            "expected_response_contains",
            "forbidden_response_contains",
            "expected_service_request_type",
            "expected_source_domain",
            "created_at",
        ),
        foreign_keys={"customer_id": "customers.customer_id"},
        allowed_enums={
            "expected_intent": (
                "loan_application_status",
                "rejection_reason",
                "kyc_document_issue",
                "emi_payment_issue",
                "charges_refund_reversal",
                "policy_faq",
                "rm_redirection",
                "loan_statement_request",
                "noc_closure_certificate",
                "bureau_reporting_issue",
                "fraud_security_issue",
                "topup_offer",
                "unknown",
            ),
            "expected_risk_level": ("low", "medium", "high", "critical"),
            "expected_priority": ("low", "medium", "high", "critical"),
            "expected_ticket_class": (
                "tier_2_conversation",
                "tier_1_service_request",
                "human_review",
            ),
            "expected_guardrail": (
                "allow",
                "allow_with_audit",
                "escalate",
                "ask_follow_up",
                "block",
            ),
        },
        json_columns=(
            "expected_tools",
            "expected_response_contains",
            "forbidden_response_contains",
        ),
        seed_phase="evaluations",
    ),
    _spec(
        "usage_counters",
        "usage_counters",
        "counter_id",
        ("counter_id", "scope", "date", "message_count", "llm_call_count"),
        optional_columns=(
            "user_id",
            "estimated_tokens",
            "limit_exceeded",
            "created_at",
            "updated_at",
        ),
        foreign_keys={"user_id": "users.user_id"},
        allowed_enums={"scope": ("user", "global", "provider")},
        seed_phase="runtime",
        required_for_validate=True,
    ),
)


SHEET_SPECS_BY_NAME: dict[str, SheetSpec] = {s.sheet_name: s for s in SHEET_SPECS}


def all_sheet_names() -> tuple[str, ...]:
    """Return ordered Excel tab names."""
    return tuple(s.sheet_name for s in SHEET_SPECS)


def header_columns(spec: SheetSpec) -> tuple[str, ...]:
    """Column order for Excel header row (required then optional)."""
    return spec.required_columns + spec.optional_columns


def sheets_required_for_validate() -> tuple[str, ...]:
    """Sheet tabs T-014 validate-only must require (all sheets in contract)."""
    return tuple(s.sheet_name for s in SHEET_SPECS if s.required_for_validate)


def sheets_for_phase(phase: SeedPhase) -> tuple[str, ...]:
    """Sheets tagged with a given seed phase."""
    return tuple(s.sheet_name for s in SHEET_SPECS if s.seed_phase == phase)


SEED_PHASE_ORDER: tuple[SeedPhase, ...] = (
    "initial",
    "lending",
    "bureau_offers",
    "policies",
    "evaluations",
    "ticketing",
    "runtime",
)

# FK: users.customer_id references customers — load customers first within initial phase.
_INITIAL_PHASE_SHEET_ORDER: tuple[str, ...] = ("customers", "users")

# FK: repayment_schedule.transaction_id references payment_transactions — load txns first.
_LENDING_PHASE_SHEET_ORDER: tuple[str, ...] = (
    "loan_applications",
    "loans",
    "kyc_documents",
    "payment_transactions",
    "repayment_schedule",
)


def seed_phase_order() -> tuple[SeedPhase, ...]:
    """Ordered seed phases for reset/upsert load."""
    return SEED_PHASE_ORDER


def sheets_in_load_order() -> tuple[SheetSpec, ...]:
    """Sheet specs in dependency-safe load order (T-015 reset/upsert)."""
    ordered: list[SheetSpec] = []
    for phase in SEED_PHASE_ORDER:
        phase_specs = [s for s in SHEET_SPECS if s.seed_phase == phase]
        if phase == "initial":
            order_map = {name: index for index, name in enumerate(_INITIAL_PHASE_SHEET_ORDER)}
            phase_specs.sort(key=lambda s: order_map.get(s.sheet_name, 999))
        elif phase == "lending":
            order_map = {name: index for index, name in enumerate(_LENDING_PHASE_SHEET_ORDER)}
            phase_specs.sort(key=lambda s: order_map.get(s.sheet_name, 999))
        ordered.extend(phase_specs)
    return tuple(ordered)


def demo_seed_collections() -> tuple[str, ...]:
    """MongoDB demo collections managed by reset/upsert (derived from sheet specs)."""
    seen: set[str] = set()
    collections: list[str] = []
    for spec in sheets_in_load_order():
        if spec.collection_target not in seen:
            seen.add(spec.collection_target)
            collections.append(spec.collection_target)
    return tuple(collections)
