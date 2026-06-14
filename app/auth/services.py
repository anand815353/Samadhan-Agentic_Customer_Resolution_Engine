"""Authentication service logic."""

import logging

from app.users.repositories import UserRepository
from app.users.schemas import UserRead
from app.users.security import verify_password

logger = logging.getLogger("samadhan.auth")

INVALID_LOGIN_MESSAGE = "Invalid email or password."


class AuthService:
    """Verify credentials against stored user records."""

    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    async def authenticate(self, email: str, password: str) -> UserRead | None:
        normalized_email = email.strip().lower()
        user = await self._user_repository.find_by_email(normalized_email)
        if user is None or not user.is_active:
            logger.info("Login failed", extra={"reason": "invalid_credentials"})
            return None
        if not verify_password(password, user.password_hash):
            logger.info("Login failed", extra={"reason": "invalid_credentials"})
            return None
        return UserRead.from_document(user)
