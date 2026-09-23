from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.core.errors import AppError
from app.schemas.ai_booking import BookingIntent, RoomContext
from app.services.ai_booking import validate_booking_intent

NOW = datetime(2030, 1, 1, 9, 0, tzinfo=ZoneInfo("Asia/Almaty"))
ROOM = RoomContext(id=uuid4(), name="Room A", capacity=4)


def _intent(**updates) -> BookingIntent:
    values = {
        "room_id": ROOM.id,
        "room_reference": "Room A",
        "start_at": NOW + timedelta(days=1),
        "end_at": NOW + timedelta(days=1, hours=1),
        "title": " Planning ",
        "participants_count": 3,
        "needs_clarification": False,
        "missing_fields": [],
        "clarification_message": None,
    }
    values.update(updates)
    return BookingIntent.model_validate(values)


def _validate(intent: BookingIntent) -> BookingIntent:
    return validate_booking_intent(intent, rooms=[ROOM], current_local_datetime=NOW)


def test_complete_intent_is_normalized_without_mutating_booking_state() -> None:
    intent = _validate(_intent())

    assert intent.title == "Planning"
    assert intent.needs_clarification is False
    assert intent.missing_fields == []
    assert intent.clarification_message is None


def test_missing_critical_values_are_normalized_to_clarification() -> None:
    intent = _validate(
        _intent(
            room_id=None,
            start_at=None,
            end_at=None,
            title=" ",
            needs_clarification=False,
            missing_fields=["participants_count", "room_id"],
        )
    )

    assert intent.needs_clarification is True
    assert intent.missing_fields == ["room_id", "start_at", "end_at", "title"]
    assert intent.clarification_message == (
        "Please provide: room, start time, end time or duration, title."
    )


def test_provider_ambiguity_is_preserved_as_clarification() -> None:
    intent = _validate(
        _intent(
            needs_clarification=True,
            clarification_message=" What time after lunch? ",
        )
    )

    assert intent.needs_clarification is True
    assert intent.clarification_message == "What time after lunch?"


def test_ai_intent_title_has_same_maximum_as_manual_booking() -> None:
    _intent(title="a" * 200)
    with pytest.raises(ValidationError):
        _intent(title="a" * 201)


def test_utc_equivalent_is_rejected_for_office_local_output_contract() -> None:
    with pytest.raises(AppError) as error:
        _validate(
            _intent(
                start_at=(NOW + timedelta(days=1)).astimezone(UTC),
                end_at=(NOW + timedelta(days=1, hours=1)).astimezone(UTC),
            )
        )
    assert error.value.code == "ai_invalid_response"


@pytest.mark.parametrize(
    "intent",
    [
        _intent(room_id=uuid4()),
        BookingIntent.model_construct(
            room_id=ROOM.id,
            start_at=datetime(2031, 1, 1, 10, 0),
            end_at=datetime(2031, 1, 1, 11, 0),
            title="Planning",
            participants_count=1,
            needs_clarification=False,
            missing_fields=[],
            clarification_message=None,
        ),
        _intent(
            start_at=NOW + timedelta(days=1),
            end_at=NOW + timedelta(hours=1),
        ),
        _intent(
            start_at=NOW - timedelta(hours=2),
            end_at=NOW - timedelta(hours=1),
        ),
        _intent(participants_count=5),
        BookingIntent.model_construct(
            room_id=ROOM.id,
            start_at=NOW + timedelta(days=1),
            end_at=NOW + timedelta(days=1, hours=1),
            title="Planning",
            participants_count=0,
            needs_clarification=False,
            missing_fields=[],
            clarification_message=None,
        ),
    ],
)
def test_impossible_domain_output_is_invalid(intent: BookingIntent) -> None:
    with pytest.raises(AppError) as error:
        _validate(intent)

    assert error.value.status_code == 502
    assert error.value.code == "ai_invalid_response"
