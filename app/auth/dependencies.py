"""FastAPI dependencies for authentication."""

from fastapi import Depends, Request

from app.auth.guards import (
    get_current_user,
    require_admin,
    require_customer,
    require_login,
    require_support_agent,
)
from app.auth.services import AuthService
from app.auth.session import SessionUser, get_session_user
from app.core.config import Settings, get_settings
from app.users.repositories import (
    MongoUserRepository,
    UnavailableUserRepository,
    UserRepository,
)


def get_user_repository(
    settings: Settings = Depends(get_settings),
) -> UserRepository:
    """Return Mongo user lookup when configured; otherwise fail closed."""
    if settings.mongodb_uri.strip() and settings.mongodb_db_name.strip():
        return MongoUserRepository(settings)
    return UnavailableUserRepository()


def get_auth_service(
    user_repository: UserRepository = Depends(get_user_repository),
) -> AuthService:
    """Build an auth service for route handlers and tests."""
    return AuthService(user_repository)


def get_optional_session_user(request: Request) -> SessionUser | None:
    """Return the current session user for public templates without enforcing login."""
    return get_session_user(request)
