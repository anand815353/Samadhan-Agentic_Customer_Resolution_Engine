"""Readable fraud case ID generation and mock freeze reference formatting."""

from __future__ import annotations

import re
from datetime import UTC, datetime

FRAUD_CASE_ID_PATTERN = r"^FRD-\d{4}-\d{4}$"

_FRD_ID_RE = re.compile(FRAUD_CASE_ID_PATTERN)


def validate_fraud_case_id(fraud_case_id: str) -> bool:
    return bool(_FRD_ID_RE.match(fraud_case_id))


def parse_fraud_case_id(fraud_case_id: str) -> tuple[int, int]:
    if not validate_fraud_case_id(fraud_case_id):
        raise ValueError(f"invalid fraud case ID format: {fraud_case_id}")
    _prefix, year_str, seq_str = fraud_case_id.split("-", maxsplit=2)
    return int(year_str), int(seq_str)


def format_fraud_case_id(*, year: int, sequence: int) -> str:
    if sequence < 1 or sequence > 9999:
        raise ValueError(f"fraud case sequence out of range: {sequence}")
    return f"FRD-{year}-{sequence:04d}"


def format_freeze_reference(*, year: int, sequence: int) -> str:
    if sequence < 1 or sequence > 9999:
        raise ValueError(f"freeze reference sequence out of range: {sequence}")
    return f"MOCK-FREEZE-{year}-{sequence:04d}"


def current_fraud_case_year(*, now: datetime | None = None) -> int:
    timestamp = now or datetime.now(UTC)
    return timestamp.year


async def allocate_fraud_case_id(
    repository: object,
    *,
    year: int | None = None,
    now: datetime | None = None,
) -> str:
    target_year = year if year is not None else current_fraud_case_year(now=now)
    max_sequence = await repository.max_sequence_for_year(target_year)  # type: ignore[attr-defined]
    return format_fraud_case_id(year=target_year, sequence=max_sequence + 1)
