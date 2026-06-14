"""Role-based post-login redirect paths."""

from app.users.constants import ROLE_ADMIN, ROLE_CUSTOMER, ROLE_SUPPORT_AGENT
from app.users.models import UserRole

ROLE_HOME_PATHS: dict[UserRole, str] = {
    ROLE_CUSTOMER: "/customer/dashboard",
    ROLE_SUPPORT_AGENT: "/agent/dashboard",
    ROLE_ADMIN: "/admin/dashboard",
}


def home_path_for_role(role: UserRole) -> str:
    """Return the post-login redirect path for a role."""
    return ROLE_HOME_PATHS[role]
