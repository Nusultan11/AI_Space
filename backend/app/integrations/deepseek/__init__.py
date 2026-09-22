"""DeepSeek booking-intent integration boundary."""

from app.integrations.deepseek.fake import FakeBookingIntentParser
from app.integrations.deepseek.parser import BookingIntentParser, DeepSeekBookingIntentParser

__all__ = ["BookingIntentParser", "DeepSeekBookingIntentParser", "FakeBookingIntentParser"]
