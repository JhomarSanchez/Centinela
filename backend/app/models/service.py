"""SQLAlchemy model for a monitored service."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    """Timezone-aware current time in UTC, used as a column default."""
    return datetime.now(UTC)


class Service(Base):
    """A URL that Centinela checks periodically."""

    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    url: Mapped[str] = mapped_column(String(2000))
    check_interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # delete-orphan: removing a service also removes its check history.
    checks: Mapped[list["Check"]] = relationship(  # noqa: F821
        back_populates="service", cascade="all, delete-orphan"
    )
    incidents: Mapped[list["Incident"]] = relationship(  # noqa: F821
        back_populates="service", cascade="all, delete-orphan"
    )
