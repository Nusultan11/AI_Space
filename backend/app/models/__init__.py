"""SQLAlchemy declarative base and Phase 02 models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base for application-owned database models."""


from app.models.room import Room  # noqa: E402
from app.models.user import User  # noqa: E402

__all__ = ["Base", "Room", "User"]
