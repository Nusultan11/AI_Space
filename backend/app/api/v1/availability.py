"""Authenticated free-room availability endpoint."""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query, Request
from pydantic import AwareDatetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, get_session
from app.core.config import Settings
from app.models.user import User
from app.schemas.availability import AvailabilityResponse
from app.services.availability import AvailabilityService

router = APIRouter(prefix="/availability", tags=["availability"])


@router.get("", response_model=AvailabilityResponse)
async def availability(
    start_at: Annotated[AwareDatetime, Query()],
    end_at: Annotated[AwareDatetime, Query()],
    _user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
    min_capacity: Annotated[int | None, Query(ge=1)] = None,
) -> AvailabilityResponse:
    settings = cast(Settings, request.app.state.settings)
    return await AvailabilityService(
        session,
        office_timezone=settings.office_timezone,
    ).free_rooms(
        start_at=start_at,
        end_at=end_at,
        min_capacity=min_capacity,
    )
