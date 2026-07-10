"""Application configuration loaded from environment variables.

pydantic-settings reads each field from an environment variable with the same
name (case-insensitive), falling back to a local `.env` file and then to the
defaults below. Docker Compose injects the real values in containers.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    api_key: str = "change-me"
    # Master secret used to derive independent session-signing and credential-
    # encryption keys. Cloud credentials cannot be saved while this is left at
    # the public development default.
    app_secret_key: str = "change-me"
    session_cookie_name: str = "centinela_session"
    session_hours: int = Field(default=12, ge=1, le=168)

    # SQLite default so the app can start without PostgreSQL during local
    # experiments; Docker Compose overrides this with the real PostgreSQL URL.
    database_url: str = "sqlite:///./centinela.db"

    # Health checks
    default_check_interval_seconds: int = Field(default=60, ge=5, le=86400)
    check_timeout_seconds: float = Field(default=5.0, gt=0, le=120)
    # A successful response slower than this is reported as "degraded".
    degraded_latency_ms: int = Field(default=2000, ge=1)

    # Scheduler
    scheduler_enabled: bool = True
    # How often the scheduler wakes up to look for services due for a check.
    scheduler_tick_seconds: int = Field(default=10, ge=1)
    # Checks older than this are deleted daily; 0 keeps history forever.
    check_retention_days: int = Field(default=30, ge=0)

    # Incidents (Phase 3)
    # This many consecutive "down" checks open an incident.
    incident_failure_threshold: int = Field(default=3, ge=1, le=100)

    # A separate APScheduler job handles LLM work so a slow provider never
    # delays health checks.
    ai_worker_seconds: int = Field(default=5, ge=1, le=300)

    # Ollama, the local LLM that writes incident summaries (Phase 3).
    # When disabled or unreachable, incidents still open/resolve normally;
    # they just carry no AI summary until Ollama answers.
    ollama_enabled: bool = True
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"
    # LLM generation is slow (especially the first call, which loads the
    # model into memory), so this timeout is intentionally generous.
    ollama_timeout_seconds: float = Field(default=120.0, gt=0, le=600)
    openai_timeout_seconds: float = Field(default=60.0, gt=0, le=300)
    anthropic_timeout_seconds: float = Field(default=60.0, gt=0, le=300)


@lru_cache
def get_settings() -> Settings:
    """Return the settings singleton (cached after the first call)."""
    return Settings()
