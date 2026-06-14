"""Canonical demo policy metadata seed rows for T-019 (aligned with RAG_AND_KNOWLEDGE_BASE).

Metadata and placeholder Markdown files only. No text extraction, chunking, or indexing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.seed.demo_personas import DEMO_SEED_TIMESTAMP
from app.seed.template_spec import SHEET_SPECS_BY_NAME, header_columns

USR_ADMIN = "USR-ADMIN-001"
POLICIES_DIR = "data/seed/policies"

# Stable document IDs for major support domains.
POL_LOAN_STATUS = "POL-LOAN-STATUS-001"
POL_REJECTION = "POL-REJECTION-001"
POL_KYC = "POL-KYC-001"
POL_EMI = "POL-EMI-001"
POL_REFUND = "POL-REFUND-001"
POL_NOC = "POL-NOC-001"
POL_BUREAU = "POL-BUREAU-001"
POL_FRAUD = "POL-FRAUD-001"
POL_TOPUP = "POL-TOPUP-001"
POL_RM = "POL-RM-001"
POL_SAFETY = "POL-SAFETY-001"

ALL_POLICY_DOCUMENT_IDS = (
    POL_LOAN_STATUS,
    POL_REJECTION,
    POL_KYC,
    POL_EMI,
    POL_REFUND,
    POL_NOC,
    POL_BUREAU,
    POL_FRAUD,
    POL_TOPUP,
    POL_RM,
    POL_SAFETY,
)

_REQUIRED_DOMAINS = frozenset(
    {
        "loan_status",
        "rejection",
        "kyc",
        "emi",
        "refund",
        "noc",
        "bureau",
        "fraud",
        "topup",
        "rm",
        "safety",
    }
)


def _policy_row(
    *,
    document_id: str,
    title: str,
    document_type: str,
    domain: str,
    source_filename: str,
) -> dict[str, Any]:
    return {
        "document_id": document_id,
        "title": title,
        "document_type": document_type,
        "domain": domain,
        "version": "1.0",
        "effective_date": "2026-01-01",
        "approval_status": "approved",
        "source_filename": source_filename,
        "storage_path": f"{POLICIES_DIR}/{source_filename}",
        "indexed_status": "not_indexed",
        "chunk_count": 0,
        "uploaded_by": USR_ADMIN,
        "uploaded_at": DEMO_SEED_TIMESTAMP,
        "indexed_at": None,
    }


_KNOWLEDGE_DOCUMENTS: list[dict[str, Any]] = [
    _policy_row(
        document_id=POL_LOAN_STATUS,
        title="Loan Application Status Policy",
        document_type="policy",
        domain="loan_status",
        source_filename="loan_application_status_policy.md",
    ),
    _policy_row(
        document_id=POL_REJECTION,
        title="Rejection Reason Communication Policy",
        document_type="policy",
        domain="rejection",
        source_filename="rejection_reason_policy.md",
    ),
    _policy_row(
        document_id=POL_KYC,
        title="KYC Document Policy",
        document_type="policy",
        domain="kyc",
        source_filename="kyc_document_policy.md",
    ),
    _policy_row(
        document_id=POL_EMI,
        title="EMI Payment Dispute SOP",
        document_type="sop",
        domain="emi",
        source_filename="emi_payment_dispute_sop.md",
    ),
    _policy_row(
        document_id=POL_REFUND,
        title="Refund and Reversal Policy",
        document_type="policy",
        domain="refund",
        source_filename="refund_reversal_policy.md",
    ),
    _policy_row(
        document_id=POL_NOC,
        title="NOC and Loan Statement SOP",
        document_type="sop",
        domain="noc",
        source_filename="noc_and_loan_statement_sop.md",
    ),
    _policy_row(
        document_id=POL_BUREAU,
        title="Bureau and CIBIL Reporting Policy",
        document_type="policy",
        domain="bureau",
        source_filename="bureau_reporting_policy.md",
    ),
    _policy_row(
        document_id=POL_FRAUD,
        title="Fraud and Security SOP",
        document_type="sop",
        domain="fraud",
        source_filename="fraud_security_sop.md",
    ),
    _policy_row(
        document_id=POL_TOPUP,
        title="Top-Up Offer Policy",
        document_type="policy",
        domain="topup",
        source_filename="topup_offer_policy.md",
    ),
    _policy_row(
        document_id=POL_RM,
        title="RM Callback SOP",
        document_type="sop",
        domain="rm",
        source_filename="rm_callback_sop.md",
    ),
    _policy_row(
        document_id=POL_SAFETY,
        title="Customer Response Safety Policy",
        document_type="policy",
        domain="safety",
        source_filename="customer_response_safety_policy.md",
    ),
]


def demo_knowledge_document_rows() -> list[dict[str, Any]]:
    return list(_KNOWLEDGE_DOCUMENTS)


def _rows_to_values(sheet_name: str, rows: list[dict[str, Any]]) -> list[list[Any]]:
    columns = header_columns(SHEET_SPECS_BY_NAME[sheet_name])
    return [[row.get(column) for column in columns] for row in rows]


def demo_knowledge_document_row_values() -> list[list[Any]]:
    return _rows_to_values("knowledge_documents", demo_knowledge_document_rows())


def _default_app_root() -> Path:
    return Path(__file__).resolve().parents[2]


def policies_alignment_errors(app_root: Path | None = None) -> list[str]:
    """Validate policy metadata coverage and on-disk file alignment."""
    errors: list[str] = []
    root = app_root or _default_app_root()

    if len(_KNOWLEDGE_DOCUMENTS) != 11:
        errors.append("knowledge_documents must contain exactly 11 rows")

    document_ids = [row["document_id"] for row in _KNOWLEDGE_DOCUMENTS]
    if len(set(document_ids)) != len(document_ids):
        errors.append("duplicate document_id in knowledge_documents")

    domains = {row["domain"] for row in _KNOWLEDGE_DOCUMENTS}
    if domains != _REQUIRED_DOMAINS:
        missing = _REQUIRED_DOMAINS - domains
        if missing:
            errors.append(f"missing policy domains: {sorted(missing)}")

    for row in _KNOWLEDGE_DOCUMENTS:
        if row.get("approval_status") != "approved":
            errors.append(f"{row['document_id']} must have approval_status approved")
        if row.get("indexed_status") != "not_indexed":
            errors.append(f"{row['document_id']} must have indexed_status not_indexed")
        if row.get("chunk_count") != 0:
            errors.append(f"{row['document_id']} must have chunk_count 0")
        if row.get("uploaded_by") != USR_ADMIN:
            errors.append(f"{row['document_id']} must be uploaded_by USR-ADMIN-001")

        source_filename = row.get("source_filename")
        storage_path = row.get("storage_path")
        if not source_filename or not storage_path:
            errors.append(f"{row['document_id']} must have source_filename and storage_path")
            continue
        if Path(storage_path).name != source_filename:
            errors.append(f"{row['document_id']} storage_path must end with source_filename")
        resolved = (root / storage_path).resolve()
        if not resolved.is_file():
            errors.append(f"{row['document_id']} storage_path does not exist: {storage_path}")

    return errors
