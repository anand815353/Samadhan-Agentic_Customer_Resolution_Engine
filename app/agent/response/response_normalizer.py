"""Normalize customer response text (T-061)."""

from __future__ import annotations

import re

from app.agent.response.response_types import RESPONSE_MAX_CHARACTERS


def normalize_response_text(text: str) -> str:
    """Trim, collapse whitespace, and enforce maximum length."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    if len(normalized) > RESPONSE_MAX_CHARACTERS:
        normalized = normalized[: RESPONSE_MAX_CHARACTERS - 3].rstrip() + "..."
    return normalized
