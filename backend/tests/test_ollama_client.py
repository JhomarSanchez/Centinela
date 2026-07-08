"""Tests for the Ollama HTTP client (mocked transport, no real LLM)."""

import json

import httpx

from app.ai import ollama_client
from app.config import Settings


def _enable_ollama(monkeypatch, **overrides):
    """Point the client at settings with Ollama enabled (tests disable it globally)."""
    settings = Settings(ollama_enabled=True, ollama_model="test-model", **overrides)
    monkeypatch.setattr(ollama_client, "get_settings", lambda: settings)


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_generate_returns_the_trimmed_response(monkeypatch):
    _enable_ollama(monkeypatch)
    client = _client(lambda request: httpx.Response(200, json={"response": "  Summary text.  "}))

    assert ollama_client.generate("prompt", client=client) == "Summary text."


def test_generate_sends_model_prompt_and_no_streaming(monkeypatch):
    _enable_ollama(monkeypatch)
    seen = {}

    def handler(request):
        seen.update(json.loads(request.read()))
        return httpx.Response(200, json={"response": "ok"})

    ollama_client.generate("why is it down?", client=_client(handler))

    assert seen["model"] == "test-model"
    assert seen["prompt"] == "why is it down?"
    assert seen["stream"] is False


def test_generate_returns_none_when_disabled():
    # conftest sets OLLAMA_ENABLED=false, so no patching needed here.
    assert ollama_client.generate("prompt") is None


def test_generate_returns_none_on_server_error(monkeypatch):
    _enable_ollama(monkeypatch)
    client = _client(lambda request: httpx.Response(500, text="model not found"))

    assert ollama_client.generate("prompt", client=client) is None


def test_generate_returns_none_on_connection_error(monkeypatch):
    _enable_ollama(monkeypatch)

    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    assert ollama_client.generate("prompt", client=_client(handler)) is None


def test_generate_returns_none_on_invalid_json(monkeypatch):
    _enable_ollama(monkeypatch)
    client = _client(lambda request: httpx.Response(200, text="not json at all"))

    assert ollama_client.generate("prompt", client=client) is None


def test_generate_returns_none_on_empty_response(monkeypatch):
    _enable_ollama(monkeypatch)
    client = _client(lambda request: httpx.Response(200, json={"response": "   "}))

    assert ollama_client.generate("prompt", client=client) is None
