"""Build safe customer context snapshots for agent intake."""

from __future__ import annotations

from app.agent.state import CustomerContextSnapshot
from app.customers.models import CustomerDocument
from app.lending.models import LoanDocument


def build_customer_context_snapshot(
    customer: CustomerDocument,
    loans: list[LoanDocument],
) -> CustomerContextSnapshot:
    """Map customer and loan records to a workflow-safe context snapshot."""
    metadata: dict[str, str] = {}
    if customer.city:
        metadata["city"] = customer.city
    if customer.customer_since:
        metadata["customer_since"] = customer.customer_since

    return CustomerContextSnapshot(
        customer_id=customer.customer_id,
        display_name=customer.full_name,
        scenario_label=customer.scenario_label,
        loan_ids=[loan.loan_id for loan in loans],
        metadata=metadata,
    )
