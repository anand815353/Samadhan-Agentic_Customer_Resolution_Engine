"""Canonical demo lending seed rows for T-017 (aligned with demo personas and MOCK_TOOLS_SPEC)."""

from __future__ import annotations

from typing import Any

from app.seed.demo_personas import DEMO_CUSTOMERS, DEMO_SEED_TIMESTAMP
from app.seed.template_spec import SHEET_SPECS_BY_NAME, header_columns

# Stable anchor IDs referenced by MOCK_TOOLS_SPEC examples.
APP_RAMESH = "APP-2026-0001"
APP_PRIYA = "APP-2026-0002"
APP_ARJUN = "APP-2026-0003"
LN_ARJUN = "LN-2026-0003"
LN_SNEHA = "LN-2026-0004"
LN_IMRAN = "LN-2026-0005"

CUSTOMER_IDS = {customer.customer_id for customer in DEMO_CUSTOMERS}

_LOAN_APPLICATIONS: list[dict[str, Any]] = [
    {
        "application_id": APP_RAMESH,
        "customer_id": "CUST-001",
        "product_type": "personal_loan",
        "application_date": "2026-02-10",
        "requested_amount": 250000,
        "status": "pending",
        "current_stage": "kyc_review",
        "last_updated_at": DEMO_SEED_TIMESTAMP,
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "application_id": APP_PRIYA,
        "customer_id": "CUST-002",
        "product_type": "personal_loan",
        "application_date": "2026-01-20",
        "requested_amount": 180000,
        "status": "rejected",
        "current_stage": "credit_review",
        "rejection_code": "ELIGIBILITY_NOT_MET",
        "customer_safe_rejection_reason": (
            "Your application could not be approved because it did not meet the "
            "current eligibility criteria for this loan product."
        ),
        "internal_rejection_notes": "Internal risk score below underwriting threshold.",
        "last_updated_at": DEMO_SEED_TIMESTAMP,
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "application_id": APP_ARJUN,
        "customer_id": "CUST-003",
        "product_type": "personal_loan",
        "application_date": "2024-08-15",
        "requested_amount": 300000,
        "status": "approved",
        "current_stage": "disbursed",
        "last_updated_at": DEMO_SEED_TIMESTAMP,
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "application_id": "APP-2026-0004",
        "customer_id": "CUST-004",
        "product_type": "personal_loan",
        "application_date": "2022-06-01",
        "requested_amount": 220000,
        "status": "approved",
        "current_stage": "closed",
        "last_updated_at": DEMO_SEED_TIMESTAMP,
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "application_id": "APP-2026-0005",
        "customer_id": "CUST-005",
        "product_type": "personal_loan",
        "application_date": "2023-03-10",
        "requested_amount": 275000,
        "status": "approved",
        "current_stage": "closed",
        "last_updated_at": DEMO_SEED_TIMESTAMP,
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "application_id": "APP-2026-0006",
        "customer_id": "CUST-006",
        "product_type": "personal_loan",
        "application_date": "2024-04-01",
        "requested_amount": 200000,
        "status": "approved",
        "current_stage": "disbursed",
        "last_updated_at": DEMO_SEED_TIMESTAMP,
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "application_id": "APP-2026-0007",
        "customer_id": "CUST-007",
        "product_type": "personal_loan",
        "application_date": "2023-11-15",
        "requested_amount": 350000,
        "status": "approved",
        "current_stage": "disbursed",
        "last_updated_at": DEMO_SEED_TIMESTAMP,
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "application_id": "APP-2026-0008",
        "customer_id": "CUST-008",
        "product_type": "personal_loan",
        "application_date": "2024-05-10",
        "requested_amount": 190000,
        "status": "approved",
        "current_stage": "disbursed",
        "last_updated_at": DEMO_SEED_TIMESTAMP,
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "application_id": "APP-2026-0009",
        "customer_id": "CUST-009",
        "product_type": "personal_loan",
        "application_date": "2023-08-22",
        "requested_amount": 240000,
        "status": "approved",
        "current_stage": "disbursed",
        "last_updated_at": DEMO_SEED_TIMESTAMP,
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "application_id": "APP-2026-0010",
        "customer_id": "CUST-010",
        "product_type": "personal_loan",
        "application_date": "2024-06-01",
        "requested_amount": 320000,
        "status": "approved",
        "current_stage": "disbursed",
        "last_updated_at": DEMO_SEED_TIMESTAMP,
        "created_at": DEMO_SEED_TIMESTAMP,
    },
]

