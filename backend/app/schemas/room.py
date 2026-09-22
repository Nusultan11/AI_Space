"""Public room response contract."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    capacity: int
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
