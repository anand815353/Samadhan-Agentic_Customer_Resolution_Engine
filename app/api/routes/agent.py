"""Support-agent protected routes."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.auth.guards import require_support_agent
from app.auth.template_context import build_template_context
from app.core.templates import templates

router = APIRouter(
    prefix="/agent",
    tags=["agent"],
    dependencies=[Depends(require_support_agent)],
)


@router.get("/dashboard", response_class=HTMLResponse)
def agent_dashboard(request: Request) -> HTMLResponse:
    """Render the support-agent dashboard shell."""
    return templates.TemplateResponse(
        request,
        "dashboards/agent/dashboard.html",
        build_template_context(
            request,
            page_title="Support agent dashboard",
            dashboard_title="Support agent dashboard",
        ),
    )
