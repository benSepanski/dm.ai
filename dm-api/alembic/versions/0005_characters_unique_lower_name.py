"""Add unique index on characters(world_id, lower(name)) — PT-22/PT-23.

Enforces the CHARACTER-proposal dedupe invariant at the database layer:
two Characters in the same world can no longer share a case-insensitive
name, so a race between two concurrent proposal-accept requests for the
same new character name can no longer both insert — the losing insert now
fails with an IntegrityError instead of silently creating a duplicate row.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-01 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX ix_characters_world_id_lower_name "
        "ON characters (world_id, lower(name))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ix_characters_world_id_lower_name")
