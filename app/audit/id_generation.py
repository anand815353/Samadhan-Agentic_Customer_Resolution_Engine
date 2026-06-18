"""Readable audit log ID generation and validation (AUD-YYYY-NNNN)."""

from __future__ import annotations

import re
from datetime import UTC, datetime

AUDIT_ID_PATTERN = r"^AUD-\d{4}-\d{4}$"

_AUDIT_ID_RE = re.compile(AUDIT_ID_PATTERN)


def validate_audit_id(audit_id: str) -> bool:
    return bool(_AUDIT_ID_RE.match(audit_id))


def parse_audit_id(audit_id: str) -> tuple[int, int]:
    """Return (year, sequence) from an audit ID."""
    if not validate_audit_id(audit_id):
        raise ValueError(f"invalid audit ID format: {audit_id}")
    _prefix, year_str, seq_str = audit_id.split("-", maxsplit=2)
    return int(year_str), int(seq_str)


def format_audit_id(*, year: int, sequence: int) -> str:
    if sequence < 1 or sequence > 9999:
        raise ValueError(f"audit sequence out of range: {sequence}")
    return f"AUD-{year}-{sequence:04d}"


def current_audit_year(*, now: datetime | None = None) -> int:
    timestamp = now or datetime.now(UTC)
    return timestamp.year


async def allocate_audit_id(
    repository: object,
    *,
    year: int | None = None,
    now: datetime | None = None,
) -> str:
    """Allocate the next audit ID for the given year using repository sequence lookup."""
    target_year = year if year is not None else current_audit_year(now=now)
    max_sequence = await repository.max_sequence_for_year(target_year)  # type: ignore[attr-defined]
    return format_audit_id(year=target_year, sequence=max_sequence + 1)
