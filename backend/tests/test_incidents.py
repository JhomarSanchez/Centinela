"""Tests for incident detection, resolution, AI summaries, and the incidents API."""

from datetime import UTC, datetime, timedelta

from app.models import Check, CheckStatus, Incident, Service
from app.services import incident_manager
from tests.conftest import API_KEY_HEADER

NOW = datetime(2026, 7, 8, 12, 0, 0, tzinfo=UTC)


def _add_service(db_session, name="svc") -> Service:
    service = Service(name=name, url="https://example.com/health", check_interval_seconds=60)
    db_session.add(service)
    db_session.commit()
    return service


def _add_check(db_session, service_id: int, status: CheckStatus, minutes_ago: int) -> Check:
    check = Check(
        service_id=service_id,
        checked_at=NOW - timedelta(minutes=minutes_ago),
        status=status,
        latency_ms=100 if status != CheckStatus.down else None,
        http_code=200 if status != CheckStatus.down else None,
    )
    db_session.add(check)
    db_session.commit()
    return check


def _open_incidents(db_session, service_id: int) -> list[Incident]:
    return incident_manager.list_incidents(db_session, service_id=service_id, active=True)


class TestIncidentDetection:
    def test_three_consecutive_downs_open_an_incident(self, db_session):
        service = _add_service(db_session)
        for minutes_ago in (3, 2, 1):
            _add_check(db_session, service.id, CheckStatus.down, minutes_ago)

        incident_manager.process_check_result(db_session, service, CheckStatus.down)

        incidents = _open_incidents(db_session, service.id)
        assert len(incidents) == 1
        # The incident starts when the failure streak began (oldest down).
        started_at = incidents[0].started_at.replace(tzinfo=UTC)
        assert started_at == NOW - timedelta(minutes=3)

    def test_fewer_downs_than_the_threshold_do_not_open_one(self, db_session):
        service = _add_service(db_session)
        for minutes_ago in (2, 1):
            _add_check(db_session, service.id, CheckStatus.down, minutes_ago)

        incident_manager.process_check_result(db_session, service, CheckStatus.down)

        assert _open_incidents(db_session, service.id) == []

    def test_a_degraded_check_breaks_the_streak(self, db_session):
        service = _add_service(db_session)
        _add_check(db_session, service.id, CheckStatus.down, 3)
        _add_check(db_session, service.id, CheckStatus.degraded, 2)
        _add_check(db_session, service.id, CheckStatus.down, 1)

        incident_manager.process_check_result(db_session, service, CheckStatus.down)

        assert _open_incidents(db_session, service.id) == []

    def test_more_downs_do_not_open_a_second_incident(self, db_session):
        service = _add_service(db_session)
        for minutes_ago in (4, 3, 2):
            _add_check(db_session, service.id, CheckStatus.down, minutes_ago)
        incident_manager.process_check_result(db_session, service, CheckStatus.down)

        _add_check(db_session, service.id, CheckStatus.down, 1)
        incident_manager.process_check_result(db_session, service, CheckStatus.down)

        all_incidents = incident_manager.list_incidents(db_session, service_id=service.id)
        assert len(all_incidents) == 1

    def test_an_up_check_resolves_the_incident(self, db_session):
        service = _add_service(db_session)
        for minutes_ago in (3, 2, 1):
            _add_check(db_session, service.id, CheckStatus.down, minutes_ago)
        incident_manager.process_check_result(db_session, service, CheckStatus.down)

        incident_manager.process_check_result(db_session, service, CheckStatus.up)

        assert _open_incidents(db_session, service.id) == []
        resolved = incident_manager.list_incidents(db_session, service_id=service.id)[0]
        assert resolved.resolved_at is not None

    def test_a_new_streak_after_recovery_opens_a_new_incident(self, db_session):
        service = _add_service(db_session)
        for minutes_ago in (9, 8, 7):
            _add_check(db_session, service.id, CheckStatus.down, minutes_ago)
        incident_manager.process_check_result(db_session, service, CheckStatus.down)
        incident_manager.process_check_result(db_session, service, CheckStatus.up)
        _add_check(db_session, service.id, CheckStatus.up, 6)

        for minutes_ago in (3, 2, 1):
            _add_check(db_session, service.id, CheckStatus.down, minutes_ago)
        incident_manager.process_check_result(db_session, service, CheckStatus.down)

        all_incidents = incident_manager.list_incidents(db_session, service_id=service.id)
        assert len(all_incidents) == 2
        assert len(_open_incidents(db_session, service.id)) == 1


