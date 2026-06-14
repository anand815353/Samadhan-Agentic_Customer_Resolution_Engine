"""Admin protected routes."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.auth.guards import require_admin
from app.auth.template_context import build_template_context
from app.core.templates import templates

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request) -> HTMLResponse:
    """Render the admin dashboard shell."""
    return templates.TemplateResponse(
        request,
        "dashboards/admin/dashboard.html",
        build_template_context(
            request,
            page_title="Admin dashboard",
            dashboard_title="Admin dashboard",
        ),
    )
