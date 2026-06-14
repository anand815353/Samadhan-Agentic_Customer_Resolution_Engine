"""Signed session helpers for authenticated users."""

from fastapi import Request
from pydantic import BaseModel

from app.users.models import UserRole
from app.users.schemas import UserRead

SESSION_USER_KEY = "user"


class SessionUser(BaseModel):
    """Minimal user payload stored in the signed session cookie."""

    user_id: str
    role: UserRole
    display_name: str
    customer_id: str | None = None
    is_active: bool = True


def set_session_user(request: Request, user: UserRead) -> None:
    """Persist safe user fields in the session; never store password or hash."""
    request.session[SESSION_USER_KEY] = SessionUser(
        user_id=user.user_id,
        role=user.role,
        display_name=user.display_name,
        customer_id=user.customer_id,
        is_active=user.is_active,
    ).model_dump(mode="json")


def get_session_user(request: Request) -> SessionUser | None:
    """Return the current session user, if any."""
    payload = request.session.get(SESSION_USER_KEY)
    if payload is None:
        return None
    return SessionUser.model_validate(payload)


def clear_session_user(request: Request) -> None:
    """Remove authenticated user state from the session."""
    request.session.pop(SESSION_USER_KEY, None)
