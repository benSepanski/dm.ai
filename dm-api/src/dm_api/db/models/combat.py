import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from dm_api.db.session import Base


class CombatState(Base):
    __tablename__ = "combat_states"
    __table_args__ = (UniqueConstraint("session_id", name="uq_combat_session"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_turn_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    initiative_order: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    combatants: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    combat_log: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class CombatStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    location_id: uuid.UUID | None
    round_number: int
    current_turn_index: int
    initiative_order: list[Any] | None
    combatants: list[Any] | None
    combat_log: list[Any] | None
    started_at: datetime
    ended_at: datetime | None


class CombatActionRequest(BaseModel):
    actor_id: str
    action_type: str  # e.g. "attack", "spell", "dash", "dodge", "help", "hide"
    target_id: str | None = None
    spell_name: str | None = None
    item_name: str | None = None
    extra: dict[str, Any] | None = None
