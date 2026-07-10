"""SQLAlchemy model for an incident: a sustained outage of one service."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.ai_setting import ProviderType
from app.models.service import Service, utcnow


class AISummaryStatus(enum.StrEnum):
    """Lifecycle of the best-effort AI summary job."""

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class Incident(Base):
    """Opened after N consecutive failed checks; resolved when the service recovers.

    `ai_summary` is filled in by the local LLM (Ollama). It stays NULL when
    Ollama is disabled or unreachable — the incident itself must never depend
    on the AI being available.
    """

    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # NULL while the incident is ongoing.
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ai_summary: Mapped[str | None] = mapped_column(Text)
    # The exact context sent to the LLM, kept for transparency/debugging.
    raw_context: Mapped[str | None] = mapped_column(Text)
    ai_provider: Mapped[ProviderType | None] = mapped_column(
        Enum(ProviderType, name="ai_provider_type", create_type=False)
    )
    ai_model: Mapped[str | None] = mapped_column(String(200))
    ai_status: Mapped[AISummaryStatus] = mapped_column(
        Enum(AISummaryStatus, name="ai_summary_status"),
        default=AISummaryStatus.skipped,
    )
    ai_attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    ai_next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ai_processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ai_last_error_code: Mapped[str | None] = mapped_column(String(50))
    ai_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ai_input_tokens: Mapped[int | None] = mapped_column(Integer)
    ai_output_tokens: Mapped[int | None] = mapped_column(Integer)
    ai_latency_ms: Mapped[int | None] = mapped_column(Integer)
    prompt_version: Mapped[int | None] = mapped_column(Integer)

    service: Mapped[Service] = relationship(back_populates="incidents")
