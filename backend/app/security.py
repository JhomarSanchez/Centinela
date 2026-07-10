"""Session signing and provider-credential encryption helpers."""

import base64
import hashlib
import secrets
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import get_settings


class SecretConfigurationError(RuntimeError):
    """Raised when a secure feature is used with the public default secret."""


def _derived_bytes(purpose: str, *, require_custom: bool = False) -> bytes:
    secret = get_settings().app_secret_key
    if not secret or (require_custom and secret == "change-me"):
        raise SecretConfigurationError(
            "APP_SECRET_KEY must be changed before sessions or cloud credentials can be used"
        )
    return hashlib.sha256(f"centinela:{purpose}:{secret}".encode()).digest()


def _session_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        _derived_bytes("session").hex(), salt="centinela-admin-session-v1"
    )


def create_session_token() -> tuple[str, str]:
    """Return a signed admin-session token and its CSRF value."""
    csrf_token = secrets.token_urlsafe(32)
    token = _session_serializer().dumps({"sub": "admin", "csrf": csrf_token})
    return token, csrf_token


@dataclass(frozen=True)
class SessionPayload:
    subject: str
    csrf_token: str


def read_session_token(token: str) -> SessionPayload | None:
    """Validate a signed session token, returning None when invalid or expired."""
    try:
        payload = _session_serializer().loads(
            token, max_age=get_settings().session_hours * 3600
        )
    except (BadSignature, SignatureExpired, SecretConfigurationError):
        return None
    if payload.get("sub") != "admin" or not payload.get("csrf"):
        return None
    return SessionPayload(subject="admin", csrf_token=str(payload["csrf"]))


def encrypt_credential(value: str) -> str:
    """Encrypt a provider credential with a key derived for this purpose only."""
    key = base64.urlsafe_b64encode(
        _derived_bytes("provider-credentials", require_custom=True)
    )
    return Fernet(key).encrypt(value.encode()).decode()


def decrypt_credential(value: str) -> str:
    """Decrypt a stored provider credential without ever logging its contents."""
    key = base64.urlsafe_b64encode(
        _derived_bytes("provider-credentials", require_custom=True)
    )
    try:
        return Fernet(key).decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise SecretConfigurationError("Stored provider credential cannot be decrypted") from exc
