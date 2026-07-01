"""Add proposals.pending_narration and proposals.source_anchor (PT-21).

Gates narration for brand-new entities at the source: the model wraps
narration that commits a new entity to canon in [PENDING]...[/PENDING]
alongside its [PROPOSAL] block. The paired pending text (and a precomputed
msg:<uuid>@<timestamp> citation anchor for the originating AI turn) are
stored on the proposal row instead of being shown until the proposal is
accepted.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-01 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("proposals", sa.Column("pending_narration", sa.Text, nullable=True))
    op.add_column("proposals", sa.Column("source_anchor", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("proposals", "source_anchor")
    op.drop_column("proposals", "pending_narration")
