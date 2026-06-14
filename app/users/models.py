"""User persistence models aligned with the MongoDB users collection."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.users.constants import ROLE_ADMIN, ROLE_CUSTOMER, ROLE_SUPPORT_AGENT

UserRole = Literal["customer", "support_agent", "admin"]

USER_ID_PATTERN = r"^USR-[A-Z]+-\d{3,4}$"


class UserDocument(BaseModel):
    """MongoDB users collection document."""

    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(..., pattern=USER_ID_PATTERN)
    email: str
    password_hash: str
    role: UserRole
    customer_id: str | None = None
    display_name: str
    is_demo_user: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def validate_role_customer_link(self) -> "UserDocument":
        if self.role == ROLE_CUSTOMER and not self.customer_id:
            raise ValueError("customer role requires customer_id")
        if self.role in (ROLE_SUPPORT_AGENT, ROLE_ADMIN) and self.customer_id is not None:
            raise ValueError(f"{self.role} role must not have customer_id")
        return self

    def to_mongo_dict(self) -> dict[str, object]:
        """Serialize for MongoDB insert/update (T-016+ repository)."""
        return self.model_dump(mode="json")
