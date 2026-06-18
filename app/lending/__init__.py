"""Lending domain module for loan applications and loan accounts."""

from app.lending.models import LoanApplicationDocument, LoanDocument
from app.lending.repositories import (
    InMemoryLoanApplicationRepository,
    InMemoryLoanRepository,
    LoanApplicationRepository,
    LoanRepository,
    MongoLoanApplicationRepository,
    MongoLoanRepository,
)

__all__ = [
    "InMemoryLoanApplicationRepository",
    "InMemoryLoanRepository",
    "LoanApplicationDocument",
    "LoanApplicationRepository",
    "LoanDocument",
    "LoanRepository",
    "MongoLoanApplicationRepository",
    "MongoLoanRepository",
]
