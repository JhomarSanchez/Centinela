"""Database engine and session setup (SQLAlchemy 2.0 style)."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class that all ORM models inherit from."""


def _build_engine():
    settings = get_settings()
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        # SQLite forbids cross-thread use by default; FastAPI handles requests
        # in a thread pool, so that restriction must be lifted.
        connect_args["check_same_thread"] = False
    # pool_pre_ping revalidates pooled connections so the API survives
    # PostgreSQL restarts without returning stale-connection errors.
    return create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields one database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
