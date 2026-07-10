"""Global AI settings, encrypted credentials, and provider construction."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.ai.providers import (
    AIProvider,
    AnthropicProvider,
    GenerationRequest,
    GenerationResult,
    OllamaProvider,
    OpenAIProvider,
    ProviderError,
    ProviderErrorCode,
)
from app.config import get_settings
from app.models import AISetting, ProviderType
from app.models.schemas import AISettingsRead, AISettingsUpdate
from app.security import decrypt_credential, encrypt_credential


def get_or_create(db: Session) -> AISetting:
    setting = db.get(AISetting, 1)
    if setting is None:
        setting = AISetting(id=1)
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting


def to_read(setting: AISetting) -> AISettingsRead:
    credential_required = setting.provider != ProviderType.ollama
    return AISettingsRead(
        provider=setting.provider,
        model=setting.model,
        summary_language=setting.summary_language,
        enabled=setting.enabled,
        credential_required=credential_required,
        credential_configured=not credential_required or bool(setting.encrypted_api_key),
        api_key_hint=setting.api_key_hint,
        updated_at=setting.updated_at,
    )


def update(db: Session, payload: AISettingsUpdate) -> AISetting:
    setting = get_or_create(db)
    provider_changed = setting.provider != payload.provider
    setting.provider = payload.provider
    setting.model = payload.model.strip()
    setting.summary_language = payload.summary_language
    setting.enabled = payload.enabled
    if provider_changed and payload.api_key is None:
        setting.encrypted_api_key = None
        setting.api_key_hint = None
    if payload.api_key is not None:
        setting.encrypted_api_key = encrypt_credential(payload.api_key)
        setting.api_key_hint = payload.api_key[-4:]
    setting.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(setting)
    return setting


def delete_credential(db: Session) -> AISetting:
    setting = get_or_create(db)
    setting.encrypted_api_key = None
    setting.api_key_hint = None
    setting.enabled = False
    setting.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(setting)
    return setting


def is_ready(setting: AISetting) -> bool:
    if not setting.enabled or not setting.model:
        return False
    if setting.provider == ProviderType.ollama:
        return get_settings().ollama_enabled
    return bool(setting.encrypted_api_key)


def build_provider(setting: AISetting) -> AIProvider:
    settings = get_settings()
    if not is_ready(setting):
        raise ProviderError(ProviderErrorCode.not_configured, retryable=False)
    if setting.provider == ProviderType.ollama:
        return OllamaProvider(settings.ollama_base_url, settings.ollama_timeout_seconds)
    api_key = decrypt_credential(setting.encrypted_api_key or "")
    if setting.provider == ProviderType.openai:
        return OpenAIProvider(api_key, settings.openai_timeout_seconds)
    return AnthropicProvider(api_key, settings.anthropic_timeout_seconds)


def test_provider(db: Session) -> GenerationResult:
    setting = get_or_create(db)
    prompt = (
        "Reply with exactly OK." if setting.summary_language.value == "en" else "Responde sólo OK."
    )
    return build_provider(setting).generate(
        GenerationRequest(prompt=prompt, model=setting.model, max_output_tokens=8)
    )
