"""Admin policy indexing orchestration (T-045)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.admin.schemas import AdminPolicyRow, AdminReindexResult
from app.audit.schemas import AuditEventCreate
from app.core.exceptions import NotFoundError

if TYPE_CHECKING:
    from app.audit.services import AuditService
    from app.knowledge.models import KnowledgeDocumentDocument
    from app.knowledge.services import KnowledgeDocumentService
    from app.rag.indexing import PolicyDocumentIndexingService
    from app.rag.indexing_schemas import DocumentIndexingResult

_ACTIVE_REINDEX: set[str] = set()
_DOCUMENT_ID_RE = re.compile(r"^POL-[A-Z0-9-]+$")


class AdminPolicyIndexingService:
    """Admin-facing policy list and re-index operations."""

    def __init__(
        self,
        knowledge_service: KnowledgeDocumentService,
        indexing_service: PolicyDocumentIndexingService,
        audit_service: AuditService,
        *,
        app_root: Path,
    ) -> None:
        from app.rag.extraction import DocumentTextExtractor

        self._knowledge_service = knowledge_service
        self._indexing_service = indexing_service
        self._audit_service = audit_service
        self._extractor = DocumentTextExtractor(app_root=app_root)
        self._app_root = app_root.resolve()

    async def list_documents(self, *, limit: int = 100) -> list[AdminPolicyRow]:
        documents = await self._knowledge_service.list_metadata(limit=limit)
        documents.sort(key=lambda item: (item.domain, item.document_id))
        return [self._to_admin_row(document) for document in documents]

    async def reindex_document(
        self,
        document_id: str,
        *,
        admin_user_id: str,
    ) -> AdminReindexResult:
        normalized_id = document_id.strip()
        if not _DOCUMENT_ID_RE.fullmatch(normalized_id):
            return AdminReindexResult(
                document_id=normalized_id,
                success=False,
                message="invalid document ID format",
                error_category="eligibility",
            )

        if normalized_id in _ACTIVE_REINDEX:
            return AdminReindexResult(
                document_id=normalized_id,
                success=False,
                message="Indexing already in progress for this document",
                error_category="busy",
            )

        _ACTIVE_REINDEX.add(normalized_id)
        try:
            try:
                metadata = await self._knowledge_service.get_metadata(normalized_id)
            except NotFoundError:
                result = AdminReindexResult(
                    document_id=normalized_id,
                    success=False,
                    message="knowledge document not found",
                    error_category="not_found",
                )
                await self._record_audit(admin_user_id, result, indexed_status=None)
                return result

            eligibility_error = self._check_eligibility(metadata)
            if eligibility_error is not None:
                result = AdminReindexResult(
                    document_id=normalized_id,
                    success=False,
                    message=eligibility_error,
                    error_category="eligibility",
                )
                await self._record_audit(
                    admin_user_id,
                    result,
                    indexed_status=metadata.indexed_status,
                )
                return result

            index_result = await self._indexing_service.index_document(normalized_id)
            refreshed = await self._knowledge_service.get_metadata(normalized_id)
            result = self._map_index_result(index_result, refreshed)
            await self._record_audit(
                admin_user_id,
                result,
                indexed_status=refreshed.indexed_status,
            )
            return result
        finally:
            _ACTIVE_REINDEX.discard(normalized_id)

    def _to_admin_row(self, document: KnowledgeDocumentDocument) -> AdminPolicyRow:
        eligibility_error = self._check_eligibility(document)
        indexed_at = str(document.indexed_at) if document.indexed_at is not None else None
        return AdminPolicyRow(
            document_id=document.document_id,
            title=document.title,
            domain=document.domain,
            approval_status=document.approval_status,
            indexed_status=document.indexed_status,
            chunk_count=document.chunk_count,
            indexed_at=indexed_at,
            source_filename=document.source_filename,
            reindex_eligible=eligibility_error is None,
            ineligible_reason=eligibility_error,
        )

    def _check_eligibility(self, document: KnowledgeDocumentDocument) -> str | None:
        from app.rag.extraction import SUPPORTED_EXTENSIONS

        if document.approval_status != "approved":
            return "only approved documents can be indexed"
        if not _DOCUMENT_ID_RE.fullmatch(document.document_id):
            return "invalid document ID format"

        suffix = Path(document.source_filename).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            return "unsupported source file type"

        extraction = self._extractor.extract_from_metadata(document)
        if not extraction.success:
            return extraction.error or "source file is not readable"
        return None

    def _map_index_result(
        self,
        index_result: DocumentIndexingResult,
        metadata: KnowledgeDocumentDocument,
    ) -> AdminReindexResult:
        indexed_at = (
            str(metadata.indexed_at)
            if metadata.indexed_at is not None
            else (
                str(index_result.indexed_at)
                if index_result.indexed_at is not None
                else None
            )
        )
        if index_result.success:
            return AdminReindexResult(
                document_id=index_result.document_id,
                success=True,
                chunk_count=index_result.chunk_count,
                indexed_at=indexed_at,
                message="Policy document indexed successfully",
            )

        error_message = self._safe_error_message(index_result.error)
        return AdminReindexResult(
            document_id=index_result.document_id,
            success=False,
            chunk_count=metadata.chunk_count,
            indexed_at=indexed_at if metadata.indexed_status == "indexed" else None,
            message=error_message,
            error_category=self._categorize_error(index_result.error),
        )

    @staticmethod
    def _safe_error_message(error: str | None) -> str:
        if not error:
            return "Policy indexing failed"
        lowered = error.lower()
        if "api_key" in lowered or "secret" in lowered or "password" in lowered:
            return "Policy indexing failed due to configuration error"
        if "traceback" in lowered or "exception" in lowered:
            return "Policy indexing failed"
        return error[:240]

    @staticmethod
    def _categorize_error(error: str | None) -> str | None:
        if not error:
            return "unknown"
        lowered = error.lower()
        if "extraction" in lowered or "extract" in lowered or "storage_path" in lowered:
            return "extraction"
        if "chunk" in lowered:
            return "chunking"
        if "embedding" in lowered:
            return "embedding"
        if "qdrant" in lowered:
            return "qdrant"
        if "not found" in lowered:
            return "not_found"
        return "indexing"

    async def _record_audit(
        self,
        admin_user_id: str,
        result: AdminReindexResult,
        *,
        indexed_status: str | None,
    ) -> None:
        summary: dict[str, Any] = {
            "document_id": result.document_id,
            "success": result.success,
            "chunk_count": result.chunk_count,
            "indexed_status": indexed_status,
            "error_category": result.error_category,
        }
        await self._audit_service.create_event(
            AuditEventCreate(
                event_type="tool_called",
                tool_name="AdminPolicyReindex",
                tool_output_summary=summary,
                action_taken="policy_reindex_success" if result.success else "policy_reindex_failed",
                user_id=admin_user_id,
                created_by="admin",
                metadata={"document_id": result.document_id},
            ),
            validate_links=False,
        )
