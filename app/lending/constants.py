"""Lending domain constants aligned with DATA_MODEL §6."""

from typing import Literal

LOAN_APPLICATIONS_COLLECTION = "loan_applications"
LOANS_COLLECTION = "loans"

ApplicationStatus = Literal["pending", "approved", "rejected", "cancelled"]
LoanStatus = Literal["active", "closed", "pending_disbursal", "written_off"]
NocStatus = Literal["not_applicable", "pending", "generated", "delivered"]
BureauStatus = Literal["reported_active", "reported_closed", "pending_update"]
