"""Database-backed global AI provider configuration."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.service import utcnow


class ProviderType(enum.StrEnum):
    """AI providers supported by the first multi-provider release."""

    ollama = "ollama"
    openai = "openai"
    anthropic = "anthropic"


class SummaryLanguage(enum.StrEnum):
    """Languages supported by the incident prompt and UI."""

    es = "es"
    en = "en"


class AISetting(Base):
    """Singleton configuration row for incident summary generation."""

    __tablename__ = "ai_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    provider: Mapped[ProviderType] = mapped_column(
        Enum(ProviderType, name="ai_provider_type"), default=ProviderType.ollama
    )
    model: Mapped[str] = mapped_column(String(200), default="llama3.1:8b")
    summary_language: Mapped[SummaryLanguage] = mapped_column(
        Enum(SummaryLanguage, name="summary_language"), default=SummaryLanguage.es
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    encrypted_api_key: Mapped[str | None] = mapped_column(Text)
    api_key_hint: Mapped[str | None] = mapped_column(String(4))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
