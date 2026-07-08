"""Tests for the service CRUD API and the check-history endpoint."""

from datetime import UTC, datetime, timedelta

from app.models import Check, CheckStatus
from tests.conftest import API_KEY_HEADER

SERVICE_PAYLOAD = {
    "name": "Personal API",
    "url": "https://example.com/health",
    "check_interval_seconds": 60,
}


def _create_service(client, payload=None):
    response = client.post("/services", json=payload or SERVICE_PAYLOAD, headers=API_KEY_HEADER)
    assert response.status_code == 201, response.text
    return response.json()


class TestApiKey:
    def test_write_without_key_is_rejected(self, client):
        assert client.post("/services", json=SERVICE_PAYLOAD).status_code == 401

    def test_write_with_wrong_key_is_rejected(self, client):
        response = client.post(
            "/services", json=SERVICE_PAYLOAD, headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 401

    def test_reads_do_not_need_a_key(self, client):
        assert client.get("/services").status_code == 200


class TestServiceCrud:
    def test_create_returns_the_service(self, client):
        data = _create_service(client)
        assert data["name"] == "Personal API"
        assert data["url"] == "https://example.com/health"
        assert data["check_interval_seconds"] == 60
        assert data["id"] == 1
        assert "created_at" in data

    def test_create_applies_default_interval_when_omitted(self, client):
        data = _create_service(
            client, {"name": "No interval", "url": "https://example.com/health"}
        )
        assert data["check_interval_seconds"] == 60  # DEFAULT_CHECK_INTERVAL_SECONDS

    def test_duplicate_name_returns_409(self, client):
        _create_service(client)
        response = client.post("/services", json=SERVICE_PAYLOAD, headers=API_KEY_HEADER)
        assert response.status_code == 409

    def test_invalid_url_returns_422(self, client):
        response = client.post(
            "/services",
            json={"name": "Bad URL", "url": "not-a-url"},
            headers=API_KEY_HEADER,
        )
        assert response.status_code == 422

    def test_list_returns_created_services(self, client):
        _create_service(client)
        _create_service(client, {"name": "Second", "url": "https://example.org/health"})
        names = [service["name"] for service in client.get("/services").json()]
        assert names == ["Personal API", "Second"]

    def test_get_by_id(self, client):
        created = _create_service(client)
        response = client.get(f"/services/{created['id']}")
        assert response.status_code == 200
        assert response.json()["name"] == "Personal API"

    def test_get_unknown_id_returns_404(self, client):
        assert client.get("/services/999").status_code == 404

    def test_partial_update(self, client):
        created = _create_service(client)
        response = client.patch(
            f"/services/{created['id']}",
            json={"check_interval_seconds": 120},
            headers=API_KEY_HEADER,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["check_interval_seconds"] == 120
        assert data["name"] == "Personal API"  # untouched fields stay the same

    def test_update_without_key_is_rejected(self, client):
        created = _create_service(client)
        response = client.patch(f"/services/{created['id']}", json={"name": "Renamed"})
        assert response.status_code == 401

    def test_delete_removes_the_service(self, client):
        created = _create_service(client)
        assert (
            client.delete(f"/services/{created['id']}", headers=API_KEY_HEADER).status_code == 204
        )
        assert client.get(f"/services/{created['id']}").status_code == 404


class TestCheckHistory:
    def _insert_checks(self, db_session, service_id: int, count: int) -> None:
        base = datetime.now(UTC)
        for i in range(count):
            db_session.add(
                Check(
                    service_id=service_id,
                    checked_at=base + timedelta(seconds=i),
                    status=CheckStatus.up,
                    latency_ms=100 + i,
                    http_code=200,
                )
            )
        db_session.commit()

    def test_history_returns_newest_first(self, client, db_session):
        created = _create_service(client)
        self._insert_checks(db_session, created["id"], count=3)

        checks = client.get(f"/services/{created['id']}/checks").json()
        assert len(checks) == 3
        latencies = [check["latency_ms"] for check in checks]
        assert latencies == [102, 101, 100]  # newest first
        assert checks[0]["status"] == "up"

    def test_history_respects_limit(self, client, db_session):
        created = _create_service(client)
        self._insert_checks(db_session, created["id"], count=5)

        checks = client.get(f"/services/{created['id']}/checks", params={"limit": 2}).json()
        assert len(checks) == 2

    def test_history_for_unknown_service_returns_404(self, client):
        assert client.get("/services/999/checks").status_code == 404
