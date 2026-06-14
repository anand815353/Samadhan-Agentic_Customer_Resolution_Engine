"""FastAPI application entrypoint."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes.admin import router as admin_router
from app.api.routes.agent import router as agent_router
from app.api.routes.auth import router as auth_router
from app.api.routes.customer import router as customer_router
from app.api.routes.health import router as health_router
from app.api.routes.public import router as public_router
from app.auth.exceptions import LoginRequired, RoleForbidden
from app.core.config import Settings, get_settings
from app.core.health_checks import (
    aggregate_status,
    checks_summary_for_logging,
    run_dependency_checks,
)
from app.core.logging import configure_logging
from app.core.templates import STATIC_DIR

logger = logging.getLogger("samadhan.startup")


def _session_secret(settings: Settings) -> str:
    key = settings.secret_key.get_secret_value()
    if key:
        return key
    if settings.app_env == "local":
        return "local-dev-only-change-me"
    raise RuntimeError("SECRET_KEY is required for session middleware outside local environment")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Configure logging and emit startup metadata."""
    settings = get_settings()
    configure_logging(settings)
    logger.info(
        "Application starting",
        extra={
            "app": settings.app_name,
            "environment": settings.app_env,
            "version": settings.app_version,
            "debug": settings.app_debug,
            "log_level": settings.log_level,
            "log_json": settings.log_json,
        },
    )
    checks = run_dependency_checks(settings)
    logger.info(
        "Startup dependency checks completed",
        extra={
            "checks": checks_summary_for_logging(checks),
            "aggregate_status": aggregate_status(checks),
        },
    )
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    active_settings = settings or get_settings()
    application = FastAPI(
        title=active_settings.app_name,
        version=active_settings.app_version,
        debug=active_settings.app_debug,
        lifespan=lifespan,
    )

    @application.exception_handler(LoginRequired)
    async def login_required_handler(_request: Request, _exc: LoginRequired) -> RedirectResponse:
        return RedirectResponse(url="/login", status_code=302)

    @application.exception_handler(RoleForbidden)
    async def role_forbidden_handler(
        _request: Request,
        exc: RoleForbidden,
    ) -> RedirectResponse:
        return RedirectResponse(url=exc.redirect_url, status_code=302)

    application.add_middleware(
        SessionMiddleware,
        secret_key=_session_secret(active_settings),
        session_cookie=active_settings.session_cookie_name,
        max_age=86400,
        same_site="lax",
        https_only=not active_settings.app_debug,
    )
    application.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    application.include_router(public_router)
    application.include_router(health_router)
    application.include_router(customer_router)
    application.include_router(agent_router)
    application.include_router(admin_router)
    application.include_router(auth_router)
    return application


app = create_app()
