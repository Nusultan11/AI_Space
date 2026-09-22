"""Authentication request and response contracts."""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field, field_validator


def normalize_email(value: str) -> str:
    return value.strip().casefold()


NormalizedEmail = Annotated[EmailStr, AfterValidator(normalize_email)]


class RegisterRequest(BaseModel):
    email: NormalizedEmail
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name must not be blank")
        return normalized


class LoginRequest(BaseModel):
    email: NormalizedEmail
    password: str = Field(min_length=1, max_length=128)


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