class TestAiSummary:
    def _open_with_streak(self, db_session, service):
        for minutes_ago in (3, 2, 1):
            _add_check(db_session, service.id, CheckStatus.down, minutes_ago)
        incident_manager.process_check_result(db_session, service, CheckStatus.down)
        return incident_manager.list_incidents(db_session, service_id=service.id)[0]

    def test_summary_and_context_are_stored_when_ollama_answers(self, db_session, monkeypatch):
        monkeypatch.setattr(
            "app.services.incident_manager.ollama_client.generate",
            lambda prompt: "The service stopped responding.",
        )
        service = _add_service(db_session)

        incident = self._open_with_streak(db_session, service)

        assert incident.ai_summary == "The service stopped responding."
        assert "svc" in incident.raw_context
        assert "status=down" in incident.raw_context

    def test_incident_opens_without_summary_when_ollama_fails(self, db_session):
        # OLLAMA_ENABLED=false in tests, so the real client returns None.
        service = _add_service(db_session)

        incident = self._open_with_streak(db_session, service)

        assert incident.ai_summary is None
        assert incident.raw_context is not None  # the prompt is kept anyway

    def test_summary_is_retried_on_the_next_down_check(self, db_session, monkeypatch):
        service = _add_service(db_session)
        incident = self._open_with_streak(db_session, service)
        assert incident.ai_summary is None

        monkeypatch.setattr(
            "app.services.incident_manager.ollama_client.generate",
            lambda prompt: "Recovered context: still failing.",
        )
        _add_check(db_session, service.id, CheckStatus.down, 0)
        incident_manager.process_check_result(db_session, service, CheckStatus.down)

        db_session.refresh(incident)
        assert incident.ai_summary == "Recovered context: still failing."


class TestIncidentsApi:
    def _seed_incident(self, db_session, service_id: int, resolved: bool) -> Incident:
        incident = Incident(
            service_id=service_id,
            started_at=NOW - timedelta(hours=1),
            resolved_at=NOW if resolved else None,
            ai_summary="summary" if resolved else None,
        )
        db_session.add(incident)
        db_session.commit()
        return incident

    def test_list_all_incidents(self, client, db_session):
        service = _add_service(db_session)
        self._seed_incident(db_session, service.id, resolved=True)
        self._seed_incident(db_session, service.id, resolved=False)

        response = client.get("/incidents")

        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_filter_active_incidents(self, client, db_session):
        service = _add_service(db_session)
        self._seed_incident(db_session, service.id, resolved=True)
        open_incident = self._seed_incident(db_session, service.id, resolved=False)

        data = client.get("/incidents", params={"active": "true"}).json()

        assert [incident["id"] for incident in data] == [open_incident.id]
        assert data[0]["resolved_at"] is None

    def test_filter_resolved_incidents(self, client, db_session):
        service = _add_service(db_session)
        resolved = self._seed_incident(db_session, service.id, resolved=True)
        self._seed_incident(db_session, service.id, resolved=False)

        data = client.get("/incidents", params={"active": "false"}).json()

        assert [incident["id"] for incident in data] == [resolved.id]
        assert data[0]["ai_summary"] == "summary"

    def test_incidents_per_service(self, client, db_session):
        first = _add_service(db_session, name="first")
        second = _add_service(db_session, name="second")
        self._seed_incident(db_session, first.id, resolved=False)
        self._seed_incident(db_session, second.id, resolved=False)

        data = client.get(f"/services/{first.id}/incidents").json()

        assert len(data) == 1
        assert data[0]["service_id"] == first.id

    def test_incidents_for_unknown_service_return_404(self, client):
        assert client.get("/services/999/incidents").status_code == 404

    def test_deleting_a_service_deletes_its_incidents(self, client, db_session):
        service = _add_service(db_session)
        self._seed_incident(db_session, service.id, resolved=False)

        response = client.delete(f"/services/{service.id}", headers=API_KEY_HEADER)
        assert response.status_code == 204

        assert client.get("/incidents").json() == []
