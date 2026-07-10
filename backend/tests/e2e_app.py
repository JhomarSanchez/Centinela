"""Disposable SQLite application used only by the browser acceptance test."""

from app.database import Base, engine
from app.main import app

Base.metadata.create_all(engine)

__all__ = ["app"]
