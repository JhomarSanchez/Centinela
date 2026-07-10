"""CRUD operations and UI-oriented service read models.

Routers stay thin: they translate HTTP to/from these functions, which hold
the actual business rules.
"""

from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import metrics
from app.config import get_settings
from app.models import Check, CheckStatus, Incident, Service
from app.models.schemas import (
    ServiceCreate,
    ServiceSummary,
    ServiceTimelineRead,
    ServiceUpdate,
    TimelinePoint,
)


class ServiceNameTakenError(Exception):
    """Raised when a service name is already registered."""


def create_service(db: Session, payload: ServiceCreate) -> Service:
    """Register a new service, applying the default check interval if omitted."""
    if db.scalar(select(Service).where(Service.name == payload.name)):
        raise ServiceNameTakenError(payload.name)

    interval = payload.check_interval_seconds or get_settings().default_check_interval_seconds
    service = Service(name=payload.name, url=str(payload.url), check_interval_seconds=interval)
    db.add(service)
    try:
        db.commit()
    except IntegrityError:
        # Two concurrent creates can both pass the pre-check above; the
        # database unique constraint is the real guarantee, so translate its
        # failure into the same domain error instead of a 500.
        db.rollback()
        raise ServiceNameTakenError(payload.name) from None
    db.refresh(service)
    return service


def list_services(db: Session) -> list[Service]:
    """All registered services, oldest first."""
    return list(db.scalars(select(Service).order_by(Service.id)))


def list_service_summaries(db: Session, now: datetime | None = None) -> list[ServiceSummary]:
    """Return every service with its latest state and 24-hour availability."""
    now = now or datetime.now(UTC)
    ranked_checks = (
        select(
            Check.service_id,
            Check.status,
            Check.checked_at,
            Check.latency_ms,
            func.row_number()
            .over(
                partition_by=Check.service_id,
                order_by=(Check.checked_at.desc(), Check.id.desc()),
            )
            .label("row_number"),
        )
        .subquery()
    )
    latest = {
        row.service_id: row
        for row in db.execute(select(ranked_checks).where(ranked_checks.c.row_number == 1))
    }
    availability = {
        row.service_id: (row.up_count, row.total)
        for row in db.execute(
            select(
                Check.service_id,
                func.sum(case((Check.status == CheckStatus.up, 1), else_=0)).label("up_count"),
                func.count(Check.id).label("total"),
            )
            .where(Check.checked_at >= now - timedelta(hours=24))
            .group_by(Check.service_id)
        )
    }
    active_incidents = {
        service_id: incident_id
        for service_id, incident_id in db.execute(
            select(Incident.service_id, Incident.id).where(Incident.resolved_at.is_(None))
        )
    }
    summaries: list[ServiceSummary] = []
    for service in list_services(db):
        latest_row = latest.get(service.id)
        up_count, total = availability.get(service.id, (0, 0))
        summaries.append(
            ServiceSummary(
                id=service.id,
                name=service.name,
                url=service.url,
                check_interval_seconds=service.check_interval_seconds,
                created_at=service.created_at,
                latest_status=latest_row.status if latest_row else None,
                last_checked_at=latest_row.checked_at if latest_row else None,
                last_latency_ms=latest_row.latency_ms if latest_row else None,
                availability_24h=round((up_count / total) * 100, 2) if total else None,
                active_incident_id=active_incidents.get(service.id),
            )
        )
    return summaries


def get_service(db: Session, service_id: int) -> Service | None:
    return db.get(Service, service_id)


def update_service(db: Session, service: Service, payload: ServiceUpdate) -> Service:
    """Apply a partial update; only fields present in the payload change."""
    old_name = service.name
    if payload.name is not None and payload.name != service.name:
        if db.scalar(select(Service).where(Service.name == payload.name)):
            raise ServiceNameTakenError(payload.name)
        service.name = payload.name
    if payload.url is not None:
        service.url = str(payload.url)
    if payload.check_interval_seconds is not None:
        service.check_interval_seconds = payload.check_interval_seconds
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ServiceNameTakenError(payload.name) from None
    db.refresh(service)

    if service.name != old_name:
        # Metric series are keyed by name: drop the old series and re-seed
        # the new one from the latest stored check, so the dashboard neither
        # shows the stale name forever nor goes blank until the next check.
        metrics.forget_service(old_name)
        metrics.restore_service(db, service)
    return service


def delete_service(db: Session, service: Service) -> None:
    """Remove a service and (via cascade) its check history."""
    name = service.name
    db.delete(service)
    db.commit()
    metrics.forget_service(name)


def list_checks(db: Session, service_id: int, limit: int = 50) -> list[Check]:
    """Most recent checks for a service, newest first."""
    return list(
        db.scalars(
            select(Check)
            .where(Check.service_id == service_id)
            .order_by(Check.checked_at.desc(), Check.id.desc())
            .limit(limit)
        )
    )


def service_timeline(
    db: Session,
    service_id: int,
    from_: datetime,
    to: datetime,
    bucket: Literal["5m", "1h", "1d"],
) -> ServiceTimelineRead:
    """Aggregate checks into portable in-memory buckets for SQLite and PostgreSQL."""
    bucket_seconds = {"5m": 300, "1h": 3600, "1d": 86400}[bucket]
    checks = list(
        db.scalars(
            select(Check)
            .where(
                Check.service_id == service_id,
                Check.checked_at >= from_,
                Check.checked_at <= to,
            )
            .order_by(Check.checked_at)
        )
    )
    grouped: dict[int, list[Check]] = {}
    for check in checks:
        checked_at = (
            check.checked_at.replace(tzinfo=UTC)
            if check.checked_at.tzinfo is None
            else check.checked_at.astimezone(UTC)
        )
        bucket_key = int(checked_at.timestamp()) // bucket_seconds * bucket_seconds
        grouped.setdefault(bucket_key, []).append(check)
    points: list[TimelinePoint] = []
    for bucket_key, bucket_checks in sorted(grouped.items()):
        counts = {status: 0 for status in CheckStatus}
        latencies: list[int] = []
        for check in bucket_checks:
            counts[check.status] += 1
            if check.latency_ms is not None:
                latencies.append(check.latency_ms)
        total = len(bucket_checks)
        points.append(
            TimelinePoint(
                bucket_start=datetime.fromtimestamp(bucket_key, tz=UTC),
                total=total,
                up=counts[CheckStatus.up],
                degraded=counts[CheckStatus.degraded],
                down=counts[CheckStatus.down],
                availability_percent=round(counts[CheckStatus.up] / total * 100, 2),
                average_latency_ms=(
                    round(sum(latencies) / len(latencies), 2) if latencies else None
                ),
            )
        )
    return ServiceTimelineRead(
        service_id=service_id,
        from_=from_,
        to=to,
        bucket=bucket,
        points=points,
    )
