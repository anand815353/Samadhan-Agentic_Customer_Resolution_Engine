"""Readable service request ID generation and validation (SR-YYYY-NNNN)."""

from __future__ import annotations

import re
from datetime import UTC, datetime

SERVICE_REQUEST_ID_PATTERN = r"^SR-\d{4}-\d{4}$"

_SR_ID_RE = re.compile(SERVICE_REQUEST_ID_PATTERN)


def validate_service_request_id(service_request_id: str) -> bool:
    return bool(_SR_ID_RE.match(service_request_id))


def parse_service_request_id(service_request_id: str) -> tuple[int, int]:
    """Return (year, sequence) from a service request ID."""
    if not validate_service_request_id(service_request_id):
        raise ValueError(f"invalid service request ID format: {service_request_id}")
    _prefix, year_str, seq_str = service_request_id.split("-", maxsplit=2)
    return int(year_str), int(seq_str)


def format_service_request_id(*, year: int, sequence: int) -> str:
    if sequence < 1 or sequence > 9999:
        raise ValueError(f"service request sequence out of range: {sequence}")
    return f"SR-{year}-{sequence:04d}"


def current_service_request_year(*, now: datetime | None = None) -> int:
    timestamp = now or datetime.now(UTC)
    return timestamp.year


async def allocate_service_request_id(
    repository: object,
    *,
    year: int | None = None,
    now: datetime | None = None,
) -> str:
    """Allocate the next service request ID for the given year."""
    target_year = year if year is not None else current_service_request_year(now=now)
    max_sequence = await repository.max_sequence_for_year(target_year)  # type: ignore[attr-defined]
    return format_service_request_id(year=target_year, sequence=max_sequence + 1)
