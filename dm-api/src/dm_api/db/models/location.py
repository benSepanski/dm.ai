import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from dm_api.db.session import Base

LocationTypeEnum = Enum(
    "realm",
    "country",
    "region",
    "town",
    "district",
    "building",
    "room",
    "dungeon",
    "wilderness",
    name="location_type",
)


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    world_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(LocationTypeEnum, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    lore: Mapped[str | None] = mapped_column(Text, nullable=True)
    history: Mapped[str | None] = mapped_column(Text, nullable=True)
    map_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    character_associations: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    interaction_log_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[Any | None] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_visited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class LocationCreate(BaseModel):
    world_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    type: str
    name: str
    description: str | None = None
    lore: str | None = None
    history: str | None = None
    map_data: dict[str, Any] | None = None
    character_associations: list[Any] | None = None
    interaction_log_summary: str | None = None


class LocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    world_id: uuid.UUID
    parent_id: uuid.UUID | None
    type: str
    name: str
    description: str | None
    lore: str | None
    history: str | None
    map_data: dict[str, Any] | None
    character_associations: list[Any] | None
    interaction_log_summary: str | None
    created_at: datetime
    last_visited_at: datetime | None


class LocationUpdate(BaseModel):
    parent_id: uuid.UUID | None = None
    type: str | None = None
    name: str | None = None
    description: str | None = None
    lore: str | None = None
    history: str | None = None
    map_data: dict[str, Any] | None = None
    character_associations: list[Any] | None = None
    interaction_log_summary: str | None = None
    last_visited_at: datetime | None = None
