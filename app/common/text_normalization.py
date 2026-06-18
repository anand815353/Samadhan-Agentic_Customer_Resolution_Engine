"""Deterministic customer message normalization for agent intake."""

from __future__ import annotations

import re
import unicodedata

from app.core.exceptions import AppError


class BlankMessageError(AppError):
    """Raised when a message is empty after normalization."""


_MULTI_BLANK_LINES_RE = re.compile(r"\n{3,}")
_HORIZONTAL_WHITESPACE_RE = re.compile(r"[ \t]+")


def normalize_customer_message(raw: str) -> str:
    """Normalize customer text without changing meaning or stored raw content."""
    normalized = unicodedata.normalize("NFKC", raw)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.strip()

    lines = []
    for line in normalized.split("\n"):
        collapsed = _HORIZONTAL_WHITESPACE_RE.sub(" ", line.strip())
        lines.append(collapsed)

    normalized = "\n".join(lines)
    normalized = _MULTI_BLANK_LINES_RE.sub("\n\n", normalized).strip()
    if not normalized:
        raise BlankMessageError("customer message is empty after normalization")
    return normalized
