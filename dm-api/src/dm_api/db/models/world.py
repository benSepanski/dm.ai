import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from dm_api.db.session import Base


class World(Base):
    __tablename__ = "worlds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    setting_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    themes: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    lore_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class WorldCreate(BaseModel):
    name: str
    setting_description: str | None = None
    themes: list[dict[str, Any]] | None = None
    lore_summary: str | None = None


class WorldRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    setting_description: str | None
    themes: list[dict[str, Any]] | None
    lore_summary: str | None
    created_at: datetime
    updated_at: datetime


class WorldUpdate(BaseModel):
    name: str | None = None
    setting_description: str | None = None
    themes: list[dict[str, Any]] | None = None
    lore_summary: str | None = None
