"""Authenticated read-only room catalog endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, get_session
from app.core.errors import AppError, ErrorEnvelope
from app.models.room import Room
from app.models.user import User
from app.repositories.rooms import RoomsRepository
from app.schemas.room import RoomResponse

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=list[RoomResponse])
async def list_rooms(
    _user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[Room]:
    return await RoomsRepository(session).list_active()


@router.get(
    "/{room_id}",
    response_model=RoomResponse,
    responses={404: {"model": ErrorEnvelope}},
)
async def room_detail(
    room_id: UUID,
    _user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Room:
    room = await RoomsRepository(session).get_active_by_id(room_id)
    if room is None:
        raise AppError(
            status_code=404,
            code="room_not_found",
            message="Room was not found.",
        )
    return room
