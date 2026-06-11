"""Add game_configs — per-game DM-tunable overrides (AI models, context budget, storage).

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-11 00:00:00
"""
from __future__ import annotations
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_configs",
        sa.Column(
            "world_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("worlds.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("ai_provider", sa.String(20), nullable=True),
        sa.Column("orchestrator_model", sa.String(100), nullable=True),
        sa.Column("generation_model", sa.String(100), nullable=True),
        sa.Column("context_token_limit", sa.Integer, nullable=True),
        sa.Column("context_preserve_last_n", sa.Integer, nullable=True),
        sa.Column("database_url", sa.Text, nullable=True),
        sa.Column("redis_url", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("game_configs")
