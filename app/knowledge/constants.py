"""Knowledge document domain constants aligned with DATA_MODEL §10.2 and seed template_spec."""

from typing import Literal

from app.rag.constants import ALL_POLICY_DOMAINS, PolicyDomain

KNOWLEDGE_DOCUMENTS_COLLECTION = "knowledge_documents"

DOCUMENT_ID_PATTERN = r"^POL-[A-Z0-9-]+$"

DocumentType = Literal["policy", "sop", "faq", "script"]
ApprovalStatus = Literal["draft", "approved", "archived"]
IndexedStatus = Literal["not_indexed", "indexed", "failed"]

ALL_DOCUMENT_TYPES: tuple[DocumentType, ...] = ("policy", "sop", "faq", "script")
ALL_APPROVAL_STATUSES: tuple[ApprovalStatus, ...] = ("draft", "approved", "archived")
ALL_INDEXED_STATUSES: tuple[IndexedStatus, ...] = ("not_indexed", "indexed", "failed")

__all__ = [
    "ALL_APPROVAL_STATUSES",
    "ALL_DOCUMENT_TYPES",
    "ALL_INDEXED_STATUSES",
    "ALL_POLICY_DOMAINS",
    "ApprovalStatus",
    "DOCUMENT_ID_PATTERN",
    "DocumentType",
    "IndexedStatus",
    "KNOWLEDGE_DOCUMENTS_COLLECTION",
    "PolicyDomain",
]
