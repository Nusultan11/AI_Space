"""Establish an empty foundation revision.

Revision ID: 0001_foundation
Revises:
Create Date: 2026-09-21
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0001_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Record the foundation without creating product schema."""


def downgrade() -> None:
    """Remove only the Alembic revision marker."""
