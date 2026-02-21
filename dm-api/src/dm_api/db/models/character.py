import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from dm_api.db.session import Base
from game_engine.types import CharacterType


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    world_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[CharacterType] = mapped_column(
        sa.Enum(CharacterType, name="character_type", create_type=False),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    race: Mapped[str | None] = mapped_column(String(100), nullable=True)
    char_class: Mapped[str | None] = mapped_column(String(100), nullable=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    alignment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    stats: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    hp_current: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hp_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ac: Mapped[int | None] = mapped_column(Integer, nullable=True)
    speed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    abilities: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    spells: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    equipment: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    personality_traits: Mapped[str | None] = mapped_column(Text, nullable=True)
    ideals: Mapped[str | None] = mapped_column(Text, nullable=True)
    bonds: Mapped[str | None] = mapped_column(Text, nullable=True)
    flaws: Mapped[str | None] = mapped_column(Text, nullable=True)
    known_facts: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    current_location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    interaction_log_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[Any | None] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class CharacterCreate(BaseModel):
    world_id: uuid.UUID
    type: CharacterType
    name: str
    race: str | None = None
    char_class: str | None = None
    level: int = 1
    alignment: str | None = None
    stats: dict[str, Any] | None = None
    hp_current: int | None = None
    hp_max: int | None = None
    ac: int | None = None
    speed: int | None = None
    abilities: list[Any] | None = None
    spells: list[Any] | None = None
    equipment: list[Any] | None = None
    personality_traits: str | None = None
    ideals: str | None = None
    bonds: str | None = None
    flaws: str | None = None
    known_facts: list[Any] | None = None
    current_location_id: uuid.UUID | None = None
    interaction_log_summary: str | None = None


class CharacterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    world_id: uuid.UUID
    type: CharacterType
    name: str
    race: str | None
    char_class: str | None
    level: int
    alignment: str | None
    stats: dict[str, Any] | None
    hp_current: int | None
    hp_max: int | None
    ac: int | None
    speed: int | None
    abilities: list[Any] | None
    spells: list[Any] | None
    equipment: list[Any] | None
    personality_traits: str | None
    ideals: str | None
    bonds: str | None
    flaws: str | None
    known_facts: list[Any] | None
    current_location_id: uuid.UUID | None
    interaction_log_summary: str | None
    created_at: datetime
    updated_at: datetime


class CharacterUpdate(BaseModel):
    name: str | None = None
    race: str | None = None
    char_class: str | None = None
    level: int | None = None
    alignment: str | None = None
    stats: dict[str, Any] | None = None
    hp_current: int | None = None
    hp_max: int | None = None
    ac: int | None = None
    speed: int | None = None
    abilities: list[Any] | None = None
    spells: list[Any] | None = None
    equipment: list[Any] | None = None
    personality_traits: str | None = None
    ideals: str | None = None
    bonds: str | None = None
    flaws: str | None = None
    known_facts: list[Any] | None = None
    current_location_id: uuid.UUID | None = None
    interaction_log_summary: str | None = None
