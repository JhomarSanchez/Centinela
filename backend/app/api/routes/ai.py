"""Global AI provider configuration endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.providers import ProviderError
from app.api.deps import DbSession, require_auth, require_write_auth
from app.models.schemas import AIProviderTestRead, AISettingsRead, AISettingsUpdate
from app.security import SecretConfigurationError
from app.services import ai_settings_manager

router = APIRouter(
    prefix="/ai",
    tags=["ai-settings"],
    dependencies=[Depends(require_auth)],
)


@router.get("/config", response_model=AISettingsRead)
def get_ai_config(db: DbSession) -> AISettingsRead:
    return ai_settings_manager.to_read(ai_settings_manager.get_or_create(db))


@router.put(
    "/config",
    response_model=AISettingsRead,
    dependencies=[Depends(require_write_auth)],
)
def update_ai_config(payload: AISettingsUpdate, db: DbSession) -> AISettingsRead:
    try:
        setting = ai_settings_manager.update(db, payload)
    except SecretConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    return ai_settings_manager.to_read(setting)


@router.delete(
    "/config/credential",
    response_model=AISettingsRead,
    dependencies=[Depends(require_write_auth)],
)
def delete_ai_credential(db: DbSession) -> AISettingsRead:
    return ai_settings_manager.to_read(ai_settings_manager.delete_credential(db))


@router.post(
    "/config/test",
    response_model=AIProviderTestRead,
    dependencies=[Depends(require_write_auth)],
)
def test_ai_config(db: DbSession) -> AIProviderTestRead:
    try:
        result = ai_settings_manager.test_provider(db)
    except (ProviderError, SecretConfigurationError) as exc:
        detail = exc.code.value if isinstance(exc, ProviderError) else str(exc)
        raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY, detail=detail) from None
    return AIProviderTestRead(
        ok=True,
        provider=result.provider,
        model=result.model,
        latency_ms=result.latency_ms,
    )
