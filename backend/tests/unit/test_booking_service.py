from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.errors import AppError
from app.models.room import Room
from app.services.bookings import validate_booking_request

NOW = datetime(2030, 1, 1, 9, 0, tzinfo=UTC)


def validate(
    *,
    start_at: datetime = NOW + timedelta(hours=1),
    end_at: datetime = NOW + timedelta(hours=2),
    participants_count: int | None = None,
) -> None:
    validate_booking_request(
        room=Room(name="Test room", capacity=4),
        start_at=start_at,
        end_at=end_at,
        participants_count=participants_count,
        now=NOW,
    )


def test_booking_validation_accepts_aware_future_interval_and_optional_count() -> None:
    validate()
    validate(participants_count=4)


@pytest.mark.parametrize(
    ("start_at", "end_at", "code"),
    [
        (
            datetime(2030, 1, 1, 10, 0),
            datetime(2030, 1, 1, 11, 0),
            "timezone_required",
        ),
        (NOW + timedelta(hours=2), NOW + timedelta(hours=1), "invalid_booking_interval"),
        (NOW - timedelta(minutes=1), NOW + timedelta(hours=1), "booking_in_past"),
    ],
)
def test_booking_validation_rejects_invalid_time_values(
    start_at: datetime,
    end_at: datetime,
    code: str,
) -> None:
    with pytest.raises(AppError) as error:
        validate(start_at=start_at, end_at=end_at)

    assert error.value.code == code


@pytest.mark.parametrize(
    ("participants_count", "code"),
    [(0, "invalid_participants_count"), (5, "room_capacity_exceeded")],
)
def test_booking_validation_enforces_participant_count(
    participants_count: int,
    code: str,
) -> None:
    with pytest.raises(AppError) as error:
        validate(participants_count=participants_count)

    assert error.value.code == code
