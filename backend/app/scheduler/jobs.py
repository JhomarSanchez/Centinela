"""Periodic health-check job.

Design note: instead of registering one APScheduler job per service, a single
"tick" job runs every few seconds, asks the database which services are due
for a check, and checks them. This keeps the scheduler stateless — creating,
updating, or deleting a service needs no scheduler bookkeeping, because the
next tick simply reads the current state from the database.
"""

import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app import metrics
from app.config import get_settings
from app.database import SessionLocal
from app.models import Check, Service
from app.services import incident_manager
from app.services.health_checker import run_check

logger = logging.getLogger(__name__)


def _as_utc(dt: datetime) -> datetime:
    """Normalize datetimes read from the database.

    PostgreSQL returns timezone-aware values, but SQLite (used in tests)
    returns naive ones; we store everything in UTC, so naive means UTC.
    """
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


def find_due_services(db: Session, now: datetime | None = None) -> list[Service]:
    """Services that were never checked, or whose last check is older than their interval."""
    now = now or datetime.now(UTC)
    # One aggregate query for every service's newest check timestamp, instead
    # of one query per service (the classic "N+1 queries" trap).
    last_check_per_service = (
        select(Check.service_id, func.max(Check.checked_at).label("last_checked_at"))
        .group_by(Check.service_id)
        .subquery()
    )
    rows = db.execute(
        select(Service, last_check_per_service.c.last_checked_at).outerjoin(
            last_check_per_service, Service.id == last_check_per_service.c.service_id
        )
    )
    return [
        service
        for service, last_checked in rows
        if last_checked is None
        or now - _as_utc(last_checked) >= timedelta(seconds=service.check_interval_seconds)
    ]


def check_due_services() -> None:
    """One scheduler tick: run a health check for every due service and store the results."""
    settings = get_settings()
    with SessionLocal() as db:
        for service in find_due_services(db):
            # Each service gets its own try/except and commit so one bad
            # apple (an unexpected error, or a service deleted mid-tick)
            # cannot discard the results of every other service in the tick.
            try:
                status, latency_ms, http_code = run_check(
                    service.url,
                    timeout=settings.check_timeout_seconds,
                    degraded_latency_ms=settings.degraded_latency_ms,
                )
                db.add(
                    Check(
                        service_id=service.id,
                        status=status,
                        latency_ms=latency_ms,
                        http_code=http_code,
                    )
                )
                db.commit()
            except Exception:
                logger.exception("health check failed for service=%s", service.name)
                db.rollback()
                continue
            # Metrics update only after the check is safely stored, so the
            # dashboard never shows a result the database does not have.
            metrics.record_check(service.name, status, latency_ms)
            logger.info(
                "checked service=%s status=%s latency_ms=%s http_code=%s",
                service.name,
                status.value,
                latency_ms,
                http_code,
            )
            # Incident handling is isolated too: a failure here (e.g. a bug
            # in the AI path) must not stop the remaining health checks.
            try:
                incident_manager.process_check_result(db, service, status)
            except Exception:
                logger.exception("incident processing failed for service=%s", service.name)
                db.rollback()


def delete_old_checks(db: Session, now: datetime | None = None) -> int:
    """Delete checks older than the retention window; returns how many were removed.

    Incidents are never deleted: they are few, small, and the valuable
    long-term history of the system.
    """
    retention_days = get_settings().check_retention_days
    if retention_days <= 0:  # 0 means "keep everything forever"
        return 0
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=retention_days)
    result = db.execute(delete(Check).where(Check.checked_at < cutoff))
    db.commit()
    return result.rowcount


def cleanup_old_checks() -> None:
    """Daily retention job: keep the checks table from growing without bound."""
    with SessionLocal() as db:
        deleted = delete_old_checks(db)
    if deleted:
        logger.info("retention: deleted %s checks older than the retention window", deleted)


def create_scheduler() -> BackgroundScheduler:
    """Build the background scheduler with the tick and retention jobs."""
    settings = get_settings()
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        check_due_services,
        "interval",
        seconds=settings.scheduler_tick_seconds,
        id="health-check-tick",
        max_instances=1,  # never run two ticks at once
        coalesce=True,  # if ticks pile up while blocked, run only one
    )
    scheduler.add_job(
        cleanup_old_checks,
        "interval",
        hours=24,
        id="check-retention",
        # Also run shortly after startup, so restarting the backend is enough
        # to apply a new retention setting without waiting a full day.
        next_run_time=datetime.now(UTC) + timedelta(minutes=1),
    )
    return scheduler
