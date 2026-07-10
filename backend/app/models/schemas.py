"""Pydantic schemas: the shapes the API accepts and returns.

Keeping these separate from the SQLAlchemy models means the database layout
can change without breaking the public API contract, and vice versa.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.ai_setting import ProviderType, SummaryLanguage
from app.models.check import CheckStatus
from app.models.incident import AISummaryStatus


class LoginRequest(BaseModel):
    api_key: str = Field(min_length=1, max_length=500)


class SessionRead(BaseModel):
    authenticated: bool
    csrf_token: str


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


class ServiceSummary(ServiceRead):
    """Service plus the latest state needed by the product UI."""

    latest_status: CheckStatus | None
    last_checked_at: datetime | None
    last_latency_ms: int | None
    availability_24h: float | None
    active_incident_id: int | None


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

    `raw_context` intentionally lives behind a separate administrative endpoint.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    service_id: int
    started_at: datetime
    resolved_at: datetime | None
    ai_summary: str | None
    ai_provider: ProviderType | None
    ai_model: str | None
    ai_status: AISummaryStatus
    ai_attempt_count: int
    ai_last_error_code: str | None
    ai_generated_at: datetime | None
    ai_input_tokens: int | None
    ai_output_tokens: int | None
    ai_latency_ms: int | None
    prompt_version: int | None


class IncidentDetailRead(IncidentRead):
    service_name: str


class IncidentContextRead(BaseModel):
    incident_id: int
    raw_context: str | None


class AISettingsUpdate(BaseModel):
    provider: ProviderType
    model: str = Field(min_length=1, max_length=200)
    summary_language: SummaryLanguage = SummaryLanguage.es
    enabled: bool = True
    api_key: str | None = Field(default=None, min_length=8, max_length=1000)


class AISettingsRead(BaseModel):
    provider: ProviderType
    model: str
    summary_language: SummaryLanguage
    enabled: bool
    credential_required: bool
    credential_configured: bool
    api_key_hint: str | None
    updated_at: datetime


class AIProviderTestRead(BaseModel):
    ok: bool
    provider: ProviderType
    model: str
    latency_ms: int


class TimelinePoint(BaseModel):
    bucket_start: datetime
    total: int
    up: int
    degraded: int
    down: int
    availability_percent: float
    average_latency_ms: float | None


class ServiceTimelineRead(BaseModel):
    service_id: int
    from_: datetime = Field(serialization_alias="from")
    to: datetime
    bucket: Literal["5m", "1h", "1d"]
    points: list[TimelinePoint]


class DashboardSummaryRead(BaseModel):
    total_services: int
    up_services: int
    degraded_services: int
    down_services: int
    unmonitored_services: int
    active_incidents: int
    availability_24h: float | None
