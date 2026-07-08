"""Incident detection, resolution, and AI summary generation.

Rules (see docs/ARCHITECTURE.md):
- N consecutive `down` checks open an incident (N = INCIDENT_FAILURE_THRESHOLD).
- An `up` check resolves the open incident.
- `degraded` does neither: it breaks a down-streak but is not a recovery.

The AI summary is best-effort: if Ollama cannot answer when the incident
opens, the incident is stored without a summary and the next `down` check
retries. Incident bookkeeping never depends on the LLM being available.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import metrics
from app.ai import ollama_client
from app.ai.prompt import build_incident_prompt
from app.config import get_settings
from app.models import Check, CheckStatus, Incident, Service

logger = logging.getLogger(__name__)

# How many recent checks the LLM sees as context.
PROMPT_CHECK_COUNT = 10


def get_open_incident(db: Session, service_id: int) -> Incident | None:
    """The service's unresolved incident, if any (there is at most one)."""
    return db.scalars(
        select(Incident)
        .where(Incident.service_id == service_id, Incident.resolved_at.is_(None))
        .order_by(Incident.started_at.desc())
        .limit(1)
    ).first()


def _recent_checks(db: Session, service_id: int, limit: int) -> list[Check]:
    """Newest-first slice of the service's check history."""
    return list(
        db.scalars(
            select(Check)
            .where(Check.service_id == service_id)
            .order_by(Check.checked_at.desc(), Check.id.desc())
            .limit(limit)
        )
    )


def process_check_result(db: Session, service: Service, status: CheckStatus) -> None:
    """Update incident state after one stored health check."""
    open_incident = get_open_incident(db, service.id)

    if status == CheckStatus.down:
        if open_incident is None:
            _maybe_open_incident(db, service)
        elif open_incident.ai_summary is None:
            # Ollama was unavailable when the incident opened; try again.
            _generate_summary(db, service, open_incident)
    elif status == CheckStatus.up and open_incident is not None:
        open_incident.resolved_at = datetime.now(UTC)
        db.commit()
        metrics.record_incident_resolved(service.name)
        logger.info(
            "incident resolved service=%s incident_id=%s", service.name, open_incident.id
        )


def _maybe_open_incident(db: Session, service: Service) -> None:
    """Open an incident when the newest N checks are all `down`."""
    threshold = get_settings().incident_failure_threshold
    streak = _recent_checks(db, service.id, limit=threshold)
    if len(streak) < threshold or any(check.status != CheckStatus.down for check in streak):
        return

    # The incident started when the failure streak began, not when the
    # threshold was crossed: streak is newest-first, so [-1] is the oldest.
    incident = Incident(service_id=service.id, started_at=streak[-1].checked_at)
    db.add(incident)
    db.commit()
    db.refresh(incident)
    metrics.record_incident_opened(service.name)
    logger.warning(
        "incident opened service=%s incident_id=%s after %s consecutive down checks",
        service.name,
        incident.id,
        threshold,
    )
    _generate_summary(db, service, incident)


def _generate_summary(db: Session, service: Service, incident: Incident) -> None:
    """Ask Ollama for a summary and store it; a failure leaves it NULL."""
    recent = _recent_checks(db, service.id, limit=PROMPT_CHECK_COUNT)
    prompt = build_incident_prompt(service, incident, recent)
    # The prompt is stored even when generation fails, so it is always
    # possible to see exactly what context the (attempted) summary used.
    incident.raw_context = prompt
    summary = ollama_client.generate(prompt)
    if summary is not None:
        incident.ai_summary = summary
        logger.info("AI summary stored for incident_id=%s", incident.id)
    db.commit()


def list_incidents(
    db: Session, service_id: int | None = None, active: bool | None = None, limit: int = 50
) -> list[Incident]:
    """Incidents newest-first, optionally filtered by service and/or open state."""
    query = select(Incident).order_by(Incident.started_at.desc(), Incident.id.desc())
    if service_id is not None:
        query = query.where(Incident.service_id == service_id)
    if active is True:
        query = query.where(Incident.resolved_at.is_(None))
    elif active is False:
        query = query.where(Incident.resolved_at.is_not(None))
    return list(db.scalars(query.limit(limit)))
