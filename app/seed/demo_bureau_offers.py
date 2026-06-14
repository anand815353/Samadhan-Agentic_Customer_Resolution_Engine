"""Canonical demo bureau/offers seed rows for T-018 (aligned with personas and MOCK_TOOLS_SPEC).

All fraud freeze fields are mock-only simulation records; no real account freeze is implied.
Top-up offer rows support eligibility checks only; no disbursement is implied.
"""

from __future__ import annotations

import json
from typing import Any

from app.seed.demo_lending import LN_IMRAN
from app.seed.demo_personas import DEMO_CUSTOMERS, DEMO_SEED_TIMESTAMP
from app.seed.template_spec import SHEET_SPECS_BY_NAME, header_columns

# Stable anchor IDs referenced by MOCK_TOOLS_SPEC examples and DEMO_GUIDE scenarios.
BRL_IMRAN_PRIOR = "BRL-2026-0001"
BRL_IMRAN_LATEST = "BRL-2026-0002"
FRD_KAVITA = "FRD-2026-0006"
OFFER_MOHIT = "OFFER-2026-0001"
OFFER_NEHA = "OFFER-2026-0002"
RM_FARHAN = "RM-2026-0001"
TKT_KAVITA_PLACEHOLDER = "TKT-2026-0006"
TXN_KAVITA_FRAUD = "TXN-2026-0006"

CUSTOMER_IDS = {customer.customer_id for customer in DEMO_CUSTOMERS}

_BUREAU_REPORTING_LOGS: list[dict[str, Any]] = [
    {
        "bureau_log_id": BRL_IMRAN_PRIOR,
        "customer_id": "CUST-005",
        "loan_id": LN_IMRAN,
        "bureau_name": "CIBIL",
        "reporting_month": "2026-01",
        "internal_loan_status": "closed",
        "reported_status": "active",
        "batch_id": "BATCH-2026-0042",
        "batch_status": "accepted",
        "expected_update_window_days": 45,
        "accepted_at": DEMO_SEED_TIMESTAMP,
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "bureau_log_id": BRL_IMRAN_LATEST,
        "customer_id": "CUST-005",
        "loan_id": LN_IMRAN,
        "bureau_name": "CIBIL",
        "reporting_month": "2026-04",
        "internal_loan_status": "closed",
        "reported_status": "closed",
        "batch_id": "BATCH-2026-0058",
        "batch_status": "submitted",
        "expected_update_window_days": 45,
        "submitted_at": DEMO_SEED_TIMESTAMP,
        "created_at": DEMO_SEED_TIMESTAMP,
    },
]

_OFFERS: list[dict[str, Any]] = [
    {
        "offer_id": OFFER_MOHIT,
        "customer_id": "CUST-007",
        "offer_type": "top_up",
        "is_eligible": True,
        "approved_limit": 50000,
        "interest_rate": 12.0,
        "tenure_options": json.dumps([12, 18, 24]),
        "valid_until": "2026-06-30",
        "lead_created": False,
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "offer_id": OFFER_NEHA,
        "customer_id": "CUST-008",
        "offer_type": "top_up",
        "is_eligible": False,
        "non_eligibility_reason": "No active pre-approved offer is available at this time.",
        "lead_created": False,
        "created_at": DEMO_SEED_TIMESTAMP,
    },
]

_RM_MAPPINGS: list[dict[str, Any]] = [
    {
        "rm_mapping_id": RM_FARHAN,
        "customer_id": "CUST-009",
        "rm_name": "Amit Verma",
        "rm_email": "amit.verma.demo@samadhan.ai",
        "rm_phone": "+91-98XX-XX2109",
        "branch": "Bengaluru Digital Lending Desk",
        "callback_available": True,
        "created_at": DEMO_SEED_TIMESTAMP,
    },
]

