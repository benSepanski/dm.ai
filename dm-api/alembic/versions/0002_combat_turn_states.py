"""Add combat_states.turn_states — persisted per-combatant action economy.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-11 00:00:00
"""
from __future__ import annotations
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("combat_states", sa.Column("turn_states", postgresql.JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("combat_states", "turn_states")
