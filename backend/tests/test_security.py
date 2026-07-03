import pytest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    encrypt_credential,
    decrypt_credential,
)


def test_password_hash_and_verify():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    token = create_access_token({"sub": "user-uuid-123", "tenant_id": "t-uuid"})
    payload = decode_token(token)
    assert payload["sub"] == "user-uuid-123"
    assert payload["type"] == "access"


def test_refresh_token_roundtrip():
    token = create_refresh_token({"sub": "user-uuid-123"})
    payload = decode_token(token)
    assert payload["type"] == "refresh"


def test_decode_invalid_token_raises():
    from jose import JWTError
    with pytest.raises(JWTError):
        decode_token("invalid.token.here")


def test_credential_encrypt_decrypt(monkeypatch):
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", key)

    from app.core.config import get_settings
    get_settings.cache_clear()

    encrypted = encrypt_credential("my-secret-token")
    assert encrypted != "my-secret-token"
    assert decrypt_credential(encrypted) == "my-secret-token"

    get_settings.cache_clear()
