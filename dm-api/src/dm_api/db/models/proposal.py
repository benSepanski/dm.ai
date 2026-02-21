import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from dm_api.db.session import Base
from game_engine.types import ProposalStatus, ProposalType


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    world_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[ProposalType] = mapped_column(
        sa.Enum(ProposalType, name="proposal_type", create_type=False),
        nullable=False,
    )
    content: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[ProposalStatus] = mapped_column(
        sa.Enum(ProposalStatus, name="proposal_status", create_type=False),
        nullable=False,
        default=ProposalStatus.PENDING,
    )
    dm_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    created_at: datetime


class ProposalAccept(BaseModel):
    dm_notes: str | None = None
    modifications: dict[str, Any] | None = None  # optional overrides to content


class ProposalReject(BaseModel):
    dm_notes: str | None = None
