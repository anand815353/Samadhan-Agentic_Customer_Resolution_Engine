"""Shared Jinja template context for authenticated routes."""

from fastapi import Request

from app.auth.session import get_session_user
from app.core.config import get_settings


def build_template_context(request: Request, **extra: object) -> dict[str, object]:
    """Build common template context including optional session user."""
    settings = get_settings()
    return {
        "request": request,
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "session_user": get_session_user(request),
        **extra,
    }
