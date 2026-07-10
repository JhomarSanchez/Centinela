"""Tests for the scheduler's "which services are due" logic and tick resilience."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.config import Settings
from app.models import Check, CheckStatus, Service
from app.scheduler.jobs import check_due_services, delete_old_checks, find_due_services

NOW = datetime(2026, 7, 7, 12, 0, 0, tzinfo=UTC)


def _add_service(db_session, name="svc", interval=60, url="https://example.com/health") -> Service:
    service = Service(name=name, url=url, check_interval_seconds=interval)
    db_session.add(service)
    db_session.commit()
    return service


def _add_check(db_session, service_id: int, checked_at: datetime) -> None:
    db_session.add(
        Check(
            service_id=service_id,
            checked_at=checked_at,
            status=CheckStatus.up,
            latency_ms=100,
            http_code=200,
        )
    )
    db_session.commit()


def test_never_checked_service_is_due(db_session):
    service = _add_service(db_session)
    assert [s.id for s in find_due_services(db_session, now=NOW)] == [service.id]


def test_recently_checked_service_is_not_due(db_session):
    service = _add_service(db_session, interval=60)
    _add_check(db_session, service.id, NOW - timedelta(seconds=10))
    assert find_due_services(db_session, now=NOW) == []


def test_service_past_its_interval_is_due(db_session):
    service = _add_service(db_session, interval=60)
    _add_check(db_session, service.id, NOW - timedelta(seconds=61))
    assert [s.id for s in find_due_services(db_session, now=NOW)] == [service.id]


def test_only_due_services_are_returned(db_session):
    due = _add_service(db_session, name="due", interval=60)
    fresh = _add_service(db_session, name="fresh", interval=60)
    _add_check(db_session, due.id, NOW - timedelta(seconds=120))
    _add_check(db_session, fresh.id, NOW - timedelta(seconds=5))

    due_ids = [s.id for s in find_due_services(db_session, now=NOW)]
    assert due_ids == [due.id]


def test_one_failing_check_does_not_lose_the_others(db_session, monkeypatch):
    """A crash while checking one service must not discard the rest of the tick."""
    _add_service(db_session, name="breaks", url="https://breaks.example.com/health")
    survivor = _add_service(db_session, name="works", url="https://works.example.com/health")

    def fake_execute_check(db, service, **kwargs):
        if "breaks" in service.url:
            raise RuntimeError("unexpected failure inside the check")
        check = Check(
            service_id=service.id,
            status=CheckStatus.up,
            latency_ms=100,
            http_code=200,
        )
        db.add(check)
        db.commit()
        return check

    # The tick opens its own session; point it at the test database instead.
    monkeypatch.setattr("app.scheduler.jobs.SessionLocal", lambda: db_session)
    monkeypatch.setattr("app.scheduler.jobs.execute_check", fake_execute_check)

    check_due_services()

    stored = list(db_session.scalars(select(Check)))
    assert [check.service_id for check in stored] == [survivor.id]
    assert stored[0].status == CheckStatus.up


class TestRetention:
    def test_old_checks_are_deleted_and_recent_ones_kept(self, db_session):
        service = _add_service(db_session)
        # Default retention is 30 days.
        _add_check(db_session, service.id, NOW - timedelta(days=40))
        _add_check(db_session, service.id, NOW - timedelta(days=1))

        deleted = delete_old_checks(db_session, now=NOW)

        assert deleted == 1
        remaining = list(db_session.scalars(select(Check)))
        assert len(remaining) == 1

    def test_retention_zero_keeps_everything(self, db_session, monkeypatch):
        monkeypatch.setattr(
            "app.scheduler.jobs.get_settings", lambda: Settings(check_retention_days=0)
        )
        service = _add_service(db_session)
        _add_check(db_session, service.id, NOW - timedelta(days=400))

        assert delete_old_checks(db_session, now=NOW) == 0
        assert len(list(db_session.scalars(select(Check)))) == 1
