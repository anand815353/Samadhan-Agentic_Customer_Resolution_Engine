"""Role-based route guard dependencies."""

from fastapi import Depends, Request

from app.auth.exceptions import LoginRequired, RoleForbidden
from app.auth.redirects import home_path_for_role
from app.auth.session import SessionUser, clear_session_user, get_session_user
from app.users.constants import ROLE_ADMIN, ROLE_CUSTOMER, ROLE_SUPPORT_AGENT


def resolve_session_user(request: Request) -> SessionUser | None:
    """Return the active session user, clearing inactive sessions."""
    user = get_session_user(request)
    if user is None:
        return None
    if not user.is_active:
        clear_session_user(request)
        return None
    return user


def require_login(request: Request) -> SessionUser:
    """Require an authenticated, active session user."""
    user = resolve_session_user(request)
    if user is None:
        raise LoginRequired()
    return user


get_current_user = require_login


def require_customer(user: SessionUser = Depends(require_login)) -> SessionUser:
    """Require the customer role."""
    if user.role != ROLE_CUSTOMER:
        raise RoleForbidden(home_path_for_role(user.role))
    return user


def require_support_agent(user: SessionUser = Depends(require_login)) -> SessionUser:
    """Require the support agent role."""
    if user.role != ROLE_SUPPORT_AGENT:
        raise RoleForbidden(home_path_for_role(user.role))
    return user


def require_admin(user: SessionUser = Depends(require_login)) -> SessionUser:
    """Require the admin role."""
    if user.role != ROLE_ADMIN:
        raise RoleForbidden(home_path_for_role(user.role))
    return user
