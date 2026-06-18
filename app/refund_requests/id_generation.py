"""Readable refund request ID generation and validation (REF-YYYY-NNNN)."""

from __future__ import annotations

import re
from datetime import UTC, datetime

REFUND_REQUEST_ID_PATTERN = r"^REF-\d{4}-\d{4}$"

_REF_ID_RE = re.compile(REFUND_REQUEST_ID_PATTERN)


def validate_refund_request_id(refund_request_id: str) -> bool:
    return bool(_REF_ID_RE.match(refund_request_id))


def parse_refund_request_id(refund_request_id: str) -> tuple[int, int]:
    if not validate_refund_request_id(refund_request_id):
        raise ValueError(f"invalid refund request ID format: {refund_request_id}")
    _prefix, year_str, seq_str = refund_request_id.split("-", maxsplit=2)
    return int(year_str), int(seq_str)


def format_refund_request_id(*, year: int, sequence: int) -> str:
    if sequence < 1 or sequence > 9999:
        raise ValueError(f"refund request sequence out of range: {sequence}")
    return f"REF-{year}-{sequence:04d}"


def current_refund_request_year(*, now: datetime | None = None) -> int:
    timestamp = now or datetime.now(UTC)
    return timestamp.year


async def allocate_refund_request_id(
    repository: object,
    *,
    year: int | None = None,
    now: datetime | None = None,
) -> str:
    target_year = year if year is not None else current_refund_request_year(now=now)
    max_sequence = await repository.max_sequence_for_year(target_year)  # type: ignore[attr-defined]
    return format_refund_request_id(year=target_year, sequence=max_sequence + 1)
