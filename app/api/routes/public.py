"""Public HTML routes."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.auth.session import get_session_user
from app.core.config import get_settings
from app.core.demo_catalog import (
    CUSTOMER_TEST_QUESTIONS,
    DEFAULT_DEMO_PASSWORD,
    DEMO_ACCOUNTS,
    DEMO_PAGE_DISCLAIMER,
    ROLE_INSTRUCTIONS,
    WALKTHROUGH_STEPS,
)
from app.core.templates import templates

router = APIRouter(tags=["public"])


@router.get("/", response_class=HTMLResponse)
def landing(request: Request) -> HTMLResponse:
    """Render the minimal public landing page."""
    settings = get_settings()
    return templates.TemplateResponse(
        request,
        "public/landing.html",
        {
            "page_title": settings.app_name,
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "session_user": get_session_user(request),
        },
    )


@router.get("/demo-access", response_class=HTMLResponse)
def demo_access(request: Request) -> HTMLResponse:
    """Render the public demo credentials and scenario guide page."""
    settings = get_settings()
    customer_accounts = [a for a in DEMO_ACCOUNTS if a["category"] == "customer"]
    support_agent_accounts = [a for a in DEMO_ACCOUNTS if a["category"] == "support_agent"]
    admin_accounts = [a for a in DEMO_ACCOUNTS if a["category"] == "admin"]
    return templates.TemplateResponse(
        request,
        "public/demo_access.html",
        {
            "page_title": "Demo access",
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "session_user": get_session_user(request),
            "default_password": DEFAULT_DEMO_PASSWORD,
            "demo_accounts": DEMO_ACCOUNTS,
            "customer_accounts": customer_accounts,
            "support_agent_accounts": support_agent_accounts,
            "admin_accounts": admin_accounts,
            "customer_test_questions": CUSTOMER_TEST_QUESTIONS,
            "walkthrough_steps": WALKTHROUGH_STEPS,
            "role_instructions": ROLE_INSTRUCTIONS,
            "demo_disclaimer": DEMO_PAGE_DISCLAIMER,
        },
    )
