"""Tests for Prometheus metric recording and the /metrics endpoint.

prometheus_client keeps metrics in a process-global registry, so each test
uses its own unique service name to stay independent of the others.
"""

from datetime import UTC, datetime

from prometheus_client import REGISTRY

from app import metrics
from app.models import Check, CheckStatus, Service
from tests.conftest import API_KEY_HEADER


def _gauge(name: str, service_name: str) -> float | None:
    return REGISTRY.get_sample_value(name, {"service_name": service_name})


def _counter(service_name: str, status: str) -> float | None:
    return REGISTRY.get_sample_value(
        "centinela_checks_total", {"service_name": service_name, "status": status}
    )


class TestRecordCheck:
    def test_up_check_sets_all_series(self):
        metrics.record_check("m-up", CheckStatus.up, latency_ms=250)

        assert _gauge("centinela_service_status", "m-up") == 2
        assert _gauge("centinela_service_up", "m-up") == 1
        assert _gauge("centinela_check_latency_seconds", "m-up") == 0.25
        assert _counter("m-up", "up") == 1

    def test_degraded_counts_as_not_up(self):
        metrics.record_check("m-degraded", CheckStatus.degraded, latency_ms=3000)

        assert _gauge("centinela_service_status", "m-degraded") == 1
        assert _gauge("centinela_service_up", "m-degraded") == 0

    def test_down_check_without_latency_skips_the_latency_gauge(self):
        metrics.record_check("m-down", CheckStatus.down, latency_ms=None)

        assert _gauge("centinela_service_status", "m-down") == 0
        assert _gauge("centinela_check_latency_seconds", "m-down") is None
        assert _counter("m-down", "down") == 1

    def test_forget_service_removes_every_series(self):
        metrics.record_check("m-forgotten", CheckStatus.up, latency_ms=100)
        metrics.forget_service("m-forgotten")

        assert _gauge("centinela_service_status", "m-forgotten") is None
        assert _gauge("centinela_service_up", "m-forgotten") is None
        assert _gauge("centinela_check_latency_seconds", "m-forgotten") is None
        assert _counter("m-forgotten", "up") is None

    def test_forget_unknown_service_is_a_no_op(self):
        metrics.forget_service("m-never-existed")  # must not raise


class TestInitFromDb:
    def test_restores_gauges_from_latest_check_without_counting(self, db_session):
        service = Service(name="m-restored", url="https://example.com", check_interval_seconds=60)
        db_session.add(service)
        db_session.commit()
        db_session.add(
            Check(
                service_id=service.id,
                checked_at=datetime(2026, 7, 8, 12, 0, tzinfo=UTC),
                status=CheckStatus.degraded,
                latency_ms=1500,
                http_code=404,
            )
        )
        db_session.commit()

        metrics.init_from_db(db_session)

        assert _gauge("centinela_service_status", "m-restored") == 1
        assert _gauge("centinela_check_latency_seconds", "m-restored") == 1.5
        # Counters only count checks observed by this process.
        assert _counter("m-restored", "degraded") is None

    def test_service_without_checks_stays_absent(self, db_session):
        db_session.add(
            Service(name="m-unchecked", url="https://example.com", check_interval_seconds=60)
        )
        db_session.commit()

        metrics.init_from_db(db_session)

        assert _gauge("centinela_service_status", "m-unchecked") is None


class TestMetricsEndpoint:
    def test_metrics_endpoint_returns_prometheus_text_format(self, client):
        metrics.record_check("m-endpoint", CheckStatus.up, latency_ms=120)

        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert 'centinela_service_status{service_name="m-endpoint"} 2.0' in response.text

    def test_metrics_endpoint_needs_no_api_key(self, client):
        assert client.get("/metrics").status_code == 200


class TestMetricsFollowServiceLifecycle:
    def test_deleting_a_service_drops_its_series(self, client):
        created = client.post(
            "/services",
            json={"name": "m-deleted", "url": "https://example.com/health"},
            headers=API_KEY_HEADER,
        ).json()
        metrics.record_check("m-deleted", CheckStatus.up, latency_ms=90)

        response = client.delete(f"/services/{created['id']}", headers=API_KEY_HEADER)
        assert response.status_code == 204

        assert _gauge("centinela_service_status", "m-deleted") is None

    def test_renaming_a_service_moves_its_series(self, client, db_session):
        created = client.post(
            "/services",
            json={"name": "m-old-name", "url": "https://example.com/health"},
            headers=API_KEY_HEADER,
        ).json()
        db_session.add(
            Check(
                service_id=created["id"],
                checked_at=datetime(2026, 7, 8, 12, 0, tzinfo=UTC),
                status=CheckStatus.up,
                latency_ms=80,
                http_code=200,
            )
        )
        db_session.commit()
        metrics.record_check("m-old-name", CheckStatus.up, latency_ms=80)

        response = client.patch(
            f"/services/{created['id']}",
            json={"name": "m-new-name"},
            headers=API_KEY_HEADER,
        )
        assert response.status_code == 200

        assert _gauge("centinela_service_status", "m-old-name") is None
        # Re-seeded from the stored check so the dashboard shows no gap.
        assert _gauge("centinela_service_status", "m-new-name") == 2
