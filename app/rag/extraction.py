"""Local policy document text extraction for supported knowledge-base formats (T-040)."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from pypdf import PdfReader

from app.rag.extraction_schemas import DocumentExtractionResult, SupportedFileType

if TYPE_CHECKING:
    from app.knowledge.models import KnowledgeDocumentDocument

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".md", ".txt", ".pdf"})
MAX_EXTRACTION_BYTES = 10 * 1024 * 1024


class DocumentTextExtractor:
    """Extract plain text from local policy/SOP files (.md, .txt, text PDFs)."""

    def __init__(
        self,
        *,
        app_root: Path,
        max_bytes: int = MAX_EXTRACTION_BYTES,
    ) -> None:
        self._app_root = app_root.resolve()
        self._max_bytes = max_bytes

    def extract_path(
        self,
        storage_path: str,
        *,
        source_filename: str | None = None,
    ) -> DocumentExtractionResult:
        filename = source_filename or Path(storage_path).name
        base_result = DocumentExtractionResult(
            text="",
            source_filename=filename,
        )

        if ".." in Path(storage_path).parts:
            return base_result.model_copy(
                update={"error": f"invalid storage_path: {storage_path}"}
            )

        if Path(storage_path).is_absolute():
            return base_result.model_copy(
                update={"error": f"absolute storage_path not allowed: {storage_path}"}
            )

        resolved = (self._app_root / storage_path).resolve()
        if not self._is_within_app_root(resolved):
            return base_result.model_copy(
                update={"error": f"storage_path escapes app root: {storage_path}"}
            )

        if not resolved.is_file():
            return base_result.model_copy(
                update={"error": f"file not found: {storage_path}"}
            )

        if source_filename is not None and resolved.name != source_filename:
            return base_result.model_copy(
                update={"error": "storage_path basename mismatch with source_filename"}
            )

        file_size = resolved.stat().st_size
        if file_size > self._max_bytes:
            return base_result.model_copy(
                update={"error": f"file exceeds max extraction size ({self._max_bytes} bytes)"}
            )

        suffix = resolved.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            return base_result.model_copy(
                update={"error": f"unsupported file type: {suffix or '(none)'}"}
            )

        file_type: SupportedFileType = suffix.lstrip(".")  # type: ignore[assignment]
        if suffix in {".md", ".txt"}:
            return self._extract_text_file(resolved, file_type=file_type, base=base_result)
        return self._extract_pdf(resolved, base=base_result)

    def extract_from_metadata(
        self,
        document: KnowledgeDocumentDocument,
    ) -> DocumentExtractionResult:
        return self.extract_path(
            document.storage_path,
            source_filename=document.source_filename,
        )

    def _is_within_app_root(self, resolved: Path) -> bool:
        try:
            resolved.relative_to(self._app_root)
        except ValueError:
            return False
        return True

    def _extract_text_file(
        self,
        path: Path,
        *,
        file_type: SupportedFileType,
        base: DocumentExtractionResult,
    ) -> DocumentExtractionResult:
        try:
            raw_text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return base.model_copy(
                update={
                    "file_type": file_type,
                    "error": f"file is not valid UTF-8: {path.name}",
                }
            )
        except OSError as exc:
            return base.model_copy(
                update={
                    "file_type": file_type,
                    "error": f"failed to read file: {exc}",
                }
            )

        text = raw_text.rstrip()
        warnings: list[str] = []
        if not text.strip():
            return base.model_copy(
                update={
                    "file_type": file_type,
                    "page_count": 1,
                    "error": "file is empty",
                }
            )

        return base.model_copy(
            update={
                "text": text,
                "file_type": file_type,
                "page_count": 1,
                "warnings": warnings,
            }
        )

    def _extract_pdf(
        self,
        path: Path,
        *,
        base: DocumentExtractionResult,
    ) -> DocumentExtractionResult:
        try:
            pdf_bytes = path.read_bytes()
            reader = PdfReader(BytesIO(pdf_bytes))
        except OSError as exc:
            return base.model_copy(
                update={"file_type": "pdf", "error": f"failed to read file: {exc}"}
            )
        except Exception as exc:  # noqa: BLE001 — controlled extraction boundary
            return base.model_copy(
                update={"file_type": "pdf", "error": f"pdf parsing failed: {exc}"}
            )

        page_count = len(reader.pages)
        warnings: list[str] = []
        page_texts: list[str] = []
        empty_pages = 0

        for page in reader.pages:
            try:
                page_text = page.extract_text() or ""
            except Exception:  # noqa: BLE001
                page_text = ""
            cleaned = page_text.rstrip()
            if cleaned.strip():
                page_texts.append(cleaned)
            else:
                empty_pages += 1

        if empty_pages:
            warnings.append(f"{empty_pages} page(s) contained no extractable text")

        combined = "\n\n".join(page_texts).strip()
        if not combined:
            return base.model_copy(
                update={
                    "file_type": "pdf",
                    "page_count": page_count,
                    "warnings": [
                        *warnings,
                        "possible scanned pdf; OCR not supported in MVP",
                    ],
                    "error": "pdf contains no extractable text",
                }
            )

        return base.model_copy(
            update={
                "text": combined,
                "file_type": "pdf",
                "page_count": page_count,
                "warnings": warnings,
            }
        )
