from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from game_engine.types import ProposalStatus, ProposalType
from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from dm_api.db.session import Base


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    world_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[ProposalType] = mapped_column(
        sa.Enum(
            ProposalType,
            name="proposal_type",
            create_type=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    content: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[ProposalStatus] = mapped_column(
        sa.Enum(
            ProposalStatus,
            name="proposal_status",
            create_type=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ProposalStatus.PENDING,
    )
    dm_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Gated narration sentence(s) tied to this proposal (PT-21): text the model
    # wrapped in [PENDING]...[/PENDING] adjacent to this proposal's block,
    # asserting the not-yet-canon entity as settled fact. None when the turn
    # had no matching pending block (mismatch case, or this proposal type
    # never carries narration — only LOCATION/CHARACTER do).
    pending_narration: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Precomputed msg:<uuid>@<timestamp> citation anchor (condenser.py's
    # MessageAnchor scheme) for the AI ChatMessage this proposal/pending
    # narration originated from. Computed once at persist time so the
    # accepted narration's anchor reflects the original AI turn, not whenever
    # accept happens (avoids a re-fetch/join on accept).
    source_anchor: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ProposalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID | None
    world_id: uuid.UUID
    type: ProposalType
    content: dict[str, Any] | None
    status: ProposalStatus
    dm_notes: str | None
    pending_narration: str | None = None
    source_anchor: str | None = None
    created_at: datetime
    # True when accepting this proposal reused an existing entity (matched by
    # case-insensitive name within the world) instead of creating a new row.
    # Always False outside of the accept endpoint.
    duplicate_merged: bool = False


class ProposalAccept(BaseModel):
    dm_notes: str | None = None
    modifications: dict[str, Any] | None = None  # optional overrides to content


class ProposalReject(BaseModel):
    dm_notes: str | None = None
