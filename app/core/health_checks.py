"""Dependency health checks using stdlib probes only."""

from __future__ import annotations

import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Literal

from pydantic import BaseModel

from app.core.config import Settings
from app.core.constants import (
    CHECK_STATUS_NOT_CONFIGURED,
    CHECK_STATUS_OK,
    CHECK_STATUS_SKIPPED,
    CHECK_STATUS_UNREACHABLE,
    HEALTH_STATUS_DEGRADED,
    HEALTH_STATUS_OK,
    PROBE_TIMEOUT_SECONDS,
)

ServiceStatus = Literal["ok", "not_configured", "skipped", "unreachable"]
HealthStatus = Literal["ok", "degraded"]


class ServiceCheck(BaseModel):
    """Safe per-service health check result."""

    configured: bool
    reachable: bool | None
    status: ServiceStatus
    detail: str | None = None


class DependencyChecksResult(BaseModel):
    """Aggregate dependency check results."""

    mongodb: ServiceCheck
    qdrant: ServiceCheck
    redis: ServiceCheck


def _safe_error_detail(exc: BaseException) -> str:
    """Return a generic error message without leaking connection details."""
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, OSError):
        return "connection refused"
    if isinstance(exc, urllib.error.URLError):
        return "connection refused"
    return "unreachable"


def _tcp_probe(host: str, port: int, timeout: float = PROBE_TIMEOUT_SECONDS) -> None:
    with socket.create_connection((host, port), timeout=timeout):
        return


def _parse_host_port(
    url: str,
    *,
    default_port: int,
    schemes: tuple[str, ...],
) -> tuple[str, int]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in schemes:
        msg = f"unsupported scheme: {parsed.scheme or 'missing'}"
        raise ValueError(msg)
    host = parsed.hostname
    if not host:
        raise ValueError("missing host")
    port = parsed.port or default_port
    return host, port


def _check_mongodb(settings: Settings) -> ServiceCheck:
    if not settings.mongodb_uri.strip():
        return ServiceCheck(
            configured=False,
            reachable=None,
            status=CHECK_STATUS_NOT_CONFIGURED,
        )
    try:
        host, port = _parse_host_port(
            settings.mongodb_uri,
            default_port=27017,
            schemes=("mongodb", "mongodb+srv"),
        )
        _tcp_probe(host, port)
    except ValueError:
        return ServiceCheck(
            configured=True,
            reachable=False,
            status=CHECK_STATUS_UNREACHABLE,
            detail="invalid configuration",
        )
    except OSError as exc:
        return ServiceCheck(
            configured=True,
            reachable=False,
            status=CHECK_STATUS_UNREACHABLE,
            detail=_safe_error_detail(exc),
        )
    return ServiceCheck(
        configured=True,
        reachable=True,
        status=CHECK_STATUS_OK,
    )


def _check_qdrant(settings: Settings) -> ServiceCheck:
    if not settings.qdrant_url.strip():
        return ServiceCheck(
            configured=False,
            reachable=None,
            status=CHECK_STATUS_NOT_CONFIGURED,
        )
    ready_url = settings.qdrant_url.rstrip("/") + "/readyz"
    request = urllib.request.Request(ready_url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=PROBE_TIMEOUT_SECONDS) as response:
            if response.status >= 400:
                return ServiceCheck(
                    configured=True,
                    reachable=False,
                    status=CHECK_STATUS_UNREACHABLE,
                    detail="service unavailable",
                )
    except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        return ServiceCheck(
            configured=True,
            reachable=False,
            status=CHECK_STATUS_UNREACHABLE,
            detail=_safe_error_detail(exc),
        )
    return ServiceCheck(
        configured=True,
        reachable=True,
        status=CHECK_STATUS_OK,
    )


def _check_redis(settings: Settings) -> ServiceCheck:
    if not settings.redis_url.strip():
        return ServiceCheck(
            configured=False,
            reachable=None,
            status=CHECK_STATUS_SKIPPED,
            detail="optional service not configured",
        )
    try:
        host, port = _parse_host_port(
            settings.redis_url,
            default_port=6379,
            schemes=("redis", "rediss"),
        )
        _tcp_probe(host, port)
    except ValueError:
        return ServiceCheck(
            configured=True,
            reachable=False,
            status=CHECK_STATUS_UNREACHABLE,
            detail="invalid configuration",
        )
    except OSError as exc:
        return ServiceCheck(
            configured=True,
            reachable=False,
            status=CHECK_STATUS_UNREACHABLE,
            detail=_safe_error_detail(exc),
        )
    return ServiceCheck(
        configured=True,
        reachable=True,
        status=CHECK_STATUS_OK,
    )


def run_dependency_checks(settings: Settings) -> DependencyChecksResult:
    """Run lightweight dependency checks without database client libraries."""
    return DependencyChecksResult(
        mongodb=_check_mongodb(settings),
        qdrant=_check_qdrant(settings),
        redis=_check_redis(settings),
    )


def aggregate_status(checks: DependencyChecksResult) -> HealthStatus:
    """Return degraded when required dependencies are unreachable."""
    required = (checks.mongodb, checks.qdrant)
    if any(check.status == CHECK_STATUS_UNREACHABLE for check in required):
        return HEALTH_STATUS_DEGRADED
    return HEALTH_STATUS_OK


def checks_summary_for_logging(checks: DependencyChecksResult) -> dict[str, str]:
    """Return safe per-service status values for structured startup logs."""
    return {
        "mongodb": checks.mongodb.status,
        "qdrant": checks.qdrant.status,
        "redis": checks.redis.status,
    }
