"""Deterministic policy document chunking for extracted text (T-041)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.config import Settings, get_settings
from app.rag.chunk_schemas import DocumentChunkingResult, PolicyDocumentChunk
from app.rag.extraction_schemas import DocumentExtractionResult, SupportedFileType

if TYPE_CHECKING:
    from app.knowledge.models import KnowledgeDocumentDocument

_HEADING_PATTERN = re.compile(r"^(#{1,2})\s+(.+)$", re.MULTILINE)
_INTERNAL_ONLY_SOP_DOMAINS = frozenset({"emi", "fraud"})


@dataclass(frozen=True)
class _TextSegment:
    text: str
    section_heading: str | None = None


def derive_chunk_visibility(document_type: str, domain: str) -> tuple[bool, bool]:
    """Return customer_visible and internal_only flags aligned with T-038 stub rules."""
    if document_type == "sop" and domain in _INTERNAL_ONLY_SOP_DOMAINS:
        return False, True
    return True, False


class DocumentChunker:
    """Split extracted policy text into metadata-rich chunks."""

    def __init__(
        self,
        *,
        chunk_size_chars: int | None = None,
        chunk_overlap_chars: int | None = None,
        chunk_min_chars: int | None = None,
        settings: Settings | None = None,
    ) -> None:
        resolved = settings or get_settings()
        self._chunk_size = chunk_size_chars if chunk_size_chars is not None else resolved.rag_chunk_size_chars
        self._chunk_overlap = (
            chunk_overlap_chars if chunk_overlap_chars is not None else resolved.rag_chunk_overlap_chars
        )
        self._chunk_min = chunk_min_chars if chunk_min_chars is not None else resolved.rag_chunk_min_chars
        if self._chunk_overlap >= self._chunk_size:
            raise ValueError("chunk_overlap_chars must be smaller than chunk_size_chars")

    def chunk(
        self,
        extraction: DocumentExtractionResult,
        metadata: KnowledgeDocumentDocument,
    ) -> DocumentChunkingResult:
        if not extraction.success:
            error = extraction.error or "empty extraction text"
            return DocumentChunkingResult(
                chunks=[],
                warnings=list(extraction.warnings),
                error=error,
            )
        result = self.chunk_text(
            extraction.text,
            metadata,
            file_type=extraction.file_type,
            source_filename=extraction.source_filename,
        )
        if extraction.warnings:
            result = result.model_copy(
                update={"warnings": [*extraction.warnings, *result.warnings]}
            )
        return result

    def chunk_text(
        self,
        text: str,
        metadata: KnowledgeDocumentDocument,
        *,
        file_type: SupportedFileType | None = None,
        source_filename: str | None = None,
    ) -> DocumentChunkingResult:
        normalized = text.strip()
        if not normalized:
            return DocumentChunkingResult(chunks=[], error="empty extraction text")

        filename = source_filename or metadata.source_filename
        segments = (
            _split_markdown_sections(normalized)
            if file_type == "md"
            else [_TextSegment(text=normalized)]
        )

        raw_chunks: list[_TextSegment] = []
        for segment in segments:
            if len(segment.text) <= self._chunk_size:
                raw_chunks.append(segment)
                continue
            for piece in _recursive_char_split(
                segment.text,
                chunk_size=self._chunk_size,
                chunk_overlap=self._chunk_overlap,
            ):
                raw_chunks.append(
                    _TextSegment(text=piece, section_heading=segment.section_heading)
                )

        filtered = _filter_segments(raw_chunks, min_chars=self._chunk_min)
        if not filtered:
            return DocumentChunkingResult(chunks=[], error="no non-empty chunks produced")

        chunks = [
            _build_chunk(
                metadata,
                chunk_index=index,
                chunk_text=segment.text.strip(),
                section_heading=segment.section_heading,
                source_filename=filename,
            )
            for index, segment in enumerate(filtered)
        ]
        return DocumentChunkingResult(chunks=chunks)


def _split_markdown_sections(text: str) -> list[_TextSegment]:
    matches = list(_HEADING_PATTERN.finditer(text))
    if not matches:
        return [_TextSegment(text=text)]

    sections: list[_TextSegment] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        if not section_text:
            continue
        heading = match.group(2).strip()
        sections.append(_TextSegment(text=section_text, section_heading=heading))

    if not sections:
        return [_TextSegment(text=text)]
    return sections


def _recursive_char_split(
    text: str,
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        if end < text_len:
            split_at = _find_split_point(text, start, end)
            if split_at > start:
                end = split_at
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= text_len:
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks


def _find_split_point(text: str, start: int, end: int) -> int:
    window = text[start:end]
    for separator in ("\n\n", "\n", ". ", " "):
        pos = window.rfind(separator)
        if pos > 0:
            return start + pos + len(separator)
    return end


def _filter_segments(segments: list[_TextSegment], *, min_chars: int) -> list[_TextSegment]:
    filtered: list[_TextSegment] = []
    for segment in segments:
        stripped = segment.text.strip()
        if len(stripped) < min_chars:
            if filtered:
                merged_text = f"{filtered[-1].text.rstrip()}\n\n{stripped}".strip()
                filtered[-1] = _TextSegment(
                    text=merged_text,
                    section_heading=filtered[-1].section_heading or segment.section_heading,
                )
            continue
        filtered.append(_TextSegment(text=stripped, section_heading=segment.section_heading))
    return filtered


def _build_chunk(
    metadata: KnowledgeDocumentDocument,
    *,
    chunk_index: int,
    chunk_text: str,
    section_heading: str | None,
    source_filename: str,
) -> PolicyDocumentChunk:
    customer_visible, internal_only = derive_chunk_visibility(
        metadata.document_type,
        metadata.domain,
    )
    return PolicyDocumentChunk(
        document_id=metadata.document_id,
        title=metadata.title,
        document_type=metadata.document_type,
        domain=metadata.domain,
        version=metadata.version,
        effective_date=str(metadata.effective_date),
        approval_status=metadata.approval_status,
        chunk_index=chunk_index,
        chunk_text=chunk_text,
        source_filename=source_filename,
        section_heading=section_heading,
        customer_visible=customer_visible,
        internal_only=internal_only,
    )
