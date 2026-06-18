"""Deterministic sensitive-data masking utilities for audit, tools, and UI layers."""

from __future__ import annotations

import re
from typing import Any

MASKED_MARKER = "****"
REDACTED_PLACEHOLDER = "[REDACTED]"

_PAN_FULL_RE = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$")
_PAN_SEARCH_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
_MOBILE_FULL_RE = re.compile(r"^(?:\+91[\s-]?)?([6-9]\d{9})$")
_MOBILE_SEARCH_RE = re.compile(r"\b[6-9]\d{9}\b")
_AADHAAR_FULL_RE = re.compile(r"^(\d{4})[-\s]?(\d{4})[-\s]?(\d{4})$")
_AADHAAR_SEARCH_RE = re.compile(r"\b(\d{4})[-\s]?(\d{4})[-\s]?(\d{4})\b")
_LOAN_FULL_RE = re.compile(r"^LN[-\s\dA-Z]+$", re.IGNORECASE)
_LOAN_SEARCH_RE = re.compile(r"\bLN[-\s\dA-Z]{4,}\b", re.IGNORECASE)
_EMAIL_FULL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_EMAIL_SEARCH_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_TXN_REF_FULL_RE = re.compile(r"^[A-Za-z]+\d+$")
_REF_TXN_FULL_RE = re.compile(r"^REF[-\s\dA-Z]+$", re.IGNORECASE)
_TXN_REF_SEARCH_RE = re.compile(r"\b[A-Za-z]{3,}\d{4,}\b")
_REF_TXN_SEARCH_RE = re.compile(r"\bREF-TXN-\d{4}-\d{4}\b", re.IGNORECASE)

SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "pan",
        "mobile",
        "phone",
        "aadhaar",
        "aadhaar_number",
        "aadhaar_last4",
        "email",
        "customer_email",
        "loan_account_number",
        "loan_account",
        "account_number",
        "transaction_reference",
        "reference_number",
        "tool_input",
        "tool_output",
        "raw_payload",
        "prompt",
        "stack_trace",
    }
)

_REDACTED_KEYS: frozenset[str] = frozenset({"prompt", "stack_trace"})
_RECURSIVE_CONTAINER_KEYS: frozenset[str] = frozenset(
    {"tool_input", "tool_output", "raw_payload"}
)


def _is_already_masked(value: str) -> bool:
    if REDACTED_PLACEHOLDER in value:
        return True
    if MASKED_MARKER in value:
        return True
    if "XXXX-XXXX" in value:
        return True
    return False


def mask_pan(value: Any) -> Any:
    if value is None or not isinstance(value, str):
        return value
    text = value.strip()
    if not text or _is_already_masked(text):
        return value
    normalized = text.upper()
    if not _PAN_FULL_RE.match(normalized):
        return value
    return f"{normalized[:5]}{MASKED_MARKER}{normalized[-1]}"


def mask_mobile(value: Any) -> Any:
    if value is None or not isinstance(value, str):
        return value
    text = value.strip()
    if not text or _is_already_masked(text):
        return value
    match = _MOBILE_FULL_RE.match(text)
    if not match:
        return value
    digits = match.group(1)
    return f"{digits[:2]}{'******'}{digits[-2:]}"


def mask_aadhaar(value: Any) -> Any:
    if value is None or not isinstance(value, str):
        return value
    text = value.strip()
    if not text or _is_already_masked(text):
        return value
    match = _AADHAAR_FULL_RE.match(text)
    if not match:
        return value
    last4 = match.group(3)
    return f"XXXX-XXXX-{last4}"


def mask_loan_account(value: Any) -> Any:
    if value is None or not isinstance(value, str):
        return value
    text = value.strip()
    if not text or _is_already_masked(text):
        return value
    if not _LOAN_FULL_RE.match(text):
        return value
    cleaned = re.sub(r"[-\s]", "", text).upper()
    if len(cleaned) < 6:
        return value
    return f"LN{'******'}{cleaned[-4:]}"


def mask_email(value: Any) -> Any:
    if value is None or not isinstance(value, str):
        return value
    text = value.strip()
    if not text or _is_already_masked(text):
        return value
    if not _EMAIL_FULL_RE.match(text):
        return value
    local, domain = text.split("@", maxsplit=1)
    if not local:
        return value
    return f"{local[0]}*****@{domain}"


def mask_transaction_reference(value: Any) -> Any:
    if value is None or not isinstance(value, str):
        return value
    text = value.strip()
    if not text or _is_already_masked(text):
        return value
    if _REF_TXN_FULL_RE.match(text):
        cleaned = re.sub(r"[-\s]", "", text).upper()
        if len(cleaned) < 6:
            return value
        return f"REF{MASKED_MARKER}{cleaned[-4:]}"
    if len(text) < 6 or not _TXN_REF_FULL_RE.match(text):
        return value
    prefix = re.match(r"^[A-Za-z]+", text)
    if not prefix:
        return value
    alpha = prefix.group(0)
    digits = text[len(alpha) :]
    if len(digits) < 2:
        return value
    return f"{alpha}{MASKED_MARKER}{digits[-2:]}"


