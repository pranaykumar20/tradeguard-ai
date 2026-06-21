"""Encrypt sensitive values at rest (OAuth tokens, etc.)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

_fernet: Fernet | None = None


def _derive_key(raw: str) -> bytes:
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet

    raw = settings.secrets_encryption_key.strip()
    if not raw:
        raw = settings.clerk_secret_key.strip() or "tradeguard-dev-secrets-key"
    _fernet = Fernet(_derive_key(raw))
    return _fernet


def encrypt_secret(value: str) -> str:
    if not value:
        return ""
    return _get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    try:
        return _get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt stored secret") from exc
