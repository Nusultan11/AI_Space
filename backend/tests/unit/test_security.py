from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.schemas.auth import LoginRequest, RegisterRequest

SECRET = "unit-test-secret-with-sufficient-length"


def test_password_hash_is_not_plaintext_and_verifies() -> None:
    encoded = hash_password("correct horse battery staple")

    assert encoded != "correct horse battery staple"
    assert encoded.startswith("$argon2")
    assert verify_password("correct horse battery staple", encoded) is True
    assert verify_password("incorrect", encoded) is False


def test_access_token_round_trip() -> None:
    user_id = uuid4()
    token = create_access_token(
        user_id=user_id,
        secret=SECRET,
        algorithm="HS256",
        expires_minutes=30,
    )

    assert decode_access_token(token=token, secret=SECRET, algorithm="HS256") == user_id


def test_expired_and_invalid_tokens_are_rejected() -> None:
    expired = create_access_token(
        user_id=uuid4(),
        secret=SECRET,
        algorithm="HS256",
        expires_minutes=1,
        now=datetime.now(UTC) - timedelta(minutes=2),
    )

    assert decode_access_token(token=expired, secret=SECRET, algorithm="HS256") is None
    assert decode_access_token(token="not-a-token", secret=SECRET, algorithm="HS256") is None


def test_auth_schemas_normalize_email_and_validate_password() -> None:
    registration = RegisterRequest(
        email="  Person@Example.COM ",
        name="  Example User  ",
        password="long-enough",
    )
    login = LoginRequest(email="PERSON@example.com", password="long-enough")

    assert str(registration.email) == "person@example.com"
    assert registration.name == "Example User"
    assert str(login.email) == "person@example.com"
    with pytest.raises(ValidationError):
        RegisterRequest(email="invalid", name="User", password="short")
