from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from app.core.errors import AppError
from app.services.availability import local_day_bounds, nearest_available_slots


def test_local_day_bounds_follow_timezone_offset_changes() -> None:
    day_start, day_end = local_day_bounds(date(2026, 3, 8), "America/New_York")

    assert day_start.hour == day_end.hour == 0
    assert day_start.utcoffset() == timedelta(hours=-5)
    assert day_end.utcoffset() == timedelta(hours=-4)
    assert day_end.astimezone(UTC) - day_start.astimezone(UTC) == timedelta(hours=23)


def test_nearest_slots_preserve_duration_granularity_and_half_open_boundaries() -> None:
    start_at = datetime(2030, 1, 1, 10, 0, tzinfo=UTC)
    end_at = start_at + timedelta(hours=1)

    slots = nearest_available_slots(
        start_at=start_at,
        end_at=end_at,
        occupied=[(start_at, end_at)],
    )

    assert slots == [
        (end_at, end_at + timedelta(hours=1)),
        (end_at + timedelta(minutes=15), end_at + timedelta(hours=1, minutes=15)),
        (end_at + timedelta(minutes=30), end_at + timedelta(hours=1, minutes=30)),
    ]
    assert all(slot_end - slot_start == timedelta(hours=1) for slot_start, slot_end in slots)


def test_nearest_slots_are_bounded_to_seven_days_and_can_be_empty() -> None:
    start_at = datetime(2030, 1, 1, 10, 0, tzinfo=UTC)
    end_at = start_at + timedelta(hours=1)

    slots = nearest_available_slots(
        start_at=start_at,
        end_at=end_at,
        occupied=[(start_at, start_at + timedelta(days=7))],
    )

    assert slots == []


@pytest.mark.parametrize(
    ("start_at", "end_at", "code"),
    [
        (datetime(2030, 1, 1, 10, 0), datetime(2030, 1, 1, 11, 0), "timezone_required"),
        (
            datetime(2030, 1, 1, 11, 0, tzinfo=UTC),
            datetime(2030, 1, 1, 10, 0, tzinfo=UTC),
            "invalid_booking_interval",
        ),
    ],
)
def test_nearest_slots_reject_invalid_intervals(
    start_at: datetime,
    end_at: datetime,
    code: str,
) -> None:
    with pytest.raises(AppError) as error:
        nearest_available_slots(start_at=start_at, end_at=end_at, occupied=[])

    assert error.value.code == code
