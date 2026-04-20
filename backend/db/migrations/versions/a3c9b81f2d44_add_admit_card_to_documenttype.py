"""add admit_card to documenttype enum

Revision ID: a3c9b81f2d44
Revises: 6f2f3f457401
Create Date: 2026-04-20 09:28:00.000000

"""
from typing import Sequence, Union
from alembic import op


revision: str = 'a3c9b81f2d44'
down_revision: Union[str, Sequence[str], None] = '6f2f3f457401'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL requires this specific syntax to add a new value to an existing enum
    op.execute("ALTER TYPE documenttype ADD VALUE IF NOT EXISTS 'admit_card'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; this is intentionally a no-op.
    # To fully revert, you would need to recreate the enum without 'admit_card'.
    pass
