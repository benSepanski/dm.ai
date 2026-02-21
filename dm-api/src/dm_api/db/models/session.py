import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from dm_api.db.session import Base


class GameSession(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    world_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_engine_version: Mapped[str] = mapped_column(
        String(50), nullable=False, default="dnd_5_5e"
    )
    player_character_ids: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    current_location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_summary: Mapped[str | None] = mapped_column(
        __import__("sqlalchemy").Text, nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class SessionCreate(BaseModel):
    world_id: uuid.UUID
    name: str
    rule_engine_version: str = "dnd_5_5e"
    player_character_ids: list[str] | None = None
    current_location_id: uuid.UUID | None = None


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    world_id: uuid.UUID
    name: str
    rule_engine_version: str
    player_character_ids: list[Any] | None
    current_location_id: uuid.UUID | None
    session_summary: str | None
    started_at: datetime
    ended_at: datetime | None
