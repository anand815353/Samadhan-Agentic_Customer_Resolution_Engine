"""Authentication routes: login and logout."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth.dependencies import get_auth_service
from app.auth.guards import resolve_session_user
from app.auth.redirects import home_path_for_role
from app.auth.services import INVALID_LOGIN_MESSAGE, AuthService
from app.auth.session import clear_session_user, set_session_user
from app.auth.template_context import build_template_context
from app.core.templates import templates

router = APIRouter(tags=["auth"])


@router.get("/login", response_model=None)
def login_page(request: Request) -> HTMLResponse | RedirectResponse:
    """Render the login form."""
    session_user = resolve_session_user(request)
    if session_user is not None:
        return RedirectResponse(url=home_path_for_role(session_user.role), status_code=302)
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        build_template_context(request, page_title="Login", error_message=None),
    )


@router.post("/login", response_model=None)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    auth_service: AuthService = Depends(get_auth_service),
) -> HTMLResponse | RedirectResponse:
    """Authenticate and start a signed session."""
    user = await auth_service.authenticate(email, password)
    if user is None:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            build_template_context(request, page_title="Login", error_message=INVALID_LOGIN_MESSAGE),
            status_code=200,
        )

    set_session_user(request, user)
    return RedirectResponse(url=home_path_for_role(user.role), status_code=302)


@router.post("/logout")
def logout(request: Request) -> RedirectResponse:
    """Clear the session and return to the login page."""
    clear_session_user(request)
    return RedirectResponse(url="/login", status_code=302)
