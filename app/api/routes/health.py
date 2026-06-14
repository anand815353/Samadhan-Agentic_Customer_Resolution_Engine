"""Health check endpoint with dependency status."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.health_checks import (
    DependencyChecksResult,
    ServiceCheck,
    aggregate_status,
    run_dependency_checks,
)

router = APIRouter(tags=["health"])

HealthStatus = Literal["ok", "degraded"]


class HealthResponse(BaseModel):
    """Application health response with safe dependency checks."""

    status: HealthStatus
    app: str
    environment: str
    version: str
    debug: bool
    checks: DependencyChecksResult


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return application health and dependency configuration status."""
    settings = get_settings()
    checks = run_dependency_checks(settings)
    return HealthResponse(
        status=aggregate_status(checks),
        app=settings.app_name,
        environment=settings.app_env,
        version=settings.app_version,
        debug=settings.app_debug,
        checks=checks,
    )
