"""Runs a single HTTP health check and classifies the result.

The classification rules live in a pure function (`classify`) so they can be
unit-tested without any network involved.
"""

import time

import httpx

from app.models import CheckStatus


def classify(
    http_code: int | None, latency_ms: int | None, degraded_latency_ms: int
) -> CheckStatus:
    """Turn a raw HTTP result into an up/degraded/down status.

    Rules:
    - No response at all (timeout, connection refused) -> down.
    - 5xx -> down: the service answered but is failing.
    - 4xx -> degraded: reachable but misbehaving (broken route, auth, etc.).
    - 2xx/3xx slower than the threshold -> degraded.
    - Anything else -> up.
    """
    if http_code is None:
        return CheckStatus.down
    if http_code >= 500:
        return CheckStatus.down
    if http_code >= 400:
        return CheckStatus.degraded
    if latency_ms is not None and latency_ms > degraded_latency_ms:
        return CheckStatus.degraded
    return CheckStatus.up


def run_check(
    url: str,
    *,
    timeout: float,
    degraded_latency_ms: int,
    client: httpx.Client | None = None,
) -> tuple[CheckStatus, int | None, int | None]:
    """Perform one HTTP GET against `url`.

    Returns (status, latency_ms, http_code). An injectable `client` lets tests
    swap in httpx.MockTransport instead of hitting the real network.
    """
    owns_client = client is None
    if client is None:
        client = httpx.Client(timeout=timeout, follow_redirects=True)

    start = time.perf_counter()
    try:
        response = client.get(url)
        http_code: int | None = response.status_code
        latency_ms: int | None = int((time.perf_counter() - start) * 1000)
    except httpx.HTTPError:
        # Covers timeouts, DNS failures, refused connections, etc.
        # Latency stays None: measuring "time until the timeout fired" would
        # pollute latency graphs with values that are not real response times.
        http_code = None
        latency_ms = None
    finally:
        if owns_client:
            client.close()

    return classify(http_code, latency_ms, degraded_latency_ms), latency_ms, http_code
