"""Base service protocol and abstract class for domain business logic."""

from abc import ABC
from typing import Protocol


class Service(Protocol):
    """Marker protocol for domain service classes."""


class BaseService(ABC):
    """Lightweight base for domain services; subclasses add repositories in future tasks."""
