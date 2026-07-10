"""Bounded retries and abandoned-lease recovery for the AI worker."""

from datetime import UTC, datetime, timedelta

from app.ai import worker
from app.ai.providers import ProviderError, ProviderErrorCode
from app.models import AISummaryStatus, Check, CheckStatus, Incident, Service


class FailingProvider:
    def __init__(self, code=ProviderErrorCode.rate_limit, retryable=True):
        self.code = code
        self.retryable = retryable

    def generate(self, request):
        raise ProviderError(self.code, retryable=self.retryable)


def _incident(db_session, *, attempts: int) -> Incident:
    service = Service(
        name=f"worker-{attempts}",
        url="https://example.com",
        check_interval_seconds=60,
    )
    db_session.add(service)
    db_session.commit()
    db_session.add(
        Check(
            service_id=service.id,
            checked_at=datetime.now(UTC),
            status=CheckStatus.down,
            latency_ms=None,
            http_code=None,
        )
    )
    incident = Incident(
        service_id=service.id,
        started_at=datetime.now(UTC),
        ai_status=AISummaryStatus.processing,
        ai_attempt_count=attempts,
        ai_processing_started_at=datetime.now(UTC),
    )
    db_session.add(incident)
    db_session.commit()
    return incident


def test_transient_failure_schedules_bounded_retry(db_session, monkeypatch):
    incident = _incident(db_session, attempts=1)
    monkeypatch.setattr(
        "app.services.ai_settings_manager.build_provider",
        lambda setting: FailingProvider(),
    )

    worker.process_incident_summary(db_session, incident)

    assert incident.ai_status == AISummaryStatus.pending
    assert incident.ai_next_attempt_at is not None
    assert incident.ai_last_error_code == "rate_limit"


def test_third_failure_stops_automatic_retries(db_session, monkeypatch):
    incident = _incident(db_session, attempts=3)
    monkeypatch.setattr(
        "app.services.ai_settings_manager.build_provider",
        lambda setting: FailingProvider(),
    )

    worker.process_incident_summary(db_session, incident)

    assert incident.ai_status == AISummaryStatus.failed
    assert incident.ai_next_attempt_at is None


def test_worker_recovers_abandoned_processing_lease(db_session, monkeypatch):
    incident = _incident(db_session, attempts=1)
    incident.ai_processing_started_at = datetime.now(UTC) - timedelta(minutes=20)
    db_session.commit()
    processed: list[int] = []

    monkeypatch.setattr(worker, "SessionLocal", lambda: db_session)

    def fake_process(db, due_incident):
        processed.append(due_incident.id)
        due_incident.ai_status = AISummaryStatus.completed
        db.commit()

    monkeypatch.setattr(worker, "process_incident_summary", fake_process)

    worker.process_pending_summaries()

    assert processed == [incident.id]
    assert db_session.get(Incident, incident.id).ai_status == AISummaryStatus.completed
