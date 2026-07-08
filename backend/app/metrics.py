"""Prometheus metrics for monitored services.

This module is the bridge between health checks and the Grafana dashboard:
every stored Check also updates these in-memory series, and Prometheus
scrapes them from GET /metrics.

Metric design notes:
- Gauges hold the *latest* check result per service. Checks are sparse
  (one per interval), so "last known value" is the honest representation.
- The counter accumulates checks by result, which lets dashboards compute
  availability as up-checks / total-checks over any time range.
- Latency is exported in seconds (not ms) because Prometheus convention is
  base SI units; dashboards format it back to ms.
"""

import logging

from prometheus_client import Counter, Gauge
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Check, CheckStatus, Incident, Service

logger = logging.getLogger(__name__)

# Numeric encoding for the status gauge; Grafana maps the numbers back to
# UP/DEGRADED/DOWN labels. Higher = healthier, so thresholds read naturally.
STATUS_VALUES: dict[CheckStatus, int] = {
    CheckStatus.down: 0,
    CheckStatus.degraded: 1,
    CheckStatus.up: 2,
}

service_status = Gauge(
    "centinela_service_status",
    "Latest check result per service (0=down, 1=degraded, 2=up).",
    ["service_name"],
)
service_up = Gauge(
    "centinela_service_up",
    "1 when the latest check was 'up', 0 otherwise (degraded counts as not up).",
    ["service_name"],
)
check_latency_seconds = Gauge(
    "centinela_check_latency_seconds",
    "Latency of the latest health check per service, in seconds.",
    ["service_name"],
)
checks_total = Counter(
    "centinela_checks_total",
    "Health checks performed since the backend started, by service and result.",
    ["service_name", "status"],
)
incident_open = Gauge(
    "centinela_incident_open",
    "1 while the service has an unresolved incident, 0 otherwise.",
    ["service_name"],
)
incidents_total = Counter(
    "centinela_incidents_total",
    "Incidents opened since the backend started, by service.",
    ["service_name"],
)


def set_gauges(service_name: str, status: CheckStatus, latency_ms: int | None) -> None:
    """Set the last-known-state gauges for one service (no counter increment)."""
    service_status.labels(service_name).set(STATUS_VALUES[status])
    service_up.labels(service_name).set(1 if status == CheckStatus.up else 0)
    if latency_ms is not None:
        check_latency_seconds.labels(service_name).set(latency_ms / 1000)


def record_check(service_name: str, status: CheckStatus, latency_ms: int | None) -> None:
    """Update all metric series after one live health check."""
    set_gauges(service_name, status, latency_ms)
    checks_total.labels(service_name, status.value).inc()


def record_incident_opened(service_name: str) -> None:
    """Mark a service as having an open incident."""
    incident_open.labels(service_name).set(1)
    incidents_total.labels(service_name).inc()


def record_incident_resolved(service_name: str) -> None:
    """Clear the open-incident flag for a service."""
    incident_open.labels(service_name).set(0)


def forget_service(service_name: str) -> None:
    """Drop every metric series for a service.

    Called when a service is deleted or renamed; otherwise the old name
    would keep showing its last value on the dashboard forever.
    """
    for gauge in (service_status, service_up, check_latency_seconds, incident_open):
        try:
            gauge.remove(service_name)
        except KeyError:
            pass  # never checked, so the series never existed
    for status in CheckStatus:
        try:
            checks_total.remove(service_name, status.value)
        except KeyError:
            pass
    try:
        incidents_total.remove(service_name)
    except KeyError:
        pass


def restore_service(db: Session, service: Service) -> None:
    """Seed the gauges from the newest stored check, if any.

    The counter is intentionally not touched: those checks happened before
    this process started, and counters must only count what this process saw.
    """
    latest = db.scalars(
        select(Check)
        .where(Check.service_id == service.id)
        .order_by(Check.checked_at.desc(), Check.id.desc())
        .limit(1)
    ).first()
    if latest is not None:
        set_gauges(service.name, latest.status, latest.latency_ms)
    has_open_incident = (
        db.scalars(
            select(Incident.id)
            .where(Incident.service_id == service.id, Incident.resolved_at.is_(None))
            .limit(1)
        ).first()
        is not None
    )
    incident_open.labels(service.name).set(1 if has_open_incident else 0)


def init_from_db(db: Session) -> None:
    """Restore gauges for every service on startup.

    Without this, a backend restart leaves /metrics empty until each service
    is checked again, and the dashboard shows "No data" for that gap.
    """
    for service in db.scalars(select(Service)):
        restore_service(db, service)
