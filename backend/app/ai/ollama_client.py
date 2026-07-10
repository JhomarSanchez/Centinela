"""Minimal HTTP client for Ollama's generate API.

Ollama runs as a separate container; the backend only sends a prompt over
HTTP and receives text back. The model never touches the database.

Every failure mode (Ollama down, model not pulled yet, timeout, bad JSON)
returns None instead of raising: an unavailable LLM must never break
incident handling, it only means "no summary yet".
"""

import logging

import httpx

from app.ai.providers import GenerationRequest, OllamaProvider, ProviderError
from app.config import get_settings

logger = logging.getLogger(__name__)


def generate(prompt: str, client: httpx.Client | None = None) -> str | None:
    """Ask the configured Ollama model for a completion; None on any failure.

    An injectable `client` lets tests use httpx.MockTransport instead of a
    real Ollama server.
    """
    settings = get_settings()
    if not settings.ollama_enabled:
        return None

    try:
        provider = OllamaProvider(
            settings.ollama_base_url,
            settings.ollama_timeout_seconds,
            client=client,
        )
        return provider.generate(GenerationRequest(prompt, settings.ollama_model)).text
    except ProviderError:
        logger.warning(
            "Ollama request failed (model=%s, url=%s); incident will have no summary yet",
            settings.ollama_model,
            settings.ollama_base_url,
            exc_info=True,
        )
        return None
