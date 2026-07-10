"""Background processing for provider-neutral incident summaries."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.ai.prompt import PROMPT_VERSION, build_incident_prompt
from app.ai.providers import GenerationRequest, ProviderError, ProviderErrorCode
from app.database import SessionLocal
from app.models import AISummaryStatus, Check, Incident
from app.services import ai_settings_manager

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
RETRY_DELAYS_SECONDS = (60, 300)
LEASE_TIMEOUT_MINUTES = 10
PROMPT_CHECK_COUNT = 10


def queue_summary(db: Session, incident: Incident) -> None:
    """Queue a new summary only when a provider is ready to use."""
    setting = ai_settings_manager.get_or_create(db)
    incident.ai_status = (
        AISummaryStatus.pending
        if ai_settings_manager.is_ready(setting)
        else AISummaryStatus.skipped
    )
    incident.ai_next_attempt_at = (
        datetime.now(UTC) if incident.ai_status == AISummaryStatus.pending else None
    )
    incident.ai_attempt_count = 0
    incident.ai_last_error_code = None


def retry_summary(db: Session, incident: Incident) -> Incident:
    """Reset a failed/skipped incident for an explicit administrative retry."""
    setting = ai_settings_manager.get_or_create(db)
    if not ai_settings_manager.is_ready(setting):
        raise ProviderError(ProviderErrorCode.not_configured, retryable=False)
    incident.ai_status = AISummaryStatus.pending
    incident.ai_attempt_count = 0
    incident.ai_next_attempt_at = datetime.now(UTC)
    incident.ai_processing_started_at = None
    incident.ai_last_error_code = None
    db.commit()
    db.refresh(incident)
    return incident


def _recent_checks(db: Session, service_id: int) -> list[Check]:
    return list(
        db.scalars(
            select(Check)
            .where(Check.service_id == service_id)
            .order_by(Check.checked_at.desc(), Check.id.desc())
            .limit(PROMPT_CHECK_COUNT)
        )
    )


def _handle_failure(db: Session, incident: Incident, error: ProviderError) -> None:
    incident.ai_last_error_code = error.code.value
    incident.ai_processing_started_at = None
    if error.retryable and incident.ai_attempt_count < MAX_ATTEMPTS:
        delay_index = min(incident.ai_attempt_count - 1, len(RETRY_DELAYS_SECONDS) - 1)
        incident.ai_status = AISummaryStatus.pending
        incident.ai_next_attempt_at = datetime.now(UTC) + timedelta(
            seconds=RETRY_DELAYS_SECONDS[delay_index]
        )
    else:
        incident.ai_status = AISummaryStatus.failed
        incident.ai_next_attempt_at = None
    db.commit()


def process_incident_summary(db: Session, incident: Incident) -> None:
    """Generate and persist one summary; all provider errors stay best-effort."""
    setting = ai_settings_manager.get_or_create(db)
    provider = ai_settings_manager.build_provider(setting)
    service = incident.service
    prompt = build_incident_prompt(
        service,
        incident,
        _recent_checks(db, service.id),
        language=setting.summary_language.value,
    )
    incident.raw_context = prompt
    incident.prompt_version = PROMPT_VERSION
    incident.ai_provider = setting.provider
    incident.ai_model = setting.model
    db.commit()
    try:
        result = provider.generate(GenerationRequest(prompt=prompt, model=setting.model))
    except ProviderError as exc:
        _handle_failure(db, incident, exc)
        logger.warning(
            "AI summary failed incident_id=%s provider=%s code=%s",
            incident.id,
            setting.provider.value,
            exc.code.value,
        )
        return
    incident.ai_summary = result.text
    incident.ai_status = AISummaryStatus.completed
    incident.ai_generated_at = datetime.now(UTC)
    incident.ai_next_attempt_at = None
    incident.ai_processing_started_at = None
    incident.ai_last_error_code = None
    incident.ai_input_tokens = result.input_tokens
    incident.ai_output_tokens = result.output_tokens
    incident.ai_latency_ms = result.latency_ms
    db.commit()
    logger.info("AI summary stored incident_id=%s provider=%s", incident.id, result.provider)


def process_pending_summaries() -> None:
    """Recover abandoned leases and process a small due batch."""
    now = datetime.now(UTC)
    with SessionLocal() as db:
        lease_cutoff = now - timedelta(minutes=LEASE_TIMEOUT_MINUTES)
        db.execute(
            update(Incident)
            .where(
                Incident.ai_status == AISummaryStatus.processing,
                Incident.ai_processing_started_at < lease_cutoff,
            )
            .values(
                ai_status=AISummaryStatus.pending,
                ai_next_attempt_at=now,
                ai_processing_started_at=None,
            )
        )
        db.commit()
        due_ids = list(
            db.scalars(
                select(Incident.id)
                .where(
                    Incident.ai_status == AISummaryStatus.pending,
                    Incident.ai_next_attempt_at <= now,
                )
                .order_by(Incident.ai_next_attempt_at, Incident.id)
                .limit(5)
            )
        )

    for incident_id in due_ids:
        with SessionLocal() as db:
            incident = db.get(Incident, incident_id)
            if incident is None or incident.ai_status != AISummaryStatus.pending:
                continue
            incident.ai_status = AISummaryStatus.processing
            incident.ai_attempt_count += 1
            incident.ai_processing_started_at = datetime.now(UTC)
            db.commit()
            try:
                process_incident_summary(db, incident)
            except ProviderError as exc:
                _handle_failure(db, incident, exc)
            except Exception:
                logger.exception("unexpected AI worker failure incident_id=%s", incident_id)
                _handle_failure(
                    db,
                    incident,
                    ProviderError(ProviderErrorCode.provider_unavailable, retryable=True),
                )
