"""Dependency bundle for the agent intake node."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.core.config import Settings, get_settings
from app.customers.models import CustomerDocument
from app.customers.repositories import CustomerRepository, InMemoryCustomerRepository
from app.lending.repositories import InMemoryLoanRepository, LoanRepository
from app.messages.repositories import InMemoryMessageRepository, MessageRepository
from app.messages.services import MessageService
from app.seed.demo_personas import DEMO_SEED_TIMESTAMP, demo_customer_rows
from app.tickets.repositories import InMemoryTicketRepository
from app.tickets.services import TicketService
from app.users.constants import ROLE_CUSTOMER, ROLE_SUPPORT_AGENT, ROLE_ADMIN
from app.users.models import UserDocument
from app.users.repositories import InMemoryUserRepository, UserRepository
from app.users.schemas import UserCreate, user_document_from_create

_intake_deps_override: IntakeDeps | None = None


@dataclass(frozen=True)
class IntakeDeps:
    """Injected repositories and services for intake node execution."""

    user_repository: UserRepository
    customer_repository: CustomerRepository
    loan_repository: LoanRepository
    ticket_service: TicketService
    message_service: MessageService
    message_repository: MessageRepository


def set_intake_deps_override(deps: IntakeDeps | None) -> None:
    """Override default intake dependencies (primarily for tests)."""
    global _intake_deps_override
    _intake_deps_override = deps


def build_in_memory_intake_deps(
    *,
    users: list[UserDocument] | None = None,
    customers: list[CustomerDocument] | None = None,
) -> IntakeDeps:
    """Build intake dependencies backed by in-memory repositories."""
    ticket_repository = InMemoryTicketRepository()
    ticket_service = TicketService(ticket_repository)
    message_repository = InMemoryMessageRepository()
    message_service = MessageService(message_repository, ticket_service)
    return IntakeDeps(
        user_repository=InMemoryUserRepository(users if users is not None else []),
        customer_repository=InMemoryCustomerRepository(customers if customers is not None else []),
        loan_repository=InMemoryLoanRepository(),
        ticket_service=ticket_service,
        message_service=message_service,
        message_repository=message_repository,
    )


def _demo_seed_timestamp() -> datetime:
    return datetime.fromisoformat(DEMO_SEED_TIMESTAMP)


def _demo_users() -> list[UserDocument]:
    timestamp = _demo_seed_timestamp()
    users: list[UserDocument] = []
    for index, customer in enumerate(demo_customer_rows(), start=1):
        users.append(
            user_document_from_create(
                UserCreate(
                    user_id=f"USR-CUST-{customer['customer_id'].split('-')[1]}",
                    email=str(customer["email"]),
                    password="Demo@123",
                    role=ROLE_CUSTOMER,
                    customer_id=str(customer["customer_id"]),
                    display_name=str(customer["full_name"]),
                    is_demo_user=True,
                ),
                now=timestamp,
            )
        )
    users.extend(
        [
            user_document_from_create(
                UserCreate(
                    user_id="USR-AGENT-001",
                    email="agent.demo@samadhan.ai",
                    password="Demo@123",
                    role=ROLE_SUPPORT_AGENT,
                    display_name="Demo Agent",
                    is_demo_user=True,
                ),
                now=timestamp,
            ),
            user_document_from_create(
                UserCreate(
                    user_id="USR-ADMIN-001",
                    email="admin.demo@samadhan.ai",
                    password="Demo@123",
                    role=ROLE_ADMIN,
                    display_name="Demo Admin",
                    is_demo_user=True,
                ),
                now=timestamp,
            ),
        ]
    )
    return users


def _demo_customers() -> list[CustomerDocument]:
    return [CustomerDocument.model_validate(row) for row in demo_customer_rows()]


def get_default_intake_deps(settings: Settings | None = None) -> IntakeDeps:
    """Return intake dependencies for local workflow execution."""
    if _intake_deps_override is not None:
        return _intake_deps_override

    _ = settings or get_settings()
    return build_in_memory_intake_deps(users=_demo_users(), customers=_demo_customers())
