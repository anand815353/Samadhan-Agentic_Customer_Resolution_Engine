"""Readable ticket ID generation and validation (TKT-YYYY-NNNN).

Service request ID helpers live in app.service_requests.id_generation and are
re-exported here for backward compatibility with ticket model validation.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

TICKET_ID_PATTERN = r"^TKT-\d{4}-\d{4}$"

_TICKET_ID_RE = re.compile(TICKET_ID_PATTERN)

_SR_REEXPORTS = frozenset(
    {
        "SERVICE_REQUEST_ID_PATTERN",
        "allocate_service_request_id",
        "format_service_request_id",
        "parse_service_request_id",
        "validate_service_request_id",
    }
)


def __getattr__(name: str) -> object:
    if name in _SR_REEXPORTS:
        import importlib

        sr_id_generation = importlib.import_module("app.service_requests.id_generation")
        return getattr(sr_id_generation, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def validate_ticket_id(ticket_id: str) -> bool:
    return bool(_TICKET_ID_RE.match(ticket_id))


def parse_ticket_id(ticket_id: str) -> tuple[int, int]:
    """Return (year, sequence) from a ticket ID."""
    if not validate_ticket_id(ticket_id):
        raise ValueError(f"invalid ticket ID format: {ticket_id}")
    _prefix, year_str, seq_str = ticket_id.split("-", maxsplit=2)
    return int(year_str), int(seq_str)


def format_ticket_id(*, year: int, sequence: int) -> str:
    if sequence < 1 or sequence > 9999:
        raise ValueError(f"ticket sequence out of range: {sequence}")
    return f"TKT-{year}-{sequence:04d}"


def current_ticket_year(*, now: datetime | None = None) -> int:
    timestamp = now or datetime.now(UTC)
    return timestamp.year


async def allocate_ticket_id(
    repository: object,
    *,
    year: int | None = None,
    now: datetime | None = None,
) -> str:
    """Allocate the next ticket ID for the given year using repository sequence lookup."""
    target_year = year if year is not None else current_ticket_year(now=now)
    max_sequence = await repository.max_sequence_for_year(target_year)  # type: ignore[attr-defined]
    return format_ticket_id(year=target_year, sequence=max_sequence + 1)


if TYPE_CHECKING:
    from app.service_requests.id_generation import (  # pragma: no cover
        SERVICE_REQUEST_ID_PATTERN,
        allocate_service_request_id,
        format_service_request_id,
        parse_service_request_id,
        validate_service_request_id,
    )
