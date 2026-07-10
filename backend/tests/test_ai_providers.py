"""Provider contract and prompt privacy tests for Phase 6."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.ai.prompt import build_incident_prompt, sanitize_service_url
from app.ai.providers import AnthropicProvider, GenerationRequest, OpenAIProvider
from app.models import Check, CheckStatus, Incident, Service


def test_sanitize_service_url_removes_credentials_and_query():
    assert (
        sanitize_service_url("https://user:pass@example.com:8443/health?token=secret#debug")
        == "https://example.com:8443/health"
    )


def test_spanish_prompt_is_versioned_and_private():
    service = Service(
        name="API",
        url="https://example.com/health?api_key=secret",
        check_interval_seconds=60,
    )
    incident = Incident(service_id=1, started_at=datetime.now(UTC))
    check = Check(
        service_id=1,
        checked_at=datetime.now(UTC),
        status=CheckStatus.down,
        latency_ms=None,
        http_code=None,
    )
    prompt = build_incident_prompt(service, incident, [check], language="es")
    assert "Escribe un resumen breve en español" in prompt
    assert "api_key" not in prompt
    assert "secret" not in prompt


def test_openai_adapter_normalizes_usage():
    response = SimpleNamespace(
        output_text=" Summary ",
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )
    client = SimpleNamespace(
        responses=SimpleNamespace(create=lambda **kwargs: response)
    )
    result = OpenAIProvider("unused", 1, client=client).generate(
        GenerationRequest("prompt", "test-model")
    )
    assert result.text == "Summary"
    assert result.input_tokens == 10
    assert result.output_tokens == 5


def test_anthropic_adapter_normalizes_text_blocks():
    response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="Summary")],
        usage=SimpleNamespace(input_tokens=12, output_tokens=6),
    )
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs: response))
    result = AnthropicProvider("unused", 1, client=client).generate(
        GenerationRequest("prompt", "test-model")
    )
    assert result.text == "Summary"
    assert result.input_tokens == 12
