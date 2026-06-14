"""Canonical demo customer and user seed rows for T-016 (aligned with demo_catalog)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.demo_catalog import DEMO_ACCOUNTS
from app.seed.template_spec import (
    DEFAULT_DEMO_PASSWORD,
    SHEET_SPECS_BY_NAME,
    header_columns,
)
from app.users.constants import ROLE_ADMIN, ROLE_CUSTOMER, ROLE_SUPPORT_AGENT

DEMO_SEED_TIMESTAMP = "2026-06-13T12:00:00+00:00"


@dataclass(frozen=True)
class DemoCustomerPersona:
    customer_id: str
    full_name: str
    email: str
    scenario_label: str
    mobile: str
    pan: str
    aadhaar_last4: str
    date_of_birth: str
    city: str
    customer_since: str
    risk_segment_label: str
    folder_slug: str


@dataclass(frozen=True)
class DemoUserPersona:
    user_id: str
    email: str
    role: str
    display_name: str
    customer_id: str | None = None


DEMO_CUSTOMERS: tuple[DemoCustomerPersona, ...] = (
    DemoCustomerPersona(
        "CUST-001",
        "Ramesh Kumar",
        "ramesh.demo@samadhan.ai",
        "Loan pending due to KYC",
        "9876500101",
        "XXXXX1001A",
        "1001",
        "1988-03-14",
        "Mumbai",
        "2024-01-15",
        "standard",
        "CUST-001_Ramesh_Kumar",
    ),
    DemoCustomerPersona(
        "CUST-002",
        "Priya Sharma",
        "priya.demo@samadhan.ai",
        "Loan rejected",
        "9876500102",
        "XXXXX1002A",
        "1002",
        "1990-07-22",
        "Delhi",
        "2024-02-01",
        "standard",
        "CUST-002_Priya_Sharma",
    ),
    DemoCustomerPersona(
        "CUST-003",
        "Arjun Mehta",
        "arjun.demo@samadhan.ai",
        "Duplicate EMI debit",
        "9876500103",
        "XXXXX1003A",
        "1003",
        "1985-11-08",
        "Bangalore",
        "2023-06-10",
        "standard",
        "CUST-003_Arjun_Mehta",
    ),
    DemoCustomerPersona(
        "CUST-004",
        "Sneha Verma",
        "sneha.demo@samadhan.ai",
        "Closed loan, NOC pending",
        "9876500104",
        "XXXXX1004A",
        "1004",
        "1992-01-30",
        "Pune",
        "2022-09-05",
        "standard",
        "CUST-004_Sneha_Verma",
    ),
    DemoCustomerPersona(
        "CUST-005",
        "Imran Khan",
        "imran.demo@samadhan.ai",
        "CIBIL still showing active",
        "9876500105",
        "XXXXX1005A",
        "1005",
        "1987-05-18",
        "Hyderabad",
        "2023-03-20",
        "standard",
        "CUST-005_Imran_Khan",
    ),
    DemoCustomerPersona(
        "CUST-006",
        "Kavita Rao",
        "kavita.demo@samadhan.ai",
        "Fraud/SMS alert",
        "9876500106",
        "XXXXX1006A",
        "1006",
        "1991-09-12",
        "Chennai",
        "2024-04-01",
        "elevated",
        "CUST-006_Kavita_Rao",
    ),
    DemoCustomerPersona(
        "CUST-007",
        "Mohit Jain",
        "mohit.demo@samadhan.ai",
        "Eligible top-up offer",
        "9876500107",
        "XXXXX1007A",
        "1007",
        "1989-12-03",
        "Ahmedabad",
        "2023-11-15",
        "preferred",
        "CUST-007_Mohit_Jain",
    ),
    DemoCustomerPersona(
        "CUST-008",
        "Neha Singh",
        "neha.demo@samadhan.ai",
        "Not eligible for top-up",
        "9876500108",
        "XXXXX1008A",
        "1008",
        "1993-04-25",
        "Jaipur",
        "2024-05-10",
        "standard",
        "CUST-008_Neha_Singh",
    ),
    DemoCustomerPersona(
        "CUST-009",
        "Farhan Ali",
        "farhan.demo@samadhan.ai",
        "RM callback",
        "9876500109",
        "XXXXX1009A",
        "1009",
        "1986-08-07",
        "Lucknow",
        "2023-08-22",
        "preferred",
        "CUST-009_Farhan_Ali",
    ),
    DemoCustomerPersona(
        "CUST-010",
        "Anita Das",
        "anita.demo@samadhan.ai",
        "Loan statement request",
        "9876500110",
        "XXXXX1010A",
        "1010",
        "1994-02-16",
        "Kolkata",
        "2024-06-01",
        "standard",
        "CUST-010_Anita_Das",
    ),
)

DEMO_USERS: tuple[DemoUserPersona, ...] = tuple(
    DemoUserPersona(
        user_id=f"USR-CUST-{customer.customer_id.split('-')[1]}",
        email=customer.email,
        role=ROLE_CUSTOMER,
        display_name=customer.full_name,
        customer_id=customer.customer_id,
    )
    for customer in DEMO_CUSTOMERS
) + (
    DemoUserPersona(
        "USR-AGENT-001",
        "agent.demo@samadhan.ai",
        ROLE_SUPPORT_AGENT,
        "Demo Agent",
    ),
    DemoUserPersona(
        "USR-ADMIN-001",
        "admin.demo@samadhan.ai",
        ROLE_ADMIN,
        "Demo Admin",
    ),
)


def _customer_folder_path(persona: DemoCustomerPersona) -> str:
    return f"data/seed/customers/{persona.folder_slug}/"


def demo_customer_rows() -> list[dict[str, Any]]:
    """Return customer sheet rows keyed by column name."""
    rows: list[dict[str, Any]] = []
    for persona in DEMO_CUSTOMERS:
        rows.append(
            {
                "customer_id": persona.customer_id,
                "full_name": persona.full_name,
                "email": persona.email,
                "mobile": persona.mobile,
                "pan": persona.pan,
                "scenario_label": persona.scenario_label,
                "folder_path": _customer_folder_path(persona),
                "aadhaar_last4": persona.aadhaar_last4,
                "date_of_birth": persona.date_of_birth,
                "city": persona.city,
                "customer_since": persona.customer_since,
                "risk_segment_label": persona.risk_segment_label,
                "created_at": DEMO_SEED_TIMESTAMP,
                "updated_at": DEMO_SEED_TIMESTAMP,
            }
        )
    return rows


def demo_user_rows() -> list[dict[str, Any]]:
    """Return users sheet rows keyed by column name."""
    rows: list[dict[str, Any]] = []
    for persona in DEMO_USERS:
        row: dict[str, Any] = {
            "user_id": persona.user_id,
            "email": persona.email,
            "password": DEFAULT_DEMO_PASSWORD,
            "role": persona.role,
            "display_name": persona.display_name,
            "is_demo_user": True,
            "is_active": True,
        }
        if persona.customer_id is not None:
            row["customer_id"] = persona.customer_id
        rows.append(row)
    return rows


def demo_customer_row_values() -> list[list[Any]]:
    """Return customer rows ordered for Excel append."""
    columns = header_columns(SHEET_SPECS_BY_NAME["customers"])
    return [
        [row.get(column) for column in columns]
        for row in demo_customer_rows()
    ]


def demo_user_row_values() -> list[list[Any]]:
    """Return user rows ordered for Excel append."""
    columns = header_columns(SHEET_SPECS_BY_NAME["users"])
    return [
        [row.get(column) for column in columns]
        for row in demo_user_rows()
    ]


def customer_folder_paths() -> tuple[str, ...]:
    """Relative folder paths for all demo customers."""
    return tuple(_customer_folder_path(persona) for persona in DEMO_CUSTOMERS)


def catalog_alignment_errors() -> list[str]:
    """Return mismatches between demo personas and demo_catalog DEMO_ACCOUNTS."""
    errors: list[str] = []
    customer_accounts = [
        account for account in DEMO_ACCOUNTS if account["category"] == "customer"
    ]
    if len(customer_accounts) != len(DEMO_CUSTOMERS):
        errors.append(
            f"expected {len(DEMO_CUSTOMERS)} customer accounts in demo_catalog, "
            f"found {len(customer_accounts)}"
        )

    persona_by_email = {customer.email: customer for customer in DEMO_CUSTOMERS}
    for account in customer_accounts:
        persona = persona_by_email.get(account["email"])
        if persona is None:
            errors.append(f"missing demo persona for email {account['email']}")
            continue
        if persona.scenario_label != account["scenario"]:
            errors.append(
                f"scenario mismatch for {account['email']}: "
                f"persona={persona.scenario_label!r} catalog={account['scenario']!r}"
            )

    staff_emails = {
        "agent.demo@samadhan.ai": ROLE_SUPPORT_AGENT,
        "admin.demo@samadhan.ai": ROLE_ADMIN,
    }
    for email, role in staff_emails.items():
        user = next((u for u in DEMO_USERS if u.email == email), None)
        if user is None:
            errors.append(f"missing demo user for {email}")
        elif user.role != role:
            errors.append(f"role mismatch for {email}: {user.role} != {role}")

    return errors
