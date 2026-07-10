"""Single-administrator browser session endpoints."""

import secrets

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.config import get_settings
from app.models.schemas import LoginRequest, SessionRead
from app.security import SecretConfigurationError, create_session_token, read_session_token

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/session", response_model=SessionRead)
def login(payload: LoginRequest, response: Response) -> SessionRead:
    """Exchange the administrative API key for a signed browser cookie."""
    settings = get_settings()
    if not secrets.compare_digest(payload.api_key.encode(), settings.api_key.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    try:
        token, csrf_token = create_session_token()
    except SecretConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=settings.session_hours * 3600,
        httponly=True,
        samesite="strict",
        secure=settings.app_env not in {"development", "test"},
        path="/",
    )
    return SessionRead(authenticated=True, csrf_token=csrf_token)


@router.get("/session", response_model=SessionRead)
def session_status(request: Request) -> SessionRead:
    """Return browser session state and the CSRF token after a page refresh."""
    token = request.cookies.get(get_settings().session_cookie_name)
    payload = read_session_token(token) if token else None
    if payload is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return SessionRead(authenticated=True, csrf_token=payload.csrf_token)


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    """Clear the browser session cookie."""
    response.delete_cookie(get_settings().session_cookie_name, path="/")
