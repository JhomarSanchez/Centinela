"""Shared FastAPI dependencies (currently just the API-key guard).

Write endpoints require the X-API-Key header, per docs/ARCHITECTURE.md.
Read endpoints stay open because this is a single-user tool on a local network.
"""

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db

# Annotated dependency alias: route signatures write `db: DbSession` instead
# of repeating `db: Session = Depends(get_db)` everywhere.
DbSession = Annotated[Session, Depends(get_db)]

# auto_error=False lets us return our own 401 instead of FastAPI's default 403.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(api_key_header)) -> None:
    """Reject write requests that do not carry the configured API key.

    compare_digest takes the same time whether the first or last character
    differs, so an attacker cannot guess the key byte-by-byte by measuring
    response times (a "timing attack"). A plain == short-circuits.
    """
    expected = get_settings().api_key
    if api_key is None or not secrets.compare_digest(api_key.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
