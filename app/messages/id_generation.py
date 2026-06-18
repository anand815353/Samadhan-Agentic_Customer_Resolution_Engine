"""Readable message ID generation and validation (MSG-YYYY-NNNN)."""

from __future__ import annotations

import re
from datetime import UTC, datetime

MESSAGE_ID_PATTERN = r"^MSG-\d{4}-\d{4}$"

_MESSAGE_ID_RE = re.compile(MESSAGE_ID_PATTERN)


def validate_message_id(message_id: str) -> bool:
    return bool(_MESSAGE_ID_RE.match(message_id))


def parse_message_id(message_id: str) -> tuple[int, int]:
    """Return (year, sequence) from a message ID."""
    if not validate_message_id(message_id):
        raise ValueError(f"invalid message ID format: {message_id}")
    _prefix, year_str, seq_str = message_id.split("-", maxsplit=2)
    return int(year_str), int(seq_str)


def format_message_id(*, year: int, sequence: int) -> str:
    if sequence < 1 or sequence > 9999:
        raise ValueError(f"message sequence out of range: {sequence}")
    return f"MSG-{year}-{sequence:04d}"


def current_message_year(*, now: datetime | None = None) -> int:
    timestamp = now or datetime.now(UTC)
    return timestamp.year


async def allocate_message_id(
    repository: object,
    *,
    year: int | None = None,
    now: datetime | None = None,
) -> str:
    """Allocate the next message ID for the given year using repository sequence lookup."""
    target_year = year if year is not None else current_message_year(now=now)
    max_sequence = await repository.max_sequence_for_year(target_year)  # type: ignore[attr-defined]
    return format_message_id(year=target_year, sequence=max_sequence + 1)
