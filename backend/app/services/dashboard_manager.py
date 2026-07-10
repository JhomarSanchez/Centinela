"""Read model for the product overview dashboard."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Check, CheckStatus, Incident
from app.models.schemas import DashboardSummaryRead
from app.services.service_manager import list_service_summaries


def dashboard_summary(db: Session, now: datetime | None = None) -> DashboardSummaryRead:
    now = now or datetime.now(UTC)
    services = list_service_summaries(db, now=now)
    total_checks, up_checks = db.execute(
        select(
            func.count(Check.id),
            func.sum(case((Check.status == CheckStatus.up, 1), else_=0)),
        ).where(Check.checked_at >= now - timedelta(hours=24))
    ).one()
    active_incidents = db.scalar(
        select(func.count(Incident.id)).where(Incident.resolved_at.is_(None))
    ) or 0
    return DashboardSummaryRead(
        total_services=len(services),
        up_services=sum(service.latest_status == CheckStatus.up for service in services),
        degraded_services=sum(
            service.latest_status == CheckStatus.degraded for service in services
        ),
        down_services=sum(service.latest_status == CheckStatus.down for service in services),
        unmonitored_services=sum(service.latest_status is None for service in services),
        active_incidents=active_incidents,
        availability_24h=(
            round((up_checks or 0) / total_checks * 100, 2) if total_checks else None
        ),
    )
