"""SQLAlchemy model for an incident: a sustained outage of one service."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.service import Service, utcnow


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

    service: Mapped[Service] = relationship(back_populates="incidents")
