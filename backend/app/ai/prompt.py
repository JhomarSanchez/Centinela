"""Builds a privacy-conscious incident-summary prompt from database facts.

The prompt contains only real, structured data (service name, timestamps,
recent check results). Giving the LLM concrete facts and a tight instruction
keeps summaries factual and short instead of speculative.
"""

from urllib.parse import urlsplit, urlunsplit

from app.models import Check, Incident, Service

PROMPT_VERSION = 2


def _format_check(check: Check) -> str:
    latency = f"{check.latency_ms}ms" if check.latency_ms is not None else "no response"
    http_code = check.http_code if check.http_code is not None else "none"
    return (
        f"- {check.checked_at.isoformat()} status={check.status.value} "
        f"http_code={http_code} latency={latency}"
    )


def sanitize_service_url(url: str) -> str:
    """Strip credentials, query parameters, and fragments before external AI use."""
    parsed = urlsplit(url)
    hostname = parsed.hostname or ""
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    port = f":{parsed.port}" if parsed.port else ""
    return urlunsplit((parsed.scheme, f"{hostname}{port}", parsed.path or "/", "", ""))


def build_incident_prompt(
    service: Service,
    incident: Incident,
    recent_checks: list[Check],
    *,
    language: str = "es",
) -> str:
    """Compose the full prompt sent to Ollama for one incident.

    `recent_checks` is expected newest-first, as returned by the check
    history query; it is reversed here so the LLM reads events in order.
    """
    checks_lines = "\n".join(_format_check(check) for check in reversed(recent_checks))
    safe_url = sanitize_service_url(service.url)
    facts = (
        f"Service name: {service.name}\n"
        f"Service URL: {safe_url}\n"
        f"Incident started at: {incident.started_at.isoformat()} (UTC)\n\n"
        "Most recent health checks (oldest first):\n"
        f"{checks_lines}\n\n"
    )
    if language == "en":
        return (
            "You are the assistant of a service-monitoring system called Centinela.\n"
            "A monitored service is failing and an incident was opened.\n\n"
            f"{facts}"
            "Write a short incident summary in plain English (3-4 sentences, no markdown):\n"
            "1. What is happening and since when.\n"
            "2. What the check data suggests (for example timeouts versus HTTP errors).\n"
            "3. One reasonable first investigation step.\n"
            "Only use the data above; do not invent numbers or causes."
        )
    return (
        "Eres el asistente de un sistema de monitoreo de servicios llamado Centinela.\n"
        "Un servicio monitoreado está fallando y se abrió un incidente.\n\n"
        f"{facts}"
        "Escribe un resumen breve en español claro (3-4 oraciones, sin markdown):\n"
        "1. Qué está ocurriendo y desde cuándo.\n"
        "2. Qué sugieren los chequeos (por ejemplo timeouts frente a errores HTTP).\n"
        "3. Un primer paso razonable para investigar.\n"
        "Usa sólo los datos anteriores; no inventes cifras ni causas."
    )
