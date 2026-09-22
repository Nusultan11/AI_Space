"""Add concurrency-safe booking core.

Revision ID: 0003_booking_core
Revises: 0002_auth_rooms
Create Date: 2026-09-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_booking_core"
down_revision: str | None = "0002_auth_rooms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

booking_status = postgresql.ENUM(
    "confirmed",
    "cancelled",
    name="booking_status",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    booking_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            booking_status,
            nullable=False,
            server_default=sa.text("'confirmed'::booking_status"),
        ),
        sa.Column("participants_count", sa.Integer(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("end_at > start_at", name="ck_bookings_end_after_start"),
        sa.CheckConstraint(
            "participants_count IS NULL OR participants_count > 0",
            name="ck_bookings_participants_positive",
        ),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], name="fk_bookings_room_id_rooms"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_bookings_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_bookings"),
    )
    op.create_index("ix_bookings_room_id", "bookings", ["room_id"])
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"])
    op.execute(
        """
        ALTER TABLE bookings
        ADD CONSTRAINT excl_bookings_room_time_confirmed
        EXCLUDE USING gist (
            room_id WITH =,
            tstzrange(start_at, end_at, '[)') WITH &&
        )
        WHERE (status = 'confirmed'::booking_status)
        """
    )


def downgrade() -> None:
    op.drop_table("bookings")
    booking_status.drop(op.get_bind(), checkfirst=True)
    op.execute("DROP EXTENSION IF EXISTS btree_gist")
