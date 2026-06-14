#!/usr/bin/env python3
"""Generate samadhan_demo_seed_data.xlsx from template_spec (T-013 through T-020)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.seed.demo_bureau_offers import (  # noqa: E402
    demo_bureau_reporting_log_row_values,
    demo_fraud_case_row_values,
    demo_offer_row_values,
    demo_rm_mapping_row_values,
)
from app.seed.demo_evaluations import demo_evaluation_case_row_values  # noqa: E402
from app.seed.demo_lending import (  # noqa: E402
    demo_kyc_document_row_values,
    demo_loan_application_row_values,
    demo_loan_row_values,
    demo_payment_transaction_row_values,
    demo_repayment_schedule_row_values,
)
from app.seed.demo_personas import (  # noqa: E402
    demo_customer_row_values,
    demo_user_row_values,
)
from app.seed.demo_policies import demo_knowledge_document_row_values  # noqa: E402
from app.seed.template_spec import (  # noqa: E402
    SHEET_SPECS,
    WORKBOOK_RELATIVE_PATH,
    header_columns,
)

INITIAL_DATA_SHEETS = frozenset(
    {
        "users",
        "customers",
        "loan_applications",
        "loans",
        "kyc_documents",
        "payment_transactions",
        "repayment_schedule",
        "bureau_reporting_logs",
        "offers",
        "rm_mapping",
        "fraud_cases",
        "knowledge_documents",
        "evaluation_cases",
    }
)


def main() -> int:
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        print(
            "openpyxl is required. Install with: uv sync",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    output_path = ROOT / WORKBOOK_RELATIVE_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    default_sheet = workbook.active
    workbook.remove(default_sheet)

    initial_rows = {
        "customers": demo_customer_row_values(),
        "users": demo_user_row_values(),
        "loan_applications": demo_loan_application_row_values(),
        "loans": demo_loan_row_values(),
        "kyc_documents": demo_kyc_document_row_values(),
        "payment_transactions": demo_payment_transaction_row_values(),
        "repayment_schedule": demo_repayment_schedule_row_values(),
        "bureau_reporting_logs": demo_bureau_reporting_log_row_values(),
        "offers": demo_offer_row_values(),
        "rm_mapping": demo_rm_mapping_row_values(),
        "fraud_cases": demo_fraud_case_row_values(),
        "knowledge_documents": demo_knowledge_document_row_values(),
        "evaluation_cases": demo_evaluation_case_row_values(),
    }

    for spec in SHEET_SPECS:
        worksheet = workbook.create_sheet(title=spec.sheet_name)
        worksheet.append(list(header_columns(spec)))
        if spec.sheet_name in INITIAL_DATA_SHEETS:
            for row in initial_rows[spec.sheet_name]:
                worksheet.append(row)

    workbook.save(output_path)
    lending_total = sum(
        len(initial_rows[sheet])
        for sheet in (
            "loan_applications",
            "loans",
            "kyc_documents",
            "payment_transactions",
            "repayment_schedule",
        )
    )
    bureau_total = sum(
        len(initial_rows[sheet])
        for sheet in (
            "bureau_reporting_logs",
            "offers",
            "rm_mapping",
            "fraud_cases",
        )
    )
    policy_total = len(initial_rows["knowledge_documents"])
    eval_total = len(initial_rows["evaluation_cases"])
    print(
        f"Wrote {len(SHEET_SPECS)} sheets to {output_path.relative_to(ROOT)} "
        f"({len(initial_rows['customers'])} customers, {len(initial_rows['users'])} users, "
        f"{lending_total} lending rows, {bureau_total} bureau/offers rows, "
        f"{policy_total} policy rows, {eval_total} evaluation rows)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
