"""Registration, login, session, and current-user dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import AppError, ErrorEnvelope
from app.core.security import create_access_token, decode_access_token
from app.models.user import User
from app.repositories.users import UsersRepository
from app.schemas.auth import AccessTokenResponse, LoginRequest, RegisterRequest
from app.schemas.user import UserResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    factory = cast(async_sessionmaker[AsyncSession], request.app.state.session_factory)
    async with factory() as session:
        yield session


def jwt_secret(settings: Settings) -> str:
    secret = cast(SecretStr | None, settings.jwt_secret)
    if secret is None:
        raise RuntimeError("JWT_SECRET must be configured before using authentication")
    return secret.get_secret_value()


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    settings = cast(Settings, request.app.state.settings)
    user_id = None
    if credentials is not None and credentials.scheme.casefold() == "bearer":
        user_id = decode_access_token(
            token=credentials.credentials,
            secret=jwt_secret(settings),
            algorithm=settings.jwt_algorithm,
        )
    user = await UsersRepository(session).get_by_id(user_id) if user_id is not None else None
    if user is None or not user.is_active:
        raise AppError(
            status_code=401,
            code="not_authenticated",
            message="Could not validate credentials.",
        )
    return user


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorEnvelope}},
)
async def register(
    payload: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    return await AuthService(session).register(
        email=str(payload.email),
        name=payload.name,
        password=payload.password,
    )


@router.post(
    "/login",
    response_model=AccessTokenResponse,
    responses={401: {"model": ErrorEnvelope}},
)
async def login(
    payload: LoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AccessTokenResponse:
    settings = cast(Settings, request.app.state.settings)
    user = await AuthService(session).authenticate(
        email=str(payload.email),
        password=payload.password,
    )
    return AccessTokenResponse(
        access_token=create_access_token(
            user_id=user.id,
            secret=jwt_secret(settings),
            algorithm=settings.jwt_algorithm,
            expires_minutes=settings.access_token_expire_minutes,
        )
    )
