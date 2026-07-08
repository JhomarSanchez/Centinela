"""Builds the incident-summary prompt from database facts.

The prompt contains only real, structured data (service name, timestamps,
recent check results). Giving the LLM concrete facts and a tight instruction
keeps summaries factual and short instead of speculative.
"""

from app.models import Check, Incident, Service


def _format_check(check: Check) -> str:
    latency = f"{check.latency_ms}ms" if check.latency_ms is not None else "no response"
    http_code = check.http_code if check.http_code is not None else "none"
    return (
        f"- {check.checked_at.isoformat()} status={check.status.value} "
        f"http_code={http_code} latency={latency}"
    )


def build_incident_prompt(service: Service, incident: Incident, recent_checks: list[Check]) -> str:
    """Compose the full prompt sent to Ollama for one incident.

    `recent_checks` is expected newest-first, as returned by the check
    history query; it is reversed here so the LLM reads events in order.
    """
    checks_lines = "\n".join(_format_check(check) for check in reversed(recent_checks))
    return (
        "You are the assistant of a service-monitoring system called Centinela.\n"
        "A monitored service is failing and an incident was opened.\n\n"
        f"Service name: {service.name}\n"
        f"Service URL: {service.url}\n"
        f"Incident started at: {incident.started_at.isoformat()} (UTC)\n\n"
        "Most recent health checks (oldest first):\n"
        f"{checks_lines}\n\n"
        "Write a short incident summary in plain English (3-4 sentences, no markdown):\n"
        "1. What is happening and since when.\n"
        "2. What the check data suggests (e.g. timeouts vs HTTP errors).\n"
        "3. One reasonable first step to investigate.\n"
        "Only use the data above; do not invent numbers or causes."
    )
