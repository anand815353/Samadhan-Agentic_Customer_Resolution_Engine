"""Authentication module: login, logout, sessions, and role guards (T-008/T-009)."""

from app.auth.dependencies import (
    get_auth_service,
    get_current_user,
    get_optional_session_user,
    get_user_repository,
    require_admin,
    require_customer,
    require_login,
    require_support_agent,
)
from app.auth.exceptions import LoginRequired, RoleForbidden
from app.auth.guards import resolve_session_user
from app.auth.redirects import home_path_for_role
from app.auth.services import INVALID_LOGIN_MESSAGE, AuthService
from app.auth.session import SessionUser, clear_session_user, get_session_user, set_session_user

__all__ = [
    "AuthService",
    "INVALID_LOGIN_MESSAGE",
    "LoginRequired",
    "RoleForbidden",
    "SessionUser",
    "clear_session_user",
    "get_auth_service",
    "get_current_user",
    "get_optional_session_user",
    "get_session_user",
    "get_user_repository",
    "home_path_for_role",
    "require_admin",
    "require_customer",
    "require_login",
    "require_support_agent",
    "resolve_session_user",
    "set_session_user",
]
