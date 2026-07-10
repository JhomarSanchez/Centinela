"""Phase 6 tests for sessions, encrypted AI settings, dashboard, and timelines."""

from datetime import UTC, datetime, timedelta

from app.models import AISetting, Check, CheckStatus, Incident, Service
from app.security import decrypt_credential
from tests.conftest import API_KEY_HEADER


def _service(db_session, name="phase6") -> Service:
    service = Service(
        name=name,
        url="https://example.com/health?token=secret",
        check_interval_seconds=60,
    )
    db_session.add(service)
    db_session.commit()
    return service


def test_browser_session_requires_csrf_for_mutations(client):
    login = client.post("/api/v1/auth/session", json={"api_key": "test-key"})
    assert login.status_code == 200
    csrf = login.json()["csrf_token"]

    assert client.get("/api/v1/auth/session").status_code == 200
    assert (
        client.post(
            "/api/v1/services",
            json={"name": "No CSRF", "url": "https://example.com"},
        ).status_code
        == 403
    )
    response = client.post(
        "/api/v1/services",
        json={"name": "With CSRF", "url": "https://example.com"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 201


def test_ai_key_is_encrypted_and_never_returned(client, db_session):
    response = client.put(
        "/api/v1/ai/config",
        headers=API_KEY_HEADER,
        json={
            "provider": "openai",
            "model": "test-model",
            "summary_language": "es",
            "enabled": True,
            "api_key": "sk-test-super-secret",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["credential_configured"] is True
    assert payload["api_key_hint"] == "cret"
    assert "sk-test" not in response.text

    stored = db_session.get(AISetting, 1)
    assert stored.encrypted_api_key != "sk-test-super-secret"
    assert decrypt_credential(stored.encrypted_api_key) == "sk-test-super-secret"

    rotated = client.put(
        "/api/v1/ai/config",
        headers=API_KEY_HEADER,
        json={
            "provider": "openai",
            "model": "test-model",
            "summary_language": "es",
            "enabled": True,
            "api_key": "sk-test-rotated-value",
        },
    )
    db_session.refresh(stored)
    assert rotated.json()["api_key_hint"] == "alue"
    assert decrypt_credential(stored.encrypted_api_key) == "sk-test-rotated-value"


def test_service_summaries_and_dashboard_use_real_check_data(client, db_session):
    service = _service(db_session)
    db_session.add_all(
        [
            Check(
                service_id=service.id,
                checked_at=datetime.now(UTC) - timedelta(minutes=5),
                status=CheckStatus.down,
                latency_ms=None,
                http_code=None,
            ),
            Check(
                service_id=service.id,
                checked_at=datetime.now(UTC),
                status=CheckStatus.up,
                latency_ms=80,
                http_code=200,
            ),
        ]
    )
    db_session.commit()

    services = client.get("/api/v1/services", headers=API_KEY_HEADER).json()
    assert services[0]["latest_status"] == "up"
    assert services[0]["last_latency_ms"] == 80
    assert services[0]["availability_24h"] == 50.0

    dashboard = client.get("/api/v1/dashboard/summary", headers=API_KEY_HEADER).json()
    assert dashboard["total_services"] == 1
    assert dashboard["up_services"] == 1
    assert dashboard["availability_24h"] == 50.0


def test_timeline_buckets_statuses(client, db_session):
    service = _service(db_session)
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    db_session.add_all(
        [
            Check(
                service_id=service.id,
                checked_at=now - timedelta(minutes=2),
                status=CheckStatus.up,
                latency_ms=100,
                http_code=200,
            ),
            Check(
                service_id=service.id,
                checked_at=now - timedelta(minutes=1),
                status=CheckStatus.degraded,
                latency_ms=3000,
                http_code=200,
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/services/{service.id}/timeline",
        headers=API_KEY_HEADER,
        params={
            "from": (now - timedelta(hours=1)).isoformat(),
            "to": now.isoformat(),
            "bucket": "5m",
        },
    )
    assert response.status_code == 200
    point = response.json()["points"][0]
    assert point["total"] == 2
    assert point["up"] == 1
    assert point["degraded"] == 1
    assert point["availability_percent"] == 50.0


def test_incident_context_is_not_in_normal_responses(client, db_session):
    service = _service(db_session)
    incident = Incident(service_id=service.id, raw_context="private prompt")
    db_session.add(incident)
    db_session.commit()

    listing = client.get("/api/v1/incidents", headers=API_KEY_HEADER)
    assert listing.status_code == 200
    assert "raw_context" not in listing.json()[0]

    context = client.get(
        f"/api/v1/incidents/{incident.id}/context", headers=API_KEY_HEADER
    )
    assert context.json()["raw_context"] == "private prompt"


def test_manual_check_reuses_health_check_pipeline(client, db_session, monkeypatch):
    service = _service(db_session)
    monkeypatch.setattr(
        "app.services.check_runner.run_check",
        lambda *args, **kwargs: (CheckStatus.up, 45, 204),
    )

    response = client.post(
        f"/api/v1/services/{service.id}/checks/run", headers=API_KEY_HEADER
    )
    assert response.status_code == 201
    assert response.json()["status"] == "up"
    assert response.json()["latency_ms"] == 45
