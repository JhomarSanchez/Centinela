"""Tests for health-check classification and execution."""

import httpx
import pytest

from app.models import CheckStatus
from app.services.health_checker import classify, run_check

DEGRADED_MS = 2000


class TestClassify:
    """The pure classification rules."""

    @pytest.mark.parametrize(
        ("http_code", "latency_ms", "expected"),
        [
            (None, 5000, CheckStatus.down),  # no response at all
            (500, 50, CheckStatus.down),
            (503, 50, CheckStatus.down),
            (404, 50, CheckStatus.degraded),
            (401, 50, CheckStatus.degraded),
            (200, 50, CheckStatus.up),
            (204, 50, CheckStatus.up),
            (301, 50, CheckStatus.up),
            (200, DEGRADED_MS, CheckStatus.up),  # exactly at the threshold is still up
            (200, DEGRADED_MS + 1, CheckStatus.degraded),  # slower than threshold
        ],
    )
    def test_classification(self, http_code, latency_ms, expected):
        assert classify(http_code, latency_ms, DEGRADED_MS) == expected


class TestRunCheck:
    """run_check with a mocked HTTP transport (no real network)."""

    def _client_returning(self, status_code: int) -> httpx.Client:
        transport = httpx.MockTransport(lambda request: httpx.Response(status_code))
        return httpx.Client(transport=transport)

    def test_healthy_service_is_up(self):
        status, latency_ms, http_code = run_check(
            "https://example.com/health",
            timeout=5.0,
            degraded_latency_ms=DEGRADED_MS,
            client=self._client_returning(200),
        )
        assert status == CheckStatus.up
        assert http_code == 200
        assert isinstance(latency_ms, int) and latency_ms >= 0

    def test_server_error_is_down(self):
        status, _, http_code = run_check(
            "https://example.com/health",
            timeout=5.0,
            degraded_latency_ms=DEGRADED_MS,
            client=self._client_returning(503),
        )
        assert status == CheckStatus.down
        assert http_code == 503

    def test_connection_error_is_down_with_no_http_code(self):
        def raise_error(request):
            raise httpx.ConnectError("connection refused", request=request)

        client = httpx.Client(transport=httpx.MockTransport(raise_error))
        status, latency_ms, http_code = run_check(
            "https://unreachable.invalid/health",
            timeout=5.0,
            degraded_latency_ms=DEGRADED_MS,
            client=client,
        )
        assert status == CheckStatus.down
        assert http_code is None
        # No response means no real latency measurement.
        assert latency_ms is None