_LOANS: list[dict[str, Any]] = [
    {
        "loan_id": LN_ARJUN,
        "loan_account_number": "LNAC-2026-0003",
        "customer_id": "CUST-003",
        "application_id": APP_ARJUN,
        "product_type": "personal_loan",
        "principal_amount": 300000,
        "disbursed_amount": 300000,
        "interest_rate": 12.5,
        "tenure_months": 36,
        "emi_amount": 12500,
        "status": "active",
        "bureau_status": "reported_active",
        "disbursal_date": "2024-09-01",
        "noc_status": "not_applicable",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "loan_id": LN_SNEHA,
        "loan_account_number": "LNAC-2026-0004",
        "customer_id": "CUST-004",
        "application_id": "APP-2026-0004",
        "product_type": "personal_loan",
        "principal_amount": 220000,
        "disbursed_amount": 220000,
        "interest_rate": 11.75,
        "tenure_months": 24,
        "emi_amount": 10500,
        "status": "closed",
        "bureau_status": "reported_closed",
        "disbursal_date": "2022-07-01",
        "closure_date": "2026-04-10",
        "noc_status": "pending",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "loan_id": LN_IMRAN,
        "loan_account_number": "LNAC-2026-0005",
        "customer_id": "CUST-005",
        "application_id": "APP-2026-0005",
        "product_type": "personal_loan",
        "principal_amount": 275000,
        "disbursed_amount": 275000,
        "interest_rate": 12.0,
        "tenure_months": 30,
        "emi_amount": 11000,
        "status": "closed",
        "bureau_status": "pending_update",
        "disbursal_date": "2023-04-01",
        "closure_date": "2026-02-15",
        "noc_status": "generated",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "loan_id": "LN-2026-0006",
        "loan_account_number": "LNAC-2026-0006",
        "customer_id": "CUST-006",
        "application_id": "APP-2026-0006",
        "product_type": "personal_loan",
        "principal_amount": 200000,
        "disbursed_amount": 200000,
        "interest_rate": 13.0,
        "tenure_months": 24,
        "emi_amount": 9500,
        "status": "active",
        "bureau_status": "reported_active",
        "disbursal_date": "2024-05-01",
        "noc_status": "not_applicable",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "loan_id": "LN-2026-0007",
        "loan_account_number": "LNAC-2026-0007",
        "customer_id": "CUST-007",
        "application_id": "APP-2026-0007",
        "product_type": "personal_loan",
        "principal_amount": 350000,
        "disbursed_amount": 350000,
        "interest_rate": 11.5,
        "tenure_months": 36,
        "emi_amount": 11500,
        "status": "active",
        "bureau_status": "reported_active",
        "disbursal_date": "2023-12-01",
        "noc_status": "not_applicable",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "loan_id": "LN-2026-0008",
        "loan_account_number": "LNAC-2026-0008",
        "customer_id": "CUST-008",
        "application_id": "APP-2026-0008",
        "product_type": "personal_loan",
        "principal_amount": 190000,
        "disbursed_amount": 190000,
        "interest_rate": 13.5,
        "tenure_months": 24,
        "emi_amount": 9000,
        "status": "active",
        "bureau_status": "reported_active",
        "disbursal_date": "2024-06-01",
        "noc_status": "not_applicable",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "loan_id": "LN-2026-0009",
        "loan_account_number": "LNAC-2026-0009",
        "customer_id": "CUST-009",
        "application_id": "APP-2026-0009",
        "product_type": "personal_loan",
        "principal_amount": 240000,
        "disbursed_amount": 240000,
        "interest_rate": 12.25,
        "tenure_months": 30,
        "emi_amount": 9800,
        "status": "active",
        "bureau_status": "reported_active",
        "disbursal_date": "2023-09-01",
        "noc_status": "not_applicable",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "loan_id": "LN-2026-0010",
        "loan_account_number": "LNAC-2026-0010",
        "customer_id": "CUST-010",
        "application_id": "APP-2026-0010",
        "product_type": "personal_loan",
        "principal_amount": 320000,
        "disbursed_amount": 320000,
        "interest_rate": 11.0,
        "tenure_months": 36,
        "emi_amount": 10500,
        "status": "active",
        "bureau_status": "reported_active",
        "disbursal_date": "2024-07-01",
        "noc_status": "not_applicable",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
]

_KYC_DOCUMENTS: list[dict[str, Any]] = [
    {
        "kyc_id": "KYC-2026-0001",
        "customer_id": "CUST-001",
        "application_id": APP_RAMESH,
        "document_type": "bank_statement",
        "status": "reupload_required",
        "rejection_reason_code": "DOC_UNCLEAR",
        "customer_safe_message": (
            "Your bank statement could not be verified because the uploaded file was unclear. "
            "Please upload a clear copy."
        ),
        "uploaded_at": "2026-02-12T10:00:00+00:00",
        "reviewed_at": "2026-02-14T09:30:00+00:00",
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "kyc_id": "KYC-2026-0002",
        "customer_id": "CUST-002",
        "application_id": APP_PRIYA,
        "document_type": "pan",
        "status": "approved",
        "uploaded_at": "2026-01-18T08:00:00+00:00",
        "reviewed_at": "2026-01-19T11:00:00+00:00",
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "kyc_id": "KYC-2026-0003",
        "customer_id": "CUST-003",
        "application_id": APP_ARJUN,
        "document_type": "pan",
        "status": "approved",
        "uploaded_at": "2024-08-10T08:00:00+00:00",
        "reviewed_at": "2024-08-12T10:00:00+00:00",
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "kyc_id": "KYC-2026-0004",
        "customer_id": "CUST-004",
        "application_id": "APP-2026-0004",
        "document_type": "address_proof",
        "status": "approved",
        "uploaded_at": "2022-05-28T08:00:00+00:00",
        "reviewed_at": "2022-05-30T10:00:00+00:00",
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "kyc_id": "KYC-2026-0005",
        "customer_id": "CUST-005",
        "application_id": "APP-2026-0005",
        "document_type": "pan",
        "status": "approved",
        "uploaded_at": "2023-03-05T08:00:00+00:00",
        "reviewed_at": "2023-03-07T10:00:00+00:00",
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "kyc_id": "KYC-2026-0006",
        "customer_id": "CUST-006",
        "application_id": "APP-2026-0006",
        "document_type": "pan",
        "status": "approved",
        "uploaded_at": "2024-03-28T08:00:00+00:00",
        "reviewed_at": "2024-03-30T10:00:00+00:00",
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "kyc_id": "KYC-2026-0007",
        "customer_id": "CUST-007",
        "application_id": "APP-2026-0007",
        "document_type": "pan",
        "status": "approved",
        "uploaded_at": "2023-11-10T08:00:00+00:00",
        "reviewed_at": "2023-11-12T10:00:00+00:00",
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "kyc_id": "KYC-2026-0008",
        "customer_id": "CUST-008",
        "application_id": "APP-2026-0008",
        "document_type": "pan",
        "status": "approved",
        "uploaded_at": "2024-05-05T08:00:00+00:00",
        "reviewed_at": "2024-05-07T10:00:00+00:00",
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "kyc_id": "KYC-2026-0009",
        "customer_id": "CUST-009",
        "application_id": "APP-2026-0009",
        "document_type": "pan",
        "status": "approved",
        "uploaded_at": "2023-08-15T08:00:00+00:00",
        "reviewed_at": "2023-08-17T10:00:00+00:00",
        "created_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "kyc_id": "KYC-2026-0010",
        "customer_id": "CUST-010",
        "application_id": "APP-2026-0010",
        "document_type": "pan",
        "status": "approved",
        "uploaded_at": "2024-05-28T08:00:00+00:00",
        "reviewed_at": "2024-05-30T10:00:00+00:00",
        "created_at": DEMO_SEED_TIMESTAMP,
    },
]


def _build_payment_transactions() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    rows.extend(
        [
            {
                "transaction_id": "TXN-2026-0003",
                "customer_id": "CUST-003",
                "loan_id": LN_ARJUN,
                "transaction_type": "emi_debit",
                "amount": 12500,
                "transaction_date": "2026-04-05T06:15:00+00:00",
                "status": "success",
                "reference_number": "REF-TXN-2026-0003",
                "is_duplicate_candidate": False,
                "remarks": "April 2026 EMI debit",
                "created_at": DEMO_SEED_TIMESTAMP,
            },
            {
                "transaction_id": "TXN-2026-0004",
                "customer_id": "CUST-003",
                "loan_id": LN_ARJUN,
                "transaction_type": "emi_debit",
                "amount": 12500,
                "transaction_date": "2026-04-05T08:42:00+00:00",
                "status": "success",
                "reference_number": "REF-TXN-2026-0004",
                "is_duplicate_candidate": True,
                "remarks": "Duplicate EMI debit candidate for April 2026",
                "created_at": DEMO_SEED_TIMESTAMP,
            },
        ]
    )

    for index in range(1, 7):
        rows.append(
            {
                "transaction_id": f"TXN-2026-{10 + index:04d}",
                "customer_id": "CUST-004",
                "loan_id": LN_SNEHA,
                "transaction_type": "emi_debit",
                "amount": 10500,
                "transaction_date": f"2025-{index + 6:02d}-05T07:00:00+00:00",
                "status": "success",
                "reference_number": f"REF-TXN-2026-00{10 + index}",
                "is_duplicate_candidate": False,
                "remarks": f"Historical EMI {index} for closed loan",
                "created_at": DEMO_SEED_TIMESTAMP,
            }
        )

    rows.append(
        {
            "transaction_id": "TXN-2026-0020",
            "customer_id": "CUST-005",
            "loan_id": LN_IMRAN,
            "transaction_type": "emi_debit",
            "amount": 11000,
            "transaction_date": "2026-02-10T07:00:00+00:00",
            "status": "success",
            "reference_number": "REF-TXN-2026-0020",
            "is_duplicate_candidate": False,
            "remarks": "Final closure EMI debit",
            "created_at": DEMO_SEED_TIMESTAMP,
        }
    )

    rows.append(
        {
            "transaction_id": "TXN-2026-0006",
            "customer_id": "CUST-006",
            "loan_id": "LN-2026-0006",
            "transaction_type": "fraud_alert",
            "amount": 4999,
            "transaction_date": "2026-05-28T14:22:00+00:00",
            "status": "pending",
            "reference_number": "REF-TXN-2026-0006",
            "is_duplicate_candidate": False,
            "remarks": "Mock SMS alert transaction flagged for review",
            "created_at": DEMO_SEED_TIMESTAMP,
        }
    )
    rows.append(
        {
            "transaction_id": "TXN-2026-0021",
            "customer_id": "CUST-006",
            "loan_id": "LN-2026-0006",
            "transaction_type": "emi_debit",
            "amount": 9500,
            "transaction_date": "2026-05-05T07:00:00+00:00",
            "status": "success",
            "reference_number": "REF-TXN-2026-0021",
            "is_duplicate_candidate": False,
            "remarks": "May 2026 EMI debit",
            "created_at": DEMO_SEED_TIMESTAMP,
        }
    )

    for cust_num, loan_id, emi, txn_base in (
        ("007", "LN-2026-0007", 11500, 30),
        ("009", "LN-2026-0009", 9800, 40),
    ):
        for month_offset in range(3):
            txn_id = f"TXN-2026-{txn_base + month_offset:04d}"
            rows.append(
                {
                    "transaction_id": txn_id,
                    "customer_id": f"CUST-{cust_num}",
                    "loan_id": loan_id,
                    "transaction_type": "emi_debit",
                    "amount": emi,
                    "transaction_date": f"2026-0{3 + month_offset}-05T07:00:00+00:00",
                    "status": "success",
                    "reference_number": f"REF-{txn_id}",
                    "is_duplicate_candidate": False,
                    "remarks": "On-time EMI debit",
                    "created_at": DEMO_SEED_TIMESTAMP,
                }
            )

    rows.extend(
        [
            {
                "transaction_id": "TXN-2026-0043",
                "customer_id": "CUST-008",
                "loan_id": "LN-2026-0008",
                "transaction_type": "emi_debit",
                "amount": 9000,
                "transaction_date": "2026-04-05T07:00:00+00:00",
                "status": "failed",
                "reference_number": "REF-TXN-2026-0043",
                "is_duplicate_candidate": False,
                "remarks": "Failed EMI debit attempt",
                "created_at": DEMO_SEED_TIMESTAMP,
            },
            {
                "transaction_id": "TXN-2026-0044",
                "customer_id": "CUST-008",
                "loan_id": "LN-2026-0008",
                "transaction_type": "emi_debit",
                "amount": 9000,
                "transaction_date": "2026-03-05T07:00:00+00:00",
                "status": "success",
                "reference_number": "REF-TXN-2026-0044",
                "is_duplicate_candidate": False,
                "remarks": "March 2026 EMI debit",
                "created_at": DEMO_SEED_TIMESTAMP,
            },
        ]
    )

    for emi_number in range(1, 13):
        txn_id = f"TXN-2026-{50 + emi_number:04d}"
        rows.append(
            {
                "transaction_id": txn_id,
                "customer_id": "CUST-010",
                "loan_id": "LN-2026-0010",
                "transaction_type": "emi_debit",
                "amount": 10500,
                "transaction_date": f"2025-{((emi_number + 5) % 12) + 1:02d}-05T07:00:00+00:00",
                "status": "success",
                "reference_number": f"REF-{txn_id}",
                "is_duplicate_candidate": False,
                "remarks": f"FY statement EMI {emi_number}",
                "created_at": DEMO_SEED_TIMESTAMP,
            }
        )

    return rows


def _build_repayment_schedules(
    transactions_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    rows.append(
        {
            "schedule_id": "SCH-2026-0003",
            "loan_id": LN_ARJUN,
            "customer_id": "CUST-003",
            "emi_number": 8,
            "due_date": "2026-04-05",
            "emi_amount": 12500,
            "principal_component": 9800,
            "interest_component": 2700,
            "status": "paid",
            "paid_date": "2026-04-05",
            "transaction_id": "TXN-2026-0003",
            "created_at": DEMO_SEED_TIMESTAMP,
        }
    )

    sneha_txns = [f"TXN-2026-{10 + index:04d}" for index in range(1, 7)]
    for emi_number, txn_id in enumerate(sneha_txns, start=1):
        rows.append(
            {
                "schedule_id": f"SCH-2026-{10 + emi_number:04d}",
                "loan_id": LN_SNEHA,
                "customer_id": "CUST-004",
                "emi_number": emi_number,
                "due_date": f"2025-{emi_number + 6:02d}-05",
                "emi_amount": 10500,
                "principal_component": 8200,
                "interest_component": 2300,
                "status": "paid",
                "paid_date": f"2025-{emi_number + 6:02d}-05",
                "transaction_id": txn_id,
                "created_at": DEMO_SEED_TIMESTAMP,
            }
        )

    rows.append(
        {
            "schedule_id": "SCH-2026-0020",
            "loan_id": LN_IMRAN,
            "customer_id": "CUST-005",
            "emi_number": 24,
            "due_date": "2026-02-10",
            "emi_amount": 11000,
            "principal_component": 9000,
            "interest_component": 2000,
            "status": "paid",
            "paid_date": "2026-02-10",
            "transaction_id": "TXN-2026-0020",
            "created_at": DEMO_SEED_TIMESTAMP,
        }
    )

    rows.append(
        {
            "schedule_id": "SCH-2026-0021",
            "loan_id": "LN-2026-0006",
            "customer_id": "CUST-006",
            "emi_number": 13,
            "due_date": "2026-05-05",
            "emi_amount": 9500,
            "principal_component": 7600,
            "interest_component": 1900,
            "status": "paid",
            "paid_date": "2026-05-05",
            "transaction_id": "TXN-2026-0021",
            "created_at": DEMO_SEED_TIMESTAMP,
        }
    )

    for cust_num, loan_id, emi, sch_base, txn_base in (
        ("007", "LN-2026-0007", 11500, 30, 30),
        ("009", "LN-2026-0009", 9800, 40, 40),
    ):
        for month_offset in range(3):
            txn_id = f"TXN-2026-{txn_base + month_offset:04d}"
            rows.append(
                {
                    "schedule_id": f"SCH-2026-{sch_base + month_offset:04d}",
                    "loan_id": loan_id,
                    "customer_id": f"CUST-{cust_num}",
                    "emi_number": month_offset + 1,
                    "due_date": f"2026-0{3 + month_offset}-05",
                    "emi_amount": emi,
                    "principal_component": round(emi * 0.78),
                    "interest_component": round(emi * 0.22),
                    "status": "paid",
                    "paid_date": f"2026-0{3 + month_offset}-05",
                    "transaction_id": txn_id,
                    "created_at": DEMO_SEED_TIMESTAMP,
                }
            )

    rows.extend(
        [
            {
                "schedule_id": "SCH-2026-0043",
                "loan_id": "LN-2026-0008",
                "customer_id": "CUST-008",
                "emi_number": 11,
                "due_date": "2026-04-05",
                "emi_amount": 9000,
                "principal_component": 7000,
                "interest_component": 2000,
                "status": "overdue",
                "created_at": DEMO_SEED_TIMESTAMP,
            },
            {
                "schedule_id": "SCH-2026-0044",
                "loan_id": "LN-2026-0008",
                "customer_id": "CUST-008",
                "emi_number": 10,
                "due_date": "2026-03-05",
                "emi_amount": 9000,
                "principal_component": 7000,
                "interest_component": 2000,
                "status": "paid",
                "paid_date": "2026-03-05",
                "transaction_id": "TXN-2026-0044",
                "created_at": DEMO_SEED_TIMESTAMP,
            },
        ]
    )

    for emi_number in range(1, 13):
        txn_id = f"TXN-2026-{50 + emi_number:04d}"
        status = "paid" if emi_number <= 11 else "due"
        row: dict[str, Any] = {
            "schedule_id": f"SCH-2026-{60 + emi_number:04d}",
            "loan_id": "LN-2026-0010",
            "customer_id": "CUST-010",
            "emi_number": emi_number,
            "due_date": f"2025-{((emi_number + 5) % 12) + 1:02d}-05",
            "emi_amount": 10500,
            "principal_component": 8200,
            "interest_component": 2300,
            "status": status,
            "created_at": DEMO_SEED_TIMESTAMP,
        }
        if status == "paid" and txn_id in transactions_by_id:
            row["paid_date"] = row["due_date"]
            row["transaction_id"] = txn_id
        rows.append(row)

    return rows


_PAYMENT_TRANSACTIONS = _build_payment_transactions()
_REPAYMENT_SCHEDULES = _build_repayment_schedules(
    {row["transaction_id"]: row for row in _PAYMENT_TRANSACTIONS}
)


def demo_loan_application_rows() -> list[dict[str, Any]]:
    return list(_LOAN_APPLICATIONS)


def demo_loan_rows() -> list[dict[str, Any]]:
    return list(_LOANS)


def demo_kyc_document_rows() -> list[dict[str, Any]]:
    return list(_KYC_DOCUMENTS)


def demo_payment_transaction_rows() -> list[dict[str, Any]]:
    return list(_PAYMENT_TRANSACTIONS)


def demo_repayment_schedule_rows() -> list[dict[str, Any]]:
    return list(_REPAYMENT_SCHEDULES)


def _rows_to_values(sheet_name: str, rows: list[dict[str, Any]]) -> list[list[Any]]:
    columns = header_columns(SHEET_SPECS_BY_NAME[sheet_name])
    return [[row.get(column) for column in columns] for row in rows]


def demo_loan_application_row_values() -> list[list[Any]]:
    return _rows_to_values("loan_applications", demo_loan_application_rows())


def demo_loan_row_values() -> list[list[Any]]:
    return _rows_to_values("loans", demo_loan_rows())


def demo_kyc_document_row_values() -> list[list[Any]]:
    return _rows_to_values("kyc_documents", demo_kyc_document_rows())


def demo_payment_transaction_row_values() -> list[list[Any]]:
    return _rows_to_values("payment_transactions", demo_payment_transaction_rows())


def demo_repayment_schedule_row_values() -> list[list[Any]]:
    return _rows_to_values("repayment_schedule", demo_repayment_schedule_rows())


def lending_alignment_errors() -> list[str]:
    """Validate lending seed coverage against demo personas."""
    errors: list[str] = []
    apps_by_customer = {row["customer_id"]: row for row in _LOAN_APPLICATIONS}
    loans_by_customer = {row["customer_id"]: row for row in _LOANS}

    for customer in DEMO_CUSTOMERS:
        customer_id = customer.customer_id
        if customer_id not in apps_by_customer:
            errors.append(f"missing loan application for {customer_id}")
            continue
        app = apps_by_customer[customer_id]
        if customer_id == "CUST-001":
            if app["status"] != "pending":
                errors.append("CUST-001 application must be pending")
            if customer_id in loans_by_customer:
                errors.append("CUST-001 must not have a loan")
        elif customer_id == "CUST-002":
            if app["status"] != "rejected":
                errors.append("CUST-002 application must be rejected")
            if not app.get("customer_safe_rejection_reason"):
                errors.append("CUST-002 must have customer_safe_rejection_reason")
        elif customer_id == "CUST-003":
            loan = loans_by_customer.get(customer_id)
            if loan is None or loan["loan_id"] != LN_ARJUN:
                errors.append("CUST-003 must have LN-2026-0003")
        elif customer_id == "CUST-004":
            loan = loans_by_customer.get(customer_id)
            if loan is None or loan.get("noc_status") != "pending":
                errors.append("CUST-004 loan must have noc_status pending")
        elif customer_id == "CUST-010":
            schedules = [
                row for row in _REPAYMENT_SCHEDULES if row["customer_id"] == customer_id
            ]
            if len(schedules) < 12:
                errors.append("CUST-010 must have at least 12 schedule rows")

    for row in _LOAN_APPLICATIONS + _LOANS + _KYC_DOCUMENTS + _PAYMENT_TRANSACTIONS + _REPAYMENT_SCHEDULES:
        if row.get("customer_id") not in CUSTOMER_IDS:
            errors.append(f"invalid customer_id in lending row: {row.get('customer_id')}")

    duplicate_emi = [
        row
        for row in _PAYMENT_TRANSACTIONS
        if row.get("customer_id") == "CUST-003" and row.get("is_duplicate_candidate")
    ]
    if len(duplicate_emi) != 1:
        errors.append("CUST-003 must have exactly one duplicate EMI transaction")

    return errors