_FRAUD_CASES: list[dict[str, Any]] = [
    {
        "fraud_case_id": FRD_KAVITA,
        "ticket_id": TKT_KAVITA_PLACEHOLDER,
        "customer_id": "CUST-006",
        "reported_transaction_id": TXN_KAVITA_FRAUD,
        "freeze_simulated": True,
        "freeze_reference": "MOCK-FREEZE-2026-0006",
        "status": "escalated",
        "priority": "critical",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
]


def demo_bureau_reporting_log_rows() -> list[dict[str, Any]]:
    return list(_BUREAU_REPORTING_LOGS)


def demo_offer_rows() -> list[dict[str, Any]]:
    return list(_OFFERS)


def demo_rm_mapping_rows() -> list[dict[str, Any]]:
    return list(_RM_MAPPINGS)


def demo_fraud_case_rows() -> list[dict[str, Any]]:
    return list(_FRAUD_CASES)


def _rows_to_values(sheet_name: str, rows: list[dict[str, Any]]) -> list[list[Any]]:
    columns = header_columns(SHEET_SPECS_BY_NAME[sheet_name])
    return [[row.get(column) for column in columns] for row in rows]


def demo_bureau_reporting_log_row_values() -> list[list[Any]]:
    return _rows_to_values("bureau_reporting_logs", demo_bureau_reporting_log_rows())


def demo_offer_row_values() -> list[list[Any]]:
    return _rows_to_values("offers", demo_offer_rows())


def demo_rm_mapping_row_values() -> list[list[Any]]:
    return _rows_to_values("rm_mapping", demo_rm_mapping_rows())


def demo_fraud_case_row_values() -> list[list[Any]]:
    return _rows_to_values("fraud_cases", demo_fraud_case_rows())


def bureau_offers_alignment_errors() -> list[str]:
    """Validate bureau/offers seed coverage against demo personas."""
    errors: list[str] = []

    imran_logs = [row for row in _BUREAU_REPORTING_LOGS if row["customer_id"] == "CUST-005"]
    if len(imran_logs) != 2:
        errors.append("CUST-005 must have exactly two bureau reporting log rows")
    elif not any(row["loan_id"] == LN_IMRAN for row in imran_logs):
        errors.append("Imran bureau logs must reference LN-2026-0005")
    elif not any(
        row["internal_loan_status"] == "closed" and row["reported_status"] == "active"
        for row in imran_logs
    ):
        errors.append("Imran bureau logs must include closed internal vs active reported mismatch")
    elif not any(row["batch_status"] == "submitted" for row in imran_logs):
        errors.append("Imran bureau logs must include a submitted closure batch")

    mohit_offers = [row for row in _OFFERS if row["customer_id"] == "CUST-007"]
    if len(mohit_offers) != 1 or not mohit_offers[0].get("is_eligible"):
        errors.append("CUST-007 must have one eligible top-up offer")
    elif mohit_offers[0].get("approved_limit") != 50000:
        errors.append("Mohit offer must have approved_limit 50000")

    neha_offers = [row for row in _OFFERS if row["customer_id"] == "CUST-008"]
    if len(neha_offers) != 1 or neha_offers[0].get("is_eligible"):
        errors.append("CUST-008 must have one ineligible offer")
    else:
        reason = neha_offers[0].get("non_eligibility_reason") or ""
        lowered = reason.lower()
        for forbidden in ("risk score", "cutoff", "probability", "underwriting threshold"):
            if forbidden in lowered:
                errors.append("Neha non_eligibility_reason must remain customer-safe")

    farhan_rm = [row for row in _RM_MAPPINGS if row["customer_id"] == "CUST-009"]
    if len(farhan_rm) != 1 or not farhan_rm[0].get("callback_available"):
        errors.append("CUST-009 must have RM mapping with callback_available true")
    elif farhan_rm[0].get("rm_name") != "Amit Verma":
        errors.append("Farhan RM mapping must use Amit Verma")

    kavita_fraud = [row for row in _FRAUD_CASES if row["customer_id"] == "CUST-006"]
    if len(kavita_fraud) != 1:
        errors.append("CUST-006 must have exactly one fraud case")
    else:
        case = kavita_fraud[0]
        if not case.get("freeze_simulated"):
            errors.append("Kavita fraud case must have freeze_simulated true")
        freeze_ref = case.get("freeze_reference") or ""
        if not freeze_ref.startswith("MOCK-FREEZE-"):
            errors.append("Kavita fraud freeze_reference must use MOCK-FREEZE prefix")
        if case.get("reported_transaction_id") != TXN_KAVITA_FRAUD:
            errors.append("Kavita fraud case must reference TXN-2026-0006")

    for row in _BUREAU_REPORTING_LOGS + _OFFERS + _RM_MAPPINGS + _FRAUD_CASES:
        if row.get("customer_id") not in CUSTOMER_IDS:
            errors.append(f"invalid customer_id in bureau/offers row: {row.get('customer_id')}")

    return errors
