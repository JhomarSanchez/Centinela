"""Shared pytest fixtures.

Tests run against an in-memory SQLite database instead of PostgreSQL so they
are fast and need no running containers. The FastAPI dependency that hands out
database sessions is overridden to use this test database.

The environment variables below must be set BEFORE importing the app, because
settings are cached on first read.
"""

import os

os.environ["SCHEDULER_ENABLED"] = "false"  # tests must never hit the real network
os.environ["OLLAMA_ENABLED"] = "false"  # same rule for the LLM
os.environ["API_KEY"] = "test-key"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

API_KEY_HEADER = {"X-API-Key": "test-key"}


@pytest.fixture()
def db_session():
    """A fresh in-memory database per test, with all tables created."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        # StaticPool shares the single in-memory database across threads.
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    """A test client whose requests use the test database session."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
