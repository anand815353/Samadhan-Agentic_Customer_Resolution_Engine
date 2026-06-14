"""User domain module: models, schemas, and password hashing (T-007)."""

from app.users.constants import (
    ROLE_ADMIN,
    ROLE_CUSTOMER,
    ROLE_SUPPORT_AGENT,
    USERS_COLLECTION,
)
from app.users.models import UserDocument, UserRole
from app.users.schemas import UserCreate, UserRead, user_document_from_create
from app.users.security import hash_password, verify_password

__all__ = [
    "ROLE_ADMIN",
    "ROLE_CUSTOMER",
    "ROLE_SUPPORT_AGENT",
    "USERS_COLLECTION",
    "UserCreate",
    "UserDocument",
    "UserRead",
    "UserRole",
    "hash_password",
    "user_document_from_create",
    "verify_password",
]
