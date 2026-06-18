"""Message domain constants aligned with DATA_MODEL §9.2."""

from typing import Literal

MESSAGES_COLLECTION = "messages"

SenderType = Literal["customer", "ai", "support_agent", "system"]
MessageActor = Literal["customer", "support_agent", "system", "ai", "admin"]

ALL_SENDER_TYPES: tuple[SenderType, ...] = (
    "customer",
    "ai",
    "support_agent",
    "system",
)

# Conventional message_metadata keys (not enforced as schema in T-022).
META_SOURCE = "source"
META_INTENT = "intent"
META_NORMALIZED_TEXT = "normalized_text"
