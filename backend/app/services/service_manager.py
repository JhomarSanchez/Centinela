"""CRUD operations for services and their check history.

Routers stay thin: they translate HTTP to/from these functions, which hold
the actual business rules.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import metrics
from app.config import get_settings
from app.models import Check, Service
from app.models.schemas import ServiceCreate, ServiceUpdate


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
