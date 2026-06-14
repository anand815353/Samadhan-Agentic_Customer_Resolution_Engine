"""Customer protected routes."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.auth.guards import require_customer
from app.auth.template_context import build_template_context
from app.core.templates import templates

router = APIRouter(
    prefix="/customer",
    tags=["customer"],
    dependencies=[Depends(require_customer)],
)


@router.get("/dashboard", response_class=HTMLResponse)
def customer_dashboard(request: Request) -> HTMLResponse:
    """Render the customer dashboard shell."""
    return templates.TemplateResponse(
        request,
        "dashboards/customer/dashboard.html",
        build_template_context(
            request,
            page_title="Customer dashboard",
            dashboard_title="Customer dashboard",
        ),
    )
