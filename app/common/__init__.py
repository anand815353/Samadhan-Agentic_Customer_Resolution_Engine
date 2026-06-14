"""Shared abstractions for repositories and services."""

from app.common.repository import BaseRepository, Repository
from app.common.service import BaseService, Service

__all__ = [
    "BaseRepository",
    "BaseService",
    "Repository",
    "Service",
]
