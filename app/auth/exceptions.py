"""Authentication exceptions for HTML redirect handling."""


class LoginRequired(Exception):
    """Raised when a protected route requires authentication."""


class RoleForbidden(Exception):
    """Raised when the authenticated user lacks the required role."""

    def __init__(self, redirect_url: str) -> None:
        self.redirect_url = redirect_url
        super().__init__(redirect_url)
