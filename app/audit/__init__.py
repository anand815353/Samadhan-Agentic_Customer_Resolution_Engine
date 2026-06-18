"""Audit log domain module — model, repository, and service (T-024)."""

from app.audit.constants import ALL_AUDIT_EVENT_TYPES, AUDIT_LOGS_COLLECTION
from app.audit.exceptions import AuditValidationError
from app.audit.models import AuditLogDocument
from app.audit.repositories import (
    AuditLogRepository,
    InMemoryAuditLogRepository,
    MongoAuditLogRepository,
)
from app.audit.schemas import AuditEventCreate, AuditEventRead, audit_document_from_create
from app.audit.services import AuditService

__all__ = [
    "ALL_AUDIT_EVENT_TYPES",
    "AUDIT_LOGS_COLLECTION",
    "AuditEventCreate",
    "AuditEventRead",
    "AuditLogDocument",
    "AuditLogRepository",
    "AuditService",
    "AuditValidationError",
    "InMemoryAuditLogRepository",
    "MongoAuditLogRepository",
    "audit_document_from_create",
]
