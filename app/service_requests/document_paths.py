"""Safe mock document path builders for demo service requests."""

from __future__ import annotations


def build_mock_document_path(
    customer_id: str,
    document_type: str,
    service_request_id: str,
) -> str:
    """Return a deterministic mock path under /storage/generated_documents/."""
    return (
        f"/storage/generated_documents/{customer_id}/"
        f"{document_type}_{service_request_id}.pdf"
    )
