"""Authenticated natural-language booking preview endpoint."""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, get_session
from app.core.config import Settings
from app.core.errors import ErrorEnvelope
from app.integrations.deepseek.parser import BookingIntentParser, DeepSeekBookingIntentParser
from app.models.user import User
from app.schemas.ai_booking import AIBookingIntentRequest, BookingIntent
from app.services.ai_booking import AIBookingService

router = APIRouter(prefix="/ai", tags=["ai"])


def get_booking_intent_parser(request: Request) -> BookingIntentParser:
    settings = cast(Settings, request.app.state.settings)
    api_key = cast(SecretStr | None, settings.deepseek_api_key)
    return DeepSeekBookingIntentParser(
        api_key=api_key.get_secret_value() if api_key is not None else None,
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
        timeout_seconds=settings.deepseek_timeout_seconds,
    )


@router.post(
    "/booking-intent",
    response_model=BookingIntent,
    responses={
        502: {"model": ErrorEnvelope},
        503: {"model": ErrorEnvelope},
        504: {"model": ErrorEnvelope},
    },
)
async def booking_intent(
    payload: AIBookingIntentRequest,
    _user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    parser: Annotated[BookingIntentParser, Depends(get_booking_intent_parser)],
    request: Request,
) -> BookingIntent:
    settings = cast(Settings, request.app.state.settings)
    return await AIBookingService(
        session,
        parser,
        office_timezone=settings.office_timezone,
    ).preview(text=payload.text)
