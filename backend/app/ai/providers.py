"""Provider-neutral incident summary generation contracts and adapters."""

import enum
import time
from dataclasses import dataclass
from typing import Any, Protocol

import anthropic
import httpx
import openai

from app.models import ProviderType


class ProviderErrorCode(enum.StrEnum):
    authentication = "authentication"
    rate_limit = "rate_limit"
    timeout = "timeout"
    model_unavailable = "model_unavailable"
    provider_unavailable = "provider_unavailable"
    invalid_response = "invalid_response"
    not_configured = "not_configured"


class ProviderError(RuntimeError):
    """A sanitized provider failure safe to persist and expose."""

    def __init__(self, code: ProviderErrorCode, *, retryable: bool) -> None:
        super().__init__(code.value)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True)
class GenerationRequest:
    prompt: str
    model: str
    max_output_tokens: int = 350


@dataclass(frozen=True)
class GenerationResult:
    text: str
    provider: ProviderType
    model: str
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None


class AIProvider(Protocol):
    def generate(self, request: GenerationRequest) -> GenerationResult: ...


class OllamaProvider:
    def __init__(
        self,
        base_url: str,
        timeout: float,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = client

    def generate(self, request: GenerationRequest) -> GenerationResult:
        owns_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout)
        start = time.perf_counter()
        try:
            response = client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": request.model,
                    "prompt": request.prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": request.max_output_tokens},
                },
            )
            response.raise_for_status()
            payload = response.json()
            text = str(payload.get("response", "")).strip()
            if not text:
                raise ProviderError(ProviderErrorCode.invalid_response, retryable=False)
            return GenerationResult(
                text=text,
                provider=ProviderType.ollama,
                model=request.model,
                latency_ms=int((time.perf_counter() - start) * 1000),
                input_tokens=payload.get("prompt_eval_count"),
                output_tokens=payload.get("eval_count"),
            )
        except ProviderError:
            raise
        except httpx.TimeoutException as exc:
            raise ProviderError(ProviderErrorCode.timeout, retryable=True) from exc
        except httpx.HTTPStatusError as exc:
            code = (
                ProviderErrorCode.model_unavailable
                if exc.response.status_code == 404
                else ProviderErrorCode.provider_unavailable
            )
            raise ProviderError(code, retryable=exc.response.status_code >= 500) from exc
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ProviderError(ProviderErrorCode.provider_unavailable, retryable=True) from exc
        finally:
            if owns_client:
                client.close()


class OpenAIProvider:
    def __init__(self, api_key: str, timeout: float, client: Any | None = None) -> None:
        self.client = client or openai.OpenAI(
            api_key=api_key,
            timeout=timeout,
            max_retries=0,
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        start = time.perf_counter()
        try:
            response = self.client.responses.create(
                model=request.model,
                input=request.prompt,
                max_output_tokens=request.max_output_tokens,
            )
            text = str(getattr(response, "output_text", "")).strip()
            if not text:
                raise ProviderError(ProviderErrorCode.invalid_response, retryable=False)
            usage = getattr(response, "usage", None)
            return GenerationResult(
                text=text,
                provider=ProviderType.openai,
                model=request.model,
                latency_ms=int((time.perf_counter() - start) * 1000),
                input_tokens=getattr(usage, "input_tokens", None),
                output_tokens=getattr(usage, "output_tokens", None),
            )
        except ProviderError:
            raise
        except openai.AuthenticationError as exc:
            raise ProviderError(ProviderErrorCode.authentication, retryable=False) from exc
        except openai.RateLimitError as exc:
            raise ProviderError(ProviderErrorCode.rate_limit, retryable=True) from exc
        except openai.APITimeoutError as exc:
            raise ProviderError(ProviderErrorCode.timeout, retryable=True) from exc
        except openai.NotFoundError as exc:
            raise ProviderError(ProviderErrorCode.model_unavailable, retryable=False) from exc
        except (openai.APIConnectionError, openai.InternalServerError) as exc:
            raise ProviderError(ProviderErrorCode.provider_unavailable, retryable=True) from exc
        except openai.APIStatusError as exc:
            raise ProviderError(
                ProviderErrorCode.provider_unavailable,
                retryable=exc.status_code >= 500,
            ) from exc


class AnthropicProvider:
    def __init__(self, api_key: str, timeout: float, client: Any | None = None) -> None:
        self.client = client or anthropic.Anthropic(
            api_key=api_key,
            timeout=timeout,
            max_retries=0,
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        start = time.perf_counter()
        try:
            response = self.client.messages.create(
                model=request.model,
                max_tokens=request.max_output_tokens,
                temperature=0.3,
                messages=[{"role": "user", "content": request.prompt}],
            )
            text = "".join(
                block.text for block in response.content if getattr(block, "type", None) == "text"
            ).strip()
            if not text:
                raise ProviderError(ProviderErrorCode.invalid_response, retryable=False)
            usage = getattr(response, "usage", None)
            return GenerationResult(
                text=text,
                provider=ProviderType.anthropic,
                model=request.model,
                latency_ms=int((time.perf_counter() - start) * 1000),
                input_tokens=getattr(usage, "input_tokens", None),
                output_tokens=getattr(usage, "output_tokens", None),
            )
        except ProviderError:
            raise
        except anthropic.AuthenticationError as exc:
            raise ProviderError(ProviderErrorCode.authentication, retryable=False) from exc
        except anthropic.RateLimitError as exc:
            raise ProviderError(ProviderErrorCode.rate_limit, retryable=True) from exc
        except anthropic.APITimeoutError as exc:
            raise ProviderError(ProviderErrorCode.timeout, retryable=True) from exc
        except anthropic.NotFoundError as exc:
            raise ProviderError(ProviderErrorCode.model_unavailable, retryable=False) from exc
        except (anthropic.APIConnectionError, anthropic.InternalServerError) as exc:
            raise ProviderError(ProviderErrorCode.provider_unavailable, retryable=True) from exc
        except anthropic.APIStatusError as exc:
            raise ProviderError(
                ProviderErrorCode.provider_unavailable,
                retryable=exc.status_code >= 500,
            ) from exc
