"""Admin protected routes."""

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.admin.dependencies import get_admin_policy_indexing_service
from app.admin.schemas import AdminReindexResult
from app.admin.services import AdminPolicyIndexingService
from app.auth.guards import require_admin
from app.auth.session import get_session_user
from app.auth.template_context import build_template_context
from app.core.templates import templates

_POLICY_ID_PATH_PATTERN = r"POL-[A-Z0-9-]+"

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


@router.get("/policies", response_class=HTMLResponse)
async def admin_policies_list(
    request: Request,
    service: AdminPolicyIndexingService = Depends(get_admin_policy_indexing_service),
) -> HTMLResponse:
    """List policy documents and indexing status for admin re-index operations."""
    flash_payload = request.session.pop("admin_flash", None)
    flash: AdminReindexResult | None = None
    if flash_payload is not None:
        flash = AdminReindexResult.model_validate(flash_payload)

    documents = await service.list_documents()
    return templates.TemplateResponse(
        request,
        "admin/policies.html",
        build_template_context(
            request,
            page_title="Policy indexing",
            dashboard_title="Policy indexing",
            documents=documents,
            flash=flash,
        ),
    )


@router.post("/policies/{document_id}/reindex")
async def admin_policy_reindex(
    request: Request,
    document_id: str = Path(..., pattern=_POLICY_ID_PATH_PATTERN),
    service: AdminPolicyIndexingService = Depends(get_admin_policy_indexing_service),
) -> RedirectResponse:
    """Re-index a single approved policy document (POST only)."""
    session_user = get_session_user(request)
    admin_user_id = session_user.user_id if session_user is not None else "USR-ADMIN-001"
    result = await service.reindex_document(document_id, admin_user_id=admin_user_id)
    request.session["admin_flash"] = result.model_dump(mode="json")
    return RedirectResponse(url="/admin/policies", status_code=303)