def _mask_string_by_format(value: str) -> str:
    for masker in (
        mask_pan,
        mask_mobile,
        mask_aadhaar,
        mask_email,
        mask_loan_account,
        mask_transaction_reference,
    ):
        masked = masker(value)
        if isinstance(masked, str) and masked != value:
            return masked
    return value


def contains_unmasked_pan(text: str) -> bool:
    if _is_already_masked(text):
        return False
    return bool(_PAN_SEARCH_RE.search(text.upper()))


def contains_unmasked_mobile(text: str) -> bool:
    if _is_already_masked(text):
        return False
    return bool(_MOBILE_SEARCH_RE.search(text))


def contains_unmasked_aadhaar(text: str) -> bool:
    if _is_already_masked(text):
        return False
    for match in _AADHAAR_SEARCH_RE.finditer(text):
        groups = match.groups()
        if any(group.upper().startswith("X") for group in groups):
            continue
        return True
    return False


def contains_unmasked_loan_account(text: str) -> bool:
    if _is_already_masked(text):
        return False
    for match in _LOAN_SEARCH_RE.finditer(text):
        token = match.group(0)
        if "******" in token or MASKED_MARKER in token:
            continue
        return True
    return False


def contains_unmasked_email(text: str) -> bool:
    if _is_already_masked(text):
        return False
    for match in _EMAIL_SEARCH_RE.finditer(text):
        email = match.group(0)
        if "*****@" in email:
            continue
        return True
    return False


def contains_unmasked_transaction_reference(text: str) -> bool:
    if _is_already_masked(text):
        return False
    for match in _REF_TXN_SEARCH_RE.finditer(text):
        token = match.group(0)
        if MASKED_MARKER in token:
            continue
        return True
    for match in _TXN_REF_SEARCH_RE.finditer(text):
        token = match.group(0)
        if MASKED_MARKER in token:
            continue
        return True
    return False


def contains_unmasked_sensitive_text(text: str) -> bool:
    return (
        contains_unmasked_pan(text)
        or contains_unmasked_mobile(text)
        or contains_unmasked_aadhaar(text)
        or contains_unmasked_loan_account(text)
        or contains_unmasked_email(text)
        or contains_unmasked_transaction_reference(text)
    )


def sensitive_violation_kind(text: str) -> str | None:
    """Return the first detected unmasked sensitive data category, if any."""
    if contains_unmasked_pan(text):
        return "PAN-like"
    if contains_unmasked_mobile(text):
        return "mobile-like"
    if contains_unmasked_aadhaar(text):
        return "Aadhaar-like"
    if contains_unmasked_loan_account(text):
        return "loan-account-like"
    if contains_unmasked_email(text):
        return "email-like"
    if contains_unmasked_transaction_reference(text):
        return "transaction-reference-like"
    return None


def mask_value_by_key(key: str, value: Any) -> Any:
    normalized = key.lower()

    if normalized in _REDACTED_KEYS:
        if isinstance(value, str):
            return REDACTED_PLACEHOLDER
        return mask_sensitive_data(value)

    if normalized in _RECURSIVE_CONTAINER_KEYS:
        return mask_sensitive_data(value)

    if normalized == "pan":
        return mask_pan(value) if isinstance(value, str) else mask_sensitive_data(value)
    if normalized in {"mobile", "phone"}:
        return mask_mobile(value) if isinstance(value, str) else mask_sensitive_data(value)
    if normalized in {"aadhaar", "aadhaar_number"}:
        return mask_aadhaar(value) if isinstance(value, str) else mask_sensitive_data(value)
    if normalized == "aadhaar_last4":
        return value
    if normalized in {"loan_account_number", "loan_account", "account_number"}:
        return mask_loan_account(value) if isinstance(value, str) else mask_sensitive_data(value)
    if normalized in {"email", "customer_email"}:
        return mask_email(value) if isinstance(value, str) else mask_sensitive_data(value)
    if normalized in {"transaction_reference", "reference_number"}:
        return (
            mask_transaction_reference(value)
            if isinstance(value, str)
            else mask_sensitive_data(value)
        )

    if isinstance(value, dict):
        return {item_key: mask_value_by_key(item_key, item_value) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [mask_sensitive_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(mask_sensitive_data(item) for item in value)

    return value


def mask_sensitive_data(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {key: mask_value_by_key(key, value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [mask_sensitive_data(item) for item in obj]
    if isinstance(obj, tuple):
        return tuple(mask_sensitive_data(item) for item in obj)
    if isinstance(obj, str):
        return _mask_string_by_format(obj)
    return obj


def mask_audit_event_for_display(payload: dict[str, Any]) -> dict[str, Any]:
    """Mask an audit event payload for support/admin display (T-073 prep)."""
    masked = mask_sensitive_data(payload)
    if isinstance(masked, dict):
        return masked
    return payload
