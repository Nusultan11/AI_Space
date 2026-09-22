"""Authenticated room catalog and schedule endpoints."""

from datetime import date
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, get_session
from app.core.config import Settings
from app.core.errors import AppError, ErrorEnvelope
from app.models.room import Room
from app.models.user import User
from app.repositories.rooms import RoomsRepository
from app.schemas.availability import RoomScheduleResponse
from app.schemas.room import RoomResponse
from app.services.availability import AvailabilityService

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


@router.get(
    "/{room_id}/schedule",
    response_model=RoomScheduleResponse,
    responses={404: {"model": ErrorEnvelope}},
)
async def room_schedule(
    room_id: UUID,
    date: date,
    _user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> RoomScheduleResponse:
    settings = cast(Settings, request.app.state.settings)
    return await AvailabilityService(
        session,
        office_timezone=settings.office_timezone,
    ).room_schedule(room_id=room_id, local_date=date)
