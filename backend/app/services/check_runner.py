"""Shared execution path for scheduled and manual health checks."""

import logging

import httpx
from sqlalchemy.orm import Session

from app import metrics
from app.config import get_settings
from app.models import Check, Service
from app.services import incident_manager
from app.services.health_checker import run_check

logger = logging.getLogger(__name__)


def execute_check(
    db: Session,
    service: Service,
    *,
    client: httpx.Client | None = None,
) -> Check:
    """Run, store, instrument, and process one service check."""
    settings = get_settings()
    status, latency_ms, http_code = run_check(
        service.url,
        timeout=settings.check_timeout_seconds,
        degraded_latency_ms=settings.degraded_latency_ms,
        client=client,
    )
    check = Check(
        service_id=service.id,
        status=status,
        latency_ms=latency_ms,
        http_code=http_code,
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    metrics.record_check(service.name, status, latency_ms)
    try:
        incident_manager.process_check_result(db, service, status)
    except Exception:
        logger.exception("incident processing failed for service=%s", service.name)
        db.rollback()
    return check
