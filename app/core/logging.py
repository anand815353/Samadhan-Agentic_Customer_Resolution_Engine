"""Structured logging configuration."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings

SAFE_LOG_EXTRA_KEYS = frozenset(
    {
        "app",
        "environment",
        "version",
        "debug",
        "log_level",
        "log_json",
        "checks",
        "aggregate_status",
    }
)


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log line for Cloud Logging compatibility."""

    def __init__(self, app_name: str, environment: str, version: str) -> None:
        super().__init__()
        self.app_name = app_name
        self.environment = environment
        self.version = version

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "app": self.app_name,
            "environment": self.environment,
            "version": self.version,
        }
        for key in SAFE_LOG_EXTRA_KEYS:
            if key in {"app", "environment", "version"}:
                continue
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(settings: Settings) -> None:
    """Configure root and uvicorn loggers from application settings."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    if settings.log_json:
        handler.setFormatter(
            JsonFormatter(
                app_name=settings.app_name,
                environment=settings.app_env,
                version=settings.app_version,
            )
        )
    else:
        handler.setFormatter(
            logging.Formatter("%(levelname)s %(name)s %(message)s")
        )

    root_logger.addHandler(handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
        uvicorn_logger.setLevel(level)
