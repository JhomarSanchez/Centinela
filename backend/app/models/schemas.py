"""Pydantic schemas: the shapes the API accepts and returns.

Keeping these separate from the SQLAlchemy models means the database layout
can change without breaking the public API contract, and vice versa.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.check import CheckStatus


class ServiceCreate(BaseModel):
    """Payload to register a new service."""

    name: str = Field(min_length=1, max_length=200)
    url: HttpUrl
    # Optional: when omitted, the server applies DEFAULT_CHECK_INTERVAL_SECONDS.
    check_interval_seconds: int | None = Field(default=None, ge=5, le=86400)


class ServiceUpdate(BaseModel):
    """Partial update: only the provided fields change."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    url: HttpUrl | None = None
    check_interval_seconds: int | None = Field(default=None, ge=5, le=86400)


class ServiceRead(BaseModel):
    """A service as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    check_interval_seconds: int
    created_at: datetime


class CheckRead(BaseModel):
    """A stored health-check result as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    service_id: int
    checked_at: datetime
    status: CheckStatus
    latency_ms: int | None
    http_code: int | None


class IncidentRead(BaseModel):
    """An incident as returned by the API.

    `ai_summary` is None while Ollama has not produced a summary yet;
    `resolved_at` is None while the incident is still open.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    service_id: int
    started_at: datetime
    resolved_at: datetime | None
    ai_summary: str | None
    raw_context: str | None
