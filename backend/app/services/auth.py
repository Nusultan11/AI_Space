"""Authentication application service."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import DUMMY_PASSWORD_HASH, hash_password, verify_password
from app.models.user import User
from app.repositories.users import UsersRepository


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UsersRepository(session)

    async def register(self, *, email: str, name: str, password: str) -> User:
        if await self.users.get_by_email(email) is not None:
            raise email_already_registered()
        try:
            user = await self.users.add(
                email=email,
                name=name,
                password_hash=hash_password(password),
            )
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except IntegrityError:
            await self.session.rollback()
            raise email_already_registered() from None

    async def authenticate(self, *, email: str, password: str) -> User:
        user = await self.users.get_by_email(email)
        encoded_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
        password_valid = verify_password(password, encoded_hash)
        if user is None or not password_valid or not user.is_active:
            raise invalid_credentials()
        return user


def email_already_registered() -> AppError:
    return AppError(
        status_code=409,
        code="email_already_registered",
        message="An account with this email already exists.",
    )


def invalid_credentials() -> AppError:
    return AppError(
        status_code=401,
        code="invalid_credentials",
        message="Invalid email or password.",
    )
