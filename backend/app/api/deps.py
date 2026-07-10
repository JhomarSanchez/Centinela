"""Shared database, API-key, signed-session, and CSRF dependencies."""

import secrets
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.security import read_session_token

# Annotated dependency alias: route signatures write `db: DbSession` instead
# of repeating `db: Session = Depends(get_db)` everywhere.
DbSession = Annotated[Session, Depends(get_db)]

# auto_error=False lets us return our own 401 instead of FastAPI's default 403.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@dataclass(frozen=True)
class AuthContext:
    """How an administrative request was authenticated."""

    method: str
    csrf_token: str | None = None


def _valid_api_key(api_key: str | None) -> bool:
    expected = get_settings().api_key
    return api_key is not None and secrets.compare_digest(api_key.encode(), expected.encode())


def require_auth(
    request: Request,
    api_key: str | None = Security(api_key_header),
) -> AuthContext:
    """Accept either the CLI API key or a signed browser session."""
    if _valid_api_key(api_key):
        return AuthContext(method="api_key")
    session_cookie = request.cookies.get(get_settings().session_cookie_name)
    if session_cookie:
        payload = read_session_token(session_cookie)
        if payload is not None:
            return AuthContext(method="session", csrf_token=payload.csrf_token)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


def require_write_auth(
    request: Request,
    auth: Annotated[AuthContext, Depends(require_auth)],
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> AuthContext:
    """Require CSRF proof for cookie-authenticated mutations.

    API-key requests are not vulnerable to browser ambient-authority CSRF, so
    CLI callers need no extra header.
    """
    if request.method in {"GET", "HEAD", "OPTIONS"} or auth.method == "api_key":
        return auth
    if (
        auth.csrf_token is None
        or csrf_header is None
        or not secrets.compare_digest(csrf_header.encode(), auth.csrf_token.encode())
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing CSRF token",
        )
    return auth


def require_api_key(api_key: str | None = Security(api_key_header)) -> None:
    """Backward-compatible API-key-only dependency used by older callers."""
    if not _valid_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
