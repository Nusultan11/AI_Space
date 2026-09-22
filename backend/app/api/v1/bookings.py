"""Authenticated manual booking endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, get_session
from app.core.errors import ErrorEnvelope
from app.models.booking import Booking
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingResponse
from app.services.bookings import BookingService

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("", response_model=list[BookingResponse])
async def list_bookings(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[Booking]:
    return await BookingService(session).list_for_user(user)


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorEnvelope}, 409: {"model": ErrorEnvelope}},
)
async def create_booking(
    payload: BookingCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Booking:
    return await BookingService(session).create(
        user=user,
        room_id=payload.room_id,
        title=payload.title,
        start_at=payload.start_at,
        end_at=payload.end_at,
        participants_count=payload.participants_count,
    )


@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
    responses={404: {"model": ErrorEnvelope}},
)
async def booking_detail(
    booking_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Booking:
    return await BookingService(session).get_for_user(booking_id=booking_id, user=user)


@router.post(
    "/{booking_id}/cancel",
    response_model=BookingResponse,
    responses={404: {"model": ErrorEnvelope}, 409: {"model": ErrorEnvelope}},
)
async def cancel_booking(
    booking_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Booking:
    return await BookingService(session).cancel(booking_id=booking_id, user=user)
