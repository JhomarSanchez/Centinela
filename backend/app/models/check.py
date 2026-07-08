"""SQLAlchemy model for one health-check result."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.service import Service, utcnow


class CheckStatus(enum.StrEnum):
    """Result of a health check. StrEnum members behave as plain strings in JSON."""

    up = "up"
    degraded = "degraded"
    down = "down"


class Check(Base):
    """Historical record of a single health check against a service."""

    __tablename__ = "checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), index=True
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    status: Mapped[CheckStatus] = mapped_column(Enum(CheckStatus, name="check_status"))
    # Both nullable: when a check gets no response at all there is neither
    # an HTTP code nor a meaningful latency measurement.
    latency_ms: Mapped[int | None]
    http_code: Mapped[int | None]

    service: Mapped[Service] = relationship(back_populates="checks")
