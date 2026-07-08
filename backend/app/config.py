"""Application configuration loaded from environment variables.

pydantic-settings reads each field from an environment variable with the same
name (case-insensitive), falling back to a local `.env` file and then to the
defaults below. Docker Compose injects the real values in containers.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    api_key: str = "change-me"

    # SQLite default so the app can start without PostgreSQL during local
    # experiments; Docker Compose overrides this with the real PostgreSQL URL.
    database_url: str = "sqlite:///./centinela.db"

    # Health checks
    default_check_interval_seconds: int = 60
    check_timeout_seconds: float = 5.0
    # A successful response slower than this is reported as "degraded".
    degraded_latency_ms: int = 2000

    # Scheduler
    scheduler_enabled: bool = True
    # How often the scheduler wakes up to look for services due for a check.
    scheduler_tick_seconds: int = 10
    # Checks older than this are deleted daily; 0 keeps history forever.
    check_retention_days: int = 30

    # Incidents (Phase 3)
    # This many consecutive "down" checks open an incident.
    incident_failure_threshold: int = 3

    # Ollama, the local LLM that writes incident summaries (Phase 3).
    # When disabled or unreachable, incidents still open/resolve normally;
    # they just carry no AI summary until Ollama answers.
    ollama_enabled: bool = True
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"
    # LLM generation is slow (especially the first call, which loads the
    # model into memory), so this timeout is intentionally generous.
    ollama_timeout_seconds: float = 120.0


@lru_cache
def get_settings() -> Settings:
    """Return the settings singleton (cached after the first call)."""
    return Settings()
