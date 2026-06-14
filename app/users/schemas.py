"""User input and API-safe schemas."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.users.models import USER_ID_PATTERN, UserDocument, UserRole
from app.users.security import hash_password


class UserCreate(BaseModel):
    """Input for creating a user; plaintext password is hashed before persistence."""

    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(..., pattern=USER_ID_PATTERN)
    email: str
    password: str = Field(..., min_length=1)
    role: UserRole
    customer_id: str | None = None
    display_name: str
    is_demo_user: bool = False
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserRead(BaseModel):
    """API-safe user representation without password_hash."""

    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str
    email: str
    role: UserRole
    customer_id: str | None = None
    display_name: str
    is_demo_user: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_document(cls, document: UserDocument) -> "UserRead":
        return cls(
            user_id=document.user_id,
            email=document.email,
            role=document.role,
            customer_id=document.customer_id,
            display_name=document.display_name,
            is_demo_user=document.is_demo_user,
            is_active=document.is_active,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )


def user_document_from_create(
    data: UserCreate,
    *,
    now: datetime | None = None,
) -> UserDocument:
    """Build a UserDocument with a hashed password; never stores plaintext."""
    timestamp = now or datetime.now(UTC)
    return UserDocument(
        user_id=data.user_id,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
        customer_id=data.customer_id,
        display_name=data.display_name,
        is_demo_user=data.is_demo_user,
        is_active=data.is_active,
        created_at=timestamp,
        updated_at=timestamp,
    )
